"""Skill router — LLM-based with memory, truncation, reflection, supervisor, web search."""
import asyncio
import traceback
import json
from app.models.schemas import ChatResponse, ContentBlock
from app.services.llm_client import llm_client
from app.services.llm_prompts import SKILL_PROMPTS
from app.services.response_parser import parse_llm_response
from app.services.document_store import doc_store
from app.services.reflection import reflect
from app.services.supervisor import classify_intent
from app.services.web_search import web_search, format_search_results

# Keep old skills as fallback
from app.skills.portfolio_analytics import PortfolioAnalyticsSkill
from app.skills.investment_analysis import InvestmentAnalysisSkill
from app.skills.market_research import MarketResearchSkill
from app.skills.benchmarking import BenchmarkingSkill
from app.skills.committee_advisor import CommitteeAdvisorSkill

FALLBACK_SKILLS = {
    "portfolio_analytics": PortfolioAnalyticsSkill(),
    "investment_analysis": InvestmentAnalysisSkill(),
    "market_research": MarketResearchSkill(),
    "benchmarking": BenchmarkingSkill(),
    "committee_advisor": CommitteeAdvisorSkill(),
}

import re as _re

from app.services.cache import cache_key as _cache_key_fn, get_cached, set_cached, clear_cache as _clear_cache

def _cache_key(skill_id: str, message: str) -> str:
    doc_ids = [d.id for d in doc_store.list_global()]
    return _cache_key_fn(skill_id, message, doc_ids)

def clear_response_cache():
    """Call when documents change."""
    _clear_cache()

# --- Context config ---
MAX_CONTEXT_BYTES = 80_000
MAX_PER_DOC_BYTES = 3_000
KB_DOC_ID = "kb_default"

SKILL_DOC_MAP = {
    "portfolio_analytics": ["kb_default", "src_mts", "src_seg_report", "src_seg_q4", "src_etalon", "src_step", "src_binno", "src_seg_credit", "src_div_mts", "src_seg_div", "src_bloomberg", "src_industry"],
    "investment_analysis": ["kb_default", "src_project", "src_finmodel", "src_appraiser", "src_mgmt", "src_legal_dd", "src_logistics", "src_jll"],
    "market_research": ["kb_default", "src_logistics", "src_jll", "src_bloomberg", "src_industry"],
    "benchmarking": ["kb_default", "src_mts", "src_seg_report", "src_etalon", "src_step", "src_binno", "src_bloomberg", "src_industry"],
    "committee_advisor": ["kb_default", "src_project", "src_finmodel", "src_appraiser", "src_mgmt", "src_legal_dd", "src_committee"],
}


def _build_context(skill_id: str, message: str, session_id: str, attachment_ids: list[str] | None = None) -> str:
    """Build document context with smart truncation."""
    parts = []
    total_bytes = 0
    relevant_ids = set(SKILL_DOC_MAP.get(skill_id, ["kb_default"]))

    # 1. KB always full (if active)
    kb_meta = doc_store.get(KB_DOC_ID)
    if kb_meta is None or kb_meta.is_active:
        kb_text = doc_store.get_text(KB_DOC_ID)
        if kb_text:
            parts.append(f"=== База знаний АФК Система ===\n{kb_text}")
            total_bytes += len(kb_text.encode("utf-8"))

    # 2. Try vector search if available
    search_chunks = None
    try:
        from app.services.vector_store import vector_store
        if vector_store and vector_store.has_data():
            search_chunks = vector_store.search(message, top_k=15)
    except (ImportError, Exception):
        pass

    if search_chunks:
        chunk_text = "\n\n".join(f"--- Релевантный фрагмент ---\n{c}" for c in search_chunks)
        if total_bytes + len(chunk_text.encode("utf-8")) < MAX_CONTEXT_BYTES:
            parts.append(chunk_text)
            total_bytes += len(chunk_text.encode("utf-8"))
    else:
        # Fallback: skill-based doc filtering with truncation
        for doc in doc_store.list_global():
            if doc.id == KB_DOC_ID:
                continue
            is_demo = doc.id.startswith("src_")
            is_relevant = doc.id in relevant_ids
            is_user_uploaded = not is_demo

            if (is_relevant or is_user_uploaded) and doc.is_active:
                text = doc_store.get_text(doc.id)
                if text:
                    # Truncate per-doc
                    if is_demo and len(text.encode("utf-8")) > MAX_PER_DOC_BYTES:
                        text = text[:MAX_PER_DOC_BYTES] + "\n[...обрезано...]"
                    doc_entry = f"=== {doc.original_name} ===\n{text}"
                    entry_bytes = len(doc_entry.encode("utf-8"))
                    if total_bytes + entry_bytes < MAX_CONTEXT_BYTES:
                        parts.append(doc_entry)
                        total_bytes += entry_bytes

    # 3. Session documents
    for doc in doc_store.list_session(session_id):
        if not doc.is_active:
            continue
        text = doc_store.get_text(doc.id)
        if text:
            doc_entry = f"=== {doc.original_name} (сессия) ===\n{text}"
            entry_bytes = len(doc_entry.encode("utf-8"))
            if total_bytes + entry_bytes < MAX_CONTEXT_BYTES:
                parts.append(doc_entry)
                total_bytes += entry_bytes

    # 4. Explicit attachments
    included = {p.split("===")[1].strip() if "===" in p else "" for p in parts}
    if attachment_ids:
        for aid in attachment_ids:
            doc = doc_store.get(aid)
            if doc and doc.original_name not in included:
                text = doc_store.get_text(aid)
                if text:
                    doc_entry = f"=== {doc.original_name} (прикреплённый) ===\n{text}"
                    entry_bytes = len(doc_entry.encode("utf-8"))
                    if total_bytes + entry_bytes < MAX_CONTEXT_BYTES:
                        parts.append(doc_entry)
                        total_bytes += entry_bytes

    return "\n\n".join(parts)


