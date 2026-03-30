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

# Skills that warrant reflection (high-stakes analysis)
REFLECTION_SKILLS = {"committee_advisor", "investment_analysis"}

# Simple skills: direct RAG (1 LLM call). Complex skills: ReAct agent (multi-turn).
SIMPLE_SKILLS = {"portfolio_analytics", "benchmarking", "market_research"}
COMPLEX_SKILLS = {"committee_advisor", "investment_analysis"}

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


# =============================================
# Helper functions
# =============================================

def _cache_key(skill_id: str, message: str) -> str:
    doc_ids = [d.id for d in doc_store.list_global()]
    return _cache_key_fn(skill_id, message, doc_ids, provider=llm_client.provider)


def clear_response_cache():
    """Call when documents change."""
    _clear_cache()


def _build_messages(history: list[dict] | None, context: str, message: str) -> list[dict]:
    """Build LLM message list from history + context + user message."""
    messages = []
    if history:
        for h in (history or [])[-8:]:
            role = h.get("role", "user")
            content = h.get("content", "")[:1500]
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    user_content = f"Контекст документов:\n\n{context}"
    user_content += f"\n\n---\n\nВопрос пользователя: {message}"
    messages.append({"role": "user", "content": user_content})
    return messages


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


def _build_tool_facts(tool_log: list[dict]) -> str:
    """Extract verified facts from tool execution log."""
    if not tool_log:
        return ""
    facts_parts = []
    for t in tool_log:
        res = t.get("result", {})
        res_str = json.dumps(res, ensure_ascii=False)[:1500]
        facts_parts.append(f"Tool `{t['action']}` вернул: {res_str}")
    return "\n".join(facts_parts)


async def _run_reflection(skill_id: str, message: str, raw_response: str,
                          tool_log: list[dict], context: str,
                          system_prompt: str, messages: list[dict]) -> str:
    """Run reflection for complex skills. Returns (possibly corrected) response."""
    if skill_id not in REFLECTION_SKILLS:
        print(f"[REFLECTION] Skipped for skill: {skill_id}")
        return raw_response

    try:
        tool_facts = _build_tool_facts(tool_log)
        # Include both tool facts AND document context so reflection sees all available data
        reflect_context = tool_facts + "\n\n" + context[:4000] if tool_facts else context[:5000]
        passed, reflection_detail = await reflect(message, raw_response, reflect_context, skill_id=skill_id)
        if not passed:
            print(f"[REFLECTION] FAIL: {reflection_detail}")
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
            return await llm_client.chat(system_prompt, retry_messages)
        else:
            print(f"[REFLECTION] PASS")
    except Exception as e:
        print(f"[REFLECTION] Skipped: {e}")

    return raw_response


async def _handle_multi_turn(raw_response: str, system_prompt: str, messages: list[dict]) -> str:
    """Handle <NEED_DATA> requests for additional data."""
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
    return raw_response


