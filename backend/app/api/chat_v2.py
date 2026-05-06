"""
V2 Chat API — multi-agent architecture.
Runs alongside v1 endpoints without breaking existing functionality.
"""

import asyncio
import json
import time
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from app.models.schemas import ChatRequest
from app.services.analytics import log_request

router = APIRouter()


# Default limits (portfolio, market, benchmark — speed matters)
DOC_CHAR_LIMIT = 2000
MAX_TOTAL_CONTEXT = 25000
MAX_DOCS = 6

# Committee needs full documents for cross-document contradiction analysis
SKILL_LIMITS = {
    "committee_advisor": {"doc_char_limit": 8000, "max_total_context": 60000, "max_docs": 10},
    "investment_analysis": {"doc_char_limit": 6000, "max_total_context": 50000, "max_docs": 8},
}

# Which doc IDs are priority for each skill (reuse from skill_router)
SKILL_DOC_PRIORITY = {
    "committee_advisor": {"src_project", "src_finmodel", "src_appraiser", "src_mgmt", "src_legal_dd", "src_committee"},
    "investment_analysis": {"src_project", "src_finmodel", "src_appraiser", "src_mgmt", "src_legal_dd", "src_logistics", "src_jll"},
}


def _build_context_v2(skill_id: str, message: str, session_id: str,
                      attachment_ids: list[str] | None = None) -> str:
    """Build document context for v2 agents. Reuses existing doc store."""
    from app.services.document_store import doc_store
    from app.data.kb_loader import KB_OVERVIEW, KB_PORTFOLIO, KB_FINANCIALS

    limits = SKILL_LIMITS.get(skill_id, {})
    doc_char_limit = limits.get("doc_char_limit", DOC_CHAR_LIMIT)
    max_total_context = limits.get("max_total_context", MAX_TOTAL_CONTEXT)
    max_docs = limits.get("max_docs", MAX_DOCS)

    parts = []

    # 1. Knowledge base context (always include, compact)
    kb_text = f"## Обзор АФК Система\n{json.dumps(KB_OVERVIEW, ensure_ascii=False)[:2000]}"
    parts.append(kb_text)

    # 2. Portfolio data (compact)
    if KB_PORTFOLIO:
        portfolio_text = json.dumps(KB_PORTFOLIO, ensure_ascii=False)[:3000]
        parts.append(f"## Портфельные компании\n{portfolio_text}")

    # 3. Financial data (compact)
    if KB_FINANCIALS:
        fin_text = json.dumps(KB_FINANCIALS, ensure_ascii=False)[:3000]
        parts.append(f"## Финансовые данные\n{fin_text}")

    # 4. Collect and prioritize documents
    active_docs = [d for d in doc_store.list_global() if d.is_active]
    if session_id:
        active_docs += doc_store.list_session(session_id)
    if attachment_ids:
        seen_ids = {d.id for d in active_docs}
        active_docs += [d for d in doc_store.list_global()
                        if d.id in attachment_ids and d.id not in seen_ids]

    # Prioritize skill-specific docs first, then the rest
    priority_ids = SKILL_DOC_PRIORITY.get(skill_id, set())
    if priority_ids:
        priority_docs = [d for d in active_docs if d.id in priority_ids]
        other_docs = [d for d in active_docs if d.id not in priority_ids]
        active_docs = priority_docs + other_docs

    current_size = sum(len(p) for p in parts)
    for doc in active_docs[:max_docs]:
        if current_size >= max_total_context:
            break
        text = doc_store.get_text(doc.id)
        if text:
            truncated = text[:doc_char_limit] if len(text) > doc_char_limit else text
            part = f"## Документ: {doc.original_name}\n{truncated}"
            current_size += len(part)
            parts.append(part)

    return "\n\n---\n\n".join(parts)


@router.post("/api/v2/chat")
async def chat_v2(req: ChatRequest, request: Request):
    """Non-streaming v2 chat with multi-agent orchestration."""
    from app.agents.orchestrator import orchestrate

    user = getattr(request.state, "user_name", "anonymous")
    t0 = time.time()

    try:
        context = _build_context_v2(req.skill_id, req.message, req.session_id, req.attachment_ids)

        result = await orchestrate(
            skill_id=req.skill_id,
            message=req.message,
            context=context,
            history=req.history,
        )

        elapsed_ms = int((time.time() - t0) * 1000)
        log_request(user, f"v2_{result.use_case}", req.message, elapsed_ms, provider="multi-agent")

        # Parse response into content blocks
        from app.services.response_parser import parse_llm_response
        blocks = parse_llm_response(result.final_answer)

        # Add agent metadata block
        agent_meta = {
            "type": "agents_info",
            "data": {
                "use_case": result.use_case,
                "agents_used": result.agents_used,
                "total_elapsed_sec": result.total_elapsed_sec,
                "agent_details": [
                    {
                        "name": r.agent_name,
                        "role": r.role,
                        "elapsed_sec": r.elapsed_sec,
                        "has_error": bool(r.error),
                    }
                    for r in result.agent_results
                ],
            },
        }

        return {
            "blocks": [b.model_dump() for b in blocks] + [agent_meta],
            "session_id": req.session_id,
        }

    except Exception as e:
        log_request(user, f"v2_{req.skill_id}", req.message,
                    int((time.time() - t0) * 1000), status="error", error=str(e))
        raise


@router.post("/api/v2/chat/stream")
async def chat_v2_stream(req: ChatRequest, request: Request):
    """Streaming v2 chat — emits agent progress + synthesized answer."""
    from app.agents.orchestrator import orchestrate_stream

    user = getattr(request.state, "user_name", "anonymous")
    t0 = time.time()

    async def event_stream():
        try:
            context = _build_context_v2(
                req.skill_id, req.message, req.session_id, req.attachment_ids
            )

            # Track time between events for heartbeat (prevents proxy/client timeouts)
            last_event_time = time.monotonic()
            async for event_data in orchestrate_stream(
                skill_id=req.skill_id,
                message=req.message,
                context=context,
                history=req.history,
            ):
                # Send heartbeat if >15s since last event
                now = time.monotonic()
                if now - last_event_time > 15:
                    yield {"data": json.dumps({"type": "heartbeat"})}
                last_event_time = now
                yield {"data": event_data}

            elapsed_ms = int((time.time() - t0) * 1000)
            log_request(user, f"v2_{req.skill_id}", req.message, elapsed_ms, provider="multi-agent")

        except BaseException as e:
            log_request(user, f"v2_{req.skill_id}", req.message,
                        int((time.time() - t0) * 1000), status="error", error=f"{type(e).__name__}: {e}")
            yield {"data": json.dumps({"type": "error", "content": f"{type(e).__name__}: {e}"})}
            yield {"data": json.dumps({"type": "done", "session_id": req.session_id})}

    return EventSourceResponse(event_stream())