def _sources_block() -> ContentBlock:
    sources = [{"id": f"doc_{d.id}", "title": d.original_name, "type": d.file_type, "page": ""} for d in doc_store.list_global()]
    return ContentBlock(type="sources", data=sources or [{"id": "none", "title": "Нет документов", "type": "info", "page": ""}])


async def route(skill_id: str, message: str, session_id: str, attachment_ids: list[str] | None = None, history: list[dict] | None = None) -> ChatResponse:
    """Route message through LLM with full pipeline: supervisor -> context -> LLM -> reflection."""

    # 1. Supervisor: auto-classify if needed
    if skill_id == "auto":
        skill_id = await classify_intent(message, history)
        print(f"[SUPERVISOR] Classified as: {skill_id}")

    system_prompt = SKILL_PROMPTS.get(skill_id)
    if not system_prompt:
        return ChatResponse(session_id=session_id, blocks=[ContentBlock(type="text", data=f"Скилл '{skill_id}' не найден.")])

    # Cache check (persistent SQLite)
    ck = _cache_key(skill_id, message)
    if not attachment_ids:
        cached_data = get_cached(ck)
        if cached_data:
            print(f"[CACHE] Hit: {message[:40]}")
            blocks = [ContentBlock(**b) for b in cached_data["blocks"]]
            return ChatResponse(session_id=session_id, blocks=blocks)

    try:
        # 2. Build context + web search in parallel
        async def _get_web_context():
            try:
                results = await web_search(f"{message} рынок Россия 2025", max_results=5)
                if results and results[0].get("url"):
                    return format_search_results(results)
            except Exception:
                pass
            return ""

        context_future = asyncio.get_event_loop().run_in_executor(
            None, _build_context, skill_id, message, session_id, attachment_ids
        )
        # web_search disabled: CoType does not support internet access
        context = await context_future
        web_context = ""

        # 4. Build messages with history
        messages = []
        if history:
            for h in (history or [])[-8:]:
                role = h.get("role", "user")
                content = h.get("content", "")[:1500]
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        user_content = f"Контекст документов:\n\n{context}"
        if web_context:
            user_content += f"\n\n{web_context}"
        user_content += f"\n\n---\n\nВопрос пользователя: {message}"
        messages.append({"role": "user", "content": user_content})

        # 5. Call ReAct agent (tool-augmented LLM)
        from app.services.react_agent import run_react_agent
        raw_response, tool_log = await run_react_agent(
            message=message,
            skill_prompt=system_prompt,
            context=context,
            history=history,
            skill_id=skill_id,
        )
        # Log tool calls for debugging
        if tool_log:
            print(f"[REACT] {len(tool_log)} tool calls: {[t['action'] for t in tool_log]}")

        # 6. Reflection — pass tool results as verified ground-truth
        try:
            # Build verified facts from tool_log results
            tool_facts = ""
            if tool_log:
                import json as _json
                facts_parts = []
                for t in tool_log:
                    res = t.get("result", {})
                    res_str = _json.dumps(res, ensure_ascii=False)[:1500]
                    facts_parts.append(f"Tool `{t['action']}` вернул: {res_str}")
                tool_facts = "\n".join(facts_parts)

            reflect_context = tool_facts if tool_facts else context[:3000]
            passed, reflection_detail = await reflect(message, raw_response, reflect_context, skill_id=skill_id)
            if not passed:
                print(f"[REFLECTION] FAIL: {reflection_detail}")
                # Retry: include tool results so LLM uses verified data, not guesses
                verified_data_msg = (
                    f"Верификатор нашёл проблему: {reflection_detail}\n\n"
                    f"Перепиши ответ, используя ТОЛЬКО эти проверенные данные из инструментов:\n{tool_facts}\n\n"
                    f"Если данные по какому-либо показателю отсутствуют — пиши 'н/д', не выдумывай."
                ) if tool_facts else (
                    f"Верификатор нашёл проблему: {reflection_detail}\n\n"
                    f"Перепиши ответ, используя только данные из документов выше. Не выдумывай цифры."
                )
                retry_messages = messages + [
                    {"role": "assistant", "content": raw_response},
                    {"role": "user", "content": verified_data_msg}
                ]
                raw_response = await llm_client.chat(system_prompt, retry_messages)
            else:
                print(f"[REFLECTION] PASS")
        except Exception as e:
            print(f"[REFLECTION] Skipped: {e}")

        # Multi-turn: if LLM needs more data
        for _iteration in range(2):
            if "<NEED_DATA" not in raw_response:
                break
            need_queries = _re.findall(r'<NEED_DATA query="([^"]+)"/>', raw_response)
            if not need_queries:
                break
            extra = ""
            try:
                from app.services.vector_store import vector_store
                for q in need_queries:
                    chunks = vector_store.search(q, top_k=5)
                    extra += "\n\n".join(chunks)
            except Exception:
                break
            clean = _re.sub(r'<NEED_DATA[^/]*/>', '', raw_response)
            messages.append({"role": "assistant", "content": clean})
            messages.append({"role": "user", "content": f"Дополнительные данные:\n{extra}"})
            raw_response = await llm_client.chat(system_prompt, messages)
            print(f"[MULTI-TURN] Iteration {_iteration + 1}")

        # 7. Parse response
        blocks = parse_llm_response(raw_response)
        # _sources_block removed — was showing all docs, not actually used sources

        # Auto-generate PDF if response has tables
        if any(b.type == "table" for b in blocks) or len(raw_response) > 1500:
            try:
                from app.services.pdf_generator import ReportPDF
                pdf = ReportPDF(f"Ответ: {message[:50]}")
                pdf.add_title_page(subtitle=message[:100], date="Март 2026")
                pdf.pdf.add_page()
                for block in blocks:
                    if block.type == "text":
                        sections = block.data.split("\n## ")
                        for i, part in enumerate(sections):
                            if part.strip():
                                lines = part.split("\n")
                                heading = lines[0].strip("# ") if i > 0 else "Аналитика"
                                body = "\n".join(lines[1:]).strip() if len(lines) > 1 else part.strip()
                                pdf.add_section(heading, body)
                    elif block.type == "table" and isinstance(block.data, dict):
                        headers = block.data.get("headers", [])
                        rows = block.data.get("rows", [])
                        if headers and rows:
                            pdf.add_table(headers, rows)
                report_id, _ = pdf.save()
                blocks.append(ContentBlock(type="pdf_link", data={
                    "report_id": report_id,
                    "title": f"Скачать: {message[:50]}",
                    "description": "PDF с таблицами и аналитикой",
                }))
            except Exception as e:
                print(f"[PDF] Failed: {e}")

        # Cache response (persistent SQLite)
        response = ChatResponse(session_id=session_id, blocks=blocks)
        if not attachment_ids:
            set_cached(ck, skill_id, message, {"blocks": [b.model_dump() for b in blocks]})
        return response

    except Exception as e:
        print(f"[LLM ERROR] {e}")
        traceback.print_exc()
        # Fallback
        fallback = FALLBACK_SKILLS.get(skill_id)
        if fallback:
            try:
                response = await fallback.handle(message, session_id, extra_context="")
                response.blocks.insert(0, ContentBlock(type="text", data="*⚠️ LLM недоступен — pre-scripted режим.*\n\n"))
                response.session_id = session_id
                return response
            except Exception:
                pass
        return ChatResponse(session_id=session_id, blocks=[ContentBlock(type="text", data=f"Ошибка: {e}")])