def _gather_tool_data(skill_id: str, message: str) -> str:
    """Pre-gather structured data from tools for direct RAG path.

    Runs relevant tools based on skill type and message keywords,
    then formats results as structured context for a single LLM call.
    """
    from app.services.tools import data_query, portfolio_ranking
    msg_lower = message.lower()
    parts = []

    if skill_id == "portfolio_analytics":
        # Always include overview + holding summary
        overview = data_query(entity="overview")
        if overview.get("data"):
            parts.append("### Обзор холдинга\n" + json.dumps(overview["data"], ensure_ascii=False, indent=2))

        # Revenue growth ranking (always useful)
        growth_data = data_query(entity="all", metric="рост")
        growth_items = [d for d in growth_data.get("data", []) if d.get("type") == "revenue_growth_ranking"]
        if growth_items:
            parts.append("### Ранжирование по росту выручки\n" + json.dumps(growth_items, ensure_ascii=False, indent=2))

        # Detect metric from message
        if any(w in msg_lower for w in ["долг", "нагруз", "leverage", "debt"]):
            ranking = portfolio_ranking(metric="долг")
        elif any(w in msg_lower for w in ["выручк", "рост", "revenue", "быстр"]):
            ranking = portfolio_ranking(metric="выручка")
        elif any(w in msg_lower for w in ["дивиденд", "выплат"]):
            ranking = portfolio_ranking(metric="дивиденды")
        elif any(w in msg_lower for w in ["прибыл", "убыт", "profit"]):
            ranking = portfolio_ranking(metric="прибыль")
        elif any(w in msg_lower for w in ["ebitda", "oibda", "марж"]):
            ranking = portfolio_ranking(metric="ebitda")
        elif any(w in msg_lower for w in ["сектор", "отрасл"]):
            ranking = portfolio_ranking(metric="выручка")
        else:
            ranking = portfolio_ranking(metric="выручка")
        if ranking.get("ranking"):
            parts.append("### Ранжирование портфеля\n" + json.dumps(ranking, ensure_ascii=False, indent=2))

        # For specific company questions, fetch detailed data
        for company in ["МТС", "Ozon", "Segezha", "Эталон", "МЕДСИ", "Биннофарм", "СТЕПЬ"]:
            if company.lower() in msg_lower:
                detail = data_query(entity=company)
                if detail.get("data"):
                    parts.append(f"### {company} (детально)\n" + json.dumps(detail["data"], ensure_ascii=False, indent=2))

    elif skill_id == "market_research":
        # Fetch sector dynamics
        sector_data = data_query(entity="all", metric="сектор")
        if sector_data.get("data"):
            parts.append("### Секторы\n" + json.dumps(sector_data["data"], ensure_ascii=False, indent=2))

        # Macro context
        macro = data_query(entity="макро")
        if macro.get("data"):
            parts.append("### Макроэкономика\n" + json.dumps(macro["data"], ensure_ascii=False, indent=2))

        # Specific sector search from message
        for sector in ["логистик", "телеком", "e-commerce", "девелоп", "медицин", "фарм", "агро", "лесопром"]:
            if sector in msg_lower:
                sec_detail = data_query(entity=sector)
                if sec_detail.get("data"):
                    parts.append(f"### Сектор: {sector}\n" + json.dumps(sec_detail["data"], ensure_ascii=False, indent=2))

    elif skill_id == "benchmarking":
        # Portfolio ranking by multiple metrics for comparison
        for m in ["выручка", "ebitda", "долг", "маржа"]:
            ranking = portfolio_ranking(metric=m)
            if ranking.get("ranking"):
                parts.append(f"### Ранжирование: {m}\n" + json.dumps(ranking, ensure_ascii=False, indent=2))

        # Company profiles with valuation_context (EV/EBITDA data)
        all_profiles = data_query(entity="all", metric="")
        profile_data = [d for d in all_profiles.get("data", []) if d.get("type") == "profile"]
        if profile_data:
            parts.append("### Профили компаний (оценка)\n" + json.dumps(profile_data, ensure_ascii=False, indent=2))

        # Specific company data if mentioned
        for company in ["МТС", "Ozon", "Segezha", "Эталон", "МЕДСИ", "Биннофарм", "СТЕПЬ"]:
            if company.lower() in msg_lower:
                detail = data_query(entity=company)
                if detail.get("data"):
                    parts.append(f"### {company}\n" + json.dumps(detail["data"], ensure_ascii=False, indent=2))

    return "\n\n".join(parts) if parts else ""


async def _run_direct_rag(system_prompt: str, messages: list[dict], tool_data: str) -> tuple[str, list[dict]]:
    """Direct RAG path: single LLM call with pre-gathered tool data. Returns (response, empty_tool_log)."""
    if tool_data:
        # Inject structured tool data into the last user message
        last_msg = messages[-1]
        messages[-1] = {
            "role": "user",
            "content": last_msg["content"] + f"\n\n---\n\nСТРУКТУРИРОВАННЫЕ ДАННЫЕ ИЗ ИНСТРУМЕНТОВ:\n{tool_data[:20000]}"
        }
    response = await llm_client.chat(system_prompt, messages)
    return response, []


def _generate_pdf(blocks: list[ContentBlock], message: str) -> ContentBlock | None:
    """Generate PDF from response blocks if applicable."""
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
        return ContentBlock(type="pdf_link", data={
            "report_id": report_id,
            "title": f"Скачать: {message[:50]}",
            "description": "PDF с таблицами и аналитикой",
        })
    except Exception as e:
        print(f"[PDF] Failed: {e}")
        return None


# =============================================
# Main route functions
# =============================================

