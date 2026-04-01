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


DOC_CHAR_LIMIT = 2000  # chars per document — keep compact for speed
MAX_TOTAL_CONTEXT = 25000  # hard cap on total context size
MAX_DOCS = 6  # max documents to include


def _build_context_v2(skill_id: str, message: str, session_id: str,
                      attachment_ids: list[str] | None = None) -> str:
    """Build document context for v2 agents. Reuses existing doc store."""
    from app.services.document_store import doc_store
    from app.data.kb_loader import KB_OVERVIEW, KB_PORTFOLIO, KB_FINANCIALS

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

    # 4. Uploaded documents (session + global)
    active_docs = [d for d in doc_store.list_global() if d.is_active]
    if session_id:
        active_docs += doc_store.list_session(session_id)
    if attachment_ids:
        active_docs += [d for d in doc_store.list_global()
                        if d.id in attachment_ids and d not in active_docs]

    current_size = sum(len(p) for p in parts)
    for doc in active_docs[:MAX_DOCS]:
        if current_size >= MAX_TOTAL_CONTEXT:
            break
        text = doc_store.get_text(doc.id)
        if text:
            truncated = text[:DOC_CHAR_LIMIT] if len(text) > DOC_CHAR_LIMIT else text
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

        except Exception as e:
            log_request(user, f"v2_{req.skill_id}", req.message,
                        int((time.time() - t0) * 1000), status="error", error=str(e))
            yield {"data": json.dumps({"type": "error", "content": str(e)})}
            yield {"data": json.dumps({"type": "done", "session_id": req.session_id})}

    return EventSourceResponse(event_stream())