async def route_stream(skill_id: str, message: str, session_id: str, attachment_ids: list[str] | None = None, history: list[dict] | None = None):
    """Streaming version of route — optimized for speed."""

    # 0. Supervisor first if auto
    if skill_id == "auto":
        skill_id = await classify_intent(message, history)
        print(f"[SUPERVISOR] Classified as: {skill_id}")

    # 1. Supervisor + context building in parallel
    async def _get_web_context():
        try:
            results = await web_search(f"{message} рынок Россия 2025", max_results=5)
            if results and results[0].get("url"):
                return format_search_results(results)
        except Exception:
            pass
        return ""

    if False:
        pass  # supervisor already called above
    else:
        # skill_id is known — run context + web search in parallel
        context_future = asyncio.get_event_loop().run_in_executor(
            None, _build_context, skill_id, message, session_id, attachment_ids
        )
        # web_search disabled: CoType does not support internet access
        context = await context_future
        web_context = ""

    system_prompt = SKILL_PROMPTS.get(skill_id)
    if not system_prompt:
        yield {"data": json.dumps({"type": "text_delta", "content": f"Скилл '{skill_id}' не найден."})}
        yield {"data": json.dumps({"type": "done", "session_id": session_id})}
        return

    try:

        # 4. Messages with history
        messages = []
        if history:
            for h in (history or [])[-8:]:
                role = h.get("role", "user")
                content = h.get("content", "")[:1500]
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        user_content = f"Контекст документов:\n\n{context}"
        if web_context:
            user_content += f"\n\n{web_context}"
        user_content += f"\n\n---\n\nВопрос пользователя: {message}"
        messages.append({"role": "user", "content": user_content})

        # 5. Collect answer through ReAct agent
        import re
        import json as _json
        from app.services.react_agent import run_react_agent_stream

        full_text = ""
        async for event in run_react_agent_stream(
            message=message,
            skill_prompt=system_prompt,
            context=context,
            history=history,
            skill_id=skill_id,
        ):
            if event["type"] == "thinking":
                yield {"data": _json.dumps({"type": "status", "content": "... " + event["content"]})}
            elif event["type"] == "tool_call":
                yield {"data": _json.dumps({"type": "status", "content": ">> " + event["content"]})}
            elif event["type"] == "tool_result":
                yield {"data": _json.dumps({"type": "status", "content": "Данные получены"})}
            elif event["type"] == "answer":
                full_text = event["content"]

        # 6. Skip reflection in streaming path — ReAct agent's _verify_answer() already checks.
        #    Reflection adds 3-5s latency for minimal benefit in interactive mode.
        verified_text = full_text

        # 7. Parse into blocks and stream response in large chunks (no artificial delays)
        from app.services.response_parser import parse_llm_response, _parse_table, _parse_chart
        tag_pattern = re.compile(r'(<TABLE>.*?</TABLE>|<CHART>.*?</CHART>)', re.DOTALL)

        parts = tag_pattern.split(verified_text)

        for part in parts:
            part_stripped = part.strip()
            if not part_stripped:
                continue

            if part_stripped.startswith("<TABLE>") and part_stripped.endswith("</TABLE>"):
                yield {"data": json.dumps({"type": "text_done"})}
                block = _parse_table(part_stripped)
                if block:
                    yield {"data": json.dumps({"type": "table", "data": block.data}, ensure_ascii=False)}
            elif part_stripped.startswith("<CHART>") and part_stripped.endswith("</CHART>"):
                yield {"data": json.dumps({"type": "text_done"})}
                block = _parse_chart(part_stripped)
                if block:
                    yield {"data": json.dumps({"type": "chart", "data": block.data}, ensure_ascii=False)}
            else:
                # Stream text in sentence-sized chunks (~500 chars) with no sleep delays
                chunk_size = 500
                for i in range(0, len(part_stripped), chunk_size):
                    chunk = part_stripped[i:i+chunk_size]
                    yield {"data": json.dumps({"type": "text_delta", "content": chunk})}
                yield {"data": json.dumps({"type": "text_done"})}

        # Auto-generate PDF
        all_blocks = parse_llm_response(verified_text)
        if any(b.type == "table" for b in all_blocks) or len(verified_text) > 1500:
            try:
                from app.services.pdf_generator import ReportPDF
                pdf = ReportPDF(f"Ответ: {message[:50]}")
                pdf.add_title_page(subtitle=message[:100], date="Март 2026")
                pdf.pdf.add_page()
                for block in all_blocks:
                    if block.type == "text":
                        sections = block.data.split("\n## ")
                        for i, part in enumerate(sections):
                            if part.strip():
                                lines = part.split("\n")
                                heading = lines[0].strip("# ") if i > 0 else "Аналитика"
                                body = "\n".join(lines[1:]).strip() if len(lines) > 1 else part.strip()
                                pdf.add_section(heading, body)
                    elif block.type == "table" and isinstance(block.data, dict):
                        headers = block.data.get("headers", [])
                        rows = block.data.get("rows", [])
                        if headers and rows:
                            pdf.add_table(headers, rows)
                report_id, _ = pdf.save()
                yield {"data": json.dumps({"type": "pdf_link", "data": {"report_id": report_id, "title": f"Скачать: {message[:50]}", "description": "PDF"}}, ensure_ascii=False)}
            except Exception as e:
                print(f"[PDF STREAM] Failed: {e}")

        # 7. Sources
        # sources block removed — was fake (showed all docs, not used ones)
        yield {"data": json.dumps({"type": "done", "session_id": session_id})}

    except Exception as e:
        print(f"[STREAM ERROR] {e}")
        traceback.print_exc()
        yield {"data": json.dumps({"type": "text_delta", "content": f"⚠️ Ошибка: {e}"})}
        yield {"data": json.dumps({"type": "done", "session_id": session_id})}