async def route(skill_id: str, message: str, session_id: str, attachment_ids: list[str] | None = None, history: list[dict] | None = None) -> ChatResponse:
    """Route message through LLM with full pipeline: supervisor -> context -> LLM -> reflection."""

    # 1. Supervisor: auto-classify if needed
    if skill_id == "auto":
        skill_id = await classify_intent(message, history)
        print(f"[SUPERVISOR] Classified as: {skill_id}")

    system_prompt = SKILL_PROMPTS.get(skill_id)
    if not system_prompt:
        return ChatResponse(session_id=session_id, blocks=[ContentBlock(type="text", data=f"Скилл '{skill_id}' не найден.")])

    # 2. Cache check
    ck = _cache_key(skill_id, message)
    if not attachment_ids:
        cached_data = get_cached(ck)
        if cached_data:
            print(f"[CACHE] Hit: {message[:40]}")
            blocks = [ContentBlock(**b) for b in cached_data["blocks"]]
            return ChatResponse(session_id=session_id, blocks=blocks)

    try:
        # 3. Build context
        context = await asyncio.get_event_loop().run_in_executor(
            None, _build_context, skill_id, message, session_id, attachment_ids
        )

        # 4. Build messages
        messages = _build_messages(history, context, message)

        # 5. Hybrid: RAG for simple skills, ReAct for complex
        if skill_id in SIMPLE_SKILLS:
            tool_data = _gather_tool_data(skill_id, message)
            raw_response, tool_log = await _run_direct_rag(system_prompt, messages, tool_data)
            print(f"[RAG] Direct response for {skill_id} ({len(tool_data)} chars tool data)")
        else:
            from app.services.react_agent import run_react_agent
            raw_response, tool_log = await run_react_agent(
                message=message,
                skill_prompt=system_prompt,
                context=context,
                history=history,
                skill_id=skill_id,
            )
            if tool_log:
                print(f"[REACT] {len(tool_log)} tool calls: {[t['action'] for t in tool_log]}")

        # 6. Reflection (only for complex skills)
        raw_response = await _run_reflection(
            skill_id, message, raw_response, tool_log, context, system_prompt, messages
        )

        # 7. Multi-turn data requests
        raw_response = await _handle_multi_turn(raw_response, system_prompt, messages)

        # 8. Parse response + PDF
        blocks = parse_llm_response(raw_response)
        if any(b.type == "table" for b in blocks) or len(raw_response) > 1500:
            pdf_block = _generate_pdf(blocks, message)
            if pdf_block:
                blocks.append(pdf_block)

        # 9. Cache and return
        response = ChatResponse(session_id=session_id, blocks=blocks)
        if not attachment_ids:
            set_cached(ck, skill_id, message, {"blocks": [b.model_dump() for b in blocks]})
        return response

    except Exception as e:
        print(f"[LLM ERROR] {e}")
        traceback.print_exc()
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

    # 1. Supervisor
    if skill_id == "auto":
        skill_id = await classify_intent(message, history)
        print(f"[SUPERVISOR] Classified as: {skill_id}")

    # 2. Build context
    context = await asyncio.get_event_loop().run_in_executor(
        None, _build_context, skill_id, message, session_id, attachment_ids
    )

    system_prompt = SKILL_PROMPTS.get(skill_id)
    if not system_prompt:
        yield {"data": json.dumps({"type": "text_delta", "content": f"Скилл '{skill_id}' не найден."})}
        yield {"data": json.dumps({"type": "done", "session_id": session_id})}
        return

    try:
        # 3. Build messages
        messages = _build_messages(history, context, message)

        import re
        import json as _json

        # 4. Hybrid: RAG stream for simple skills, ReAct stream for complex
        full_text = ""
        if skill_id in SIMPLE_SKILLS:
            # Direct RAG: gather data, single LLM stream call
            tool_data = _gather_tool_data(skill_id, message)
            if tool_data:
                messages[-1] = {
                    "role": "user",
                    "content": messages[-1]["content"] + f"\n\n---\n\nСТРУКТУРИРОВАННЫЕ ДАННЫЕ ИЗ ИНСТРУМЕНТОВ:\n{tool_data[:20000]}"
                }
            yield {"data": _json.dumps({"type": "status", "content": "Анализирую данные..."})}
            async for chunk in llm_client.stream(system_prompt, messages):
                full_text += chunk
                yield {"data": _json.dumps({"type": "text_delta", "content": chunk})}
            yield {"data": _json.dumps({"type": "text_done"})}
        else:
            # ReAct agent stream for complex skills
            from app.services.react_agent import run_react_agent_stream
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

        verified_text = full_text

        # 6. Parse and stream response (only for ReAct path — RAG already streamed above)
        if skill_id not in SIMPLE_SKILLS:
            from app.services.response_parser import _parse_table, _parse_chart
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
                    chunk_size = 500
                    for i in range(0, len(part_stripped), chunk_size):
                        chunk = part_stripped[i:i+chunk_size]
                        yield {"data": json.dumps({"type": "text_delta", "content": chunk})}
                    yield {"data": json.dumps({"type": "text_done"})}

        # 7. Auto-generate PDF
        all_blocks = parse_llm_response(verified_text)
        if any(b.type == "table" for b in all_blocks) or len(verified_text) > 1500:
            pdf_block = _generate_pdf(all_blocks, message)
            if pdf_block:
                yield {"data": json.dumps({"type": "pdf_link", "data": pdf_block.data}, ensure_ascii=False)}

        yield {"data": json.dumps({"type": "done", "session_id": session_id})}

    except Exception as e:
        print(f"[STREAM ERROR] {e}")
        traceback.print_exc()
        yield {"data": json.dumps({"type": "text_delta", "content": f"⚠️ Ошибка: {e}"})}
        yield {"data": json.dumps({"type": "done", "session_id": session_id})}
