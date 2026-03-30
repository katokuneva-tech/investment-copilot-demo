import json
import time
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from app.models.schemas import ChatRequest
from app.services import skill_router
from app.services.analytics import log_request

router = APIRouter()


@router.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    t0 = time.time()
    user = getattr(request.state, "user_name", "anonymous")
    try:
        response = await skill_router.route(
            req.skill_id, req.message, req.session_id,
            req.attachment_ids, req.history
        )
        log_request(user, req.skill_id, req.message, int((time.time() - t0) * 1000))
        return response
    except Exception as e:
        log_request(user, req.skill_id, req.message, int((time.time() - t0) * 1000), status="error", error=str(e))
        raise


@router.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    user = getattr(request.state, "user_name", "anonymous")
    t0 = time.time()

    async def logged_stream():
        try:
            async for event in skill_router.route_stream(
                req.skill_id, req.message, req.session_id,
                req.attachment_ids, req.history
            ):
                yield event
            from app.services.llm_client import llm_client
            log_request(user, req.skill_id, req.message, int((time.time() - t0) * 1000), provider=llm_client.provider)
        except Exception as e:
            log_request(user, req.skill_id, req.message, int((time.time() - t0) * 1000), status="error", error=str(e))
            yield {"data": json.dumps({"type": "text_delta", "content": f"Error: {e}"})}
            yield {"data": json.dumps({"type": "done", "session_id": req.session_id})}

    return EventSourceResponse(logged_stream())


@router.post("/api/chat/pre-analysis")
async def pre_analysis(request: Request):
    """Generate pre-analysis brief for committee documents."""
    from app.services.document_store import doc_store
    from app.services.llm_client import llm_client

    user = getattr(request.state, "user_name", "anonymous")

    # Gather all committee-relevant docs
    docs = []
    for d in doc_store.list_global():
        if d.id.startswith("src_project") or d.id.startswith("src_finmodel") or \
           d.id.startswith("src_appraiser") or d.id.startswith("src_mgmt") or \
           d.id.startswith("src_legal_dd") or d.id.startswith("src_committee") or \
           (not d.id.startswith("src_") and d.id != "kb_default"):
            if d.is_active:
                text = doc_store.get_text(d.id)
                if text:
                    docs.append({"name": d.original_name, "type": d.file_type, "size": d.size_bytes, "preview": text[:2000]})

    if not docs:
        return {"brief": "Нет загруженных документов для анализа. Загрузите материалы сделки."}

    # Build context
    doc_summary = "\n\n".join([f"=== {d['name']} ({d['type']}) ===\n{d['preview']}" for d in docs])

    prompt = f"""Проведи PRE-ANALYSIS BRIEF по загруженным документам сделки.

ДОКУМЕНТЫ ({len(docs)} шт.):
{doc_summary}

ЗАДАЧА — выдай краткую сводку по шаблону:

1. ИНВЕНТАРИЗАЦИЯ: перечисли все документы, их тип и статус обработки
2. КЛЮЧЕВЫЕ МЕТРИКИ СДЕЛКИ: тип сделки, объём инвестиций (CAPEX), IRR, NPV, payback, горизонт
3. ПЕРЕКРЁСТНАЯ ПРОВЕРКА: сравни ключевые цифры между документами, отметь расхождения
4. RED FLAGS: нереалистичные допущения, отсутствие стресс-тестов, завышенные прогнозы
5. РЕКОМЕНДАЦИЯ: на что обратить внимание в первую очередь

Будь СКЕПТИЧЕН. Ищи слабые места. Не используй emoji. Используй маркеры [КРИТ], [ВЫСОК], [СРЕДН]."""

    try:
        t0 = time.time()
        response = await llm_client.chat(
            "Ты — скептичный аналитик инвестиционного комитета. Кратко, по делу, с цифрами.",
            [{"role": "user", "content": prompt}],
        )
        elapsed = int((time.time() - t0) * 1000)
        log_request(user, "pre_analysis", f"Pre-analysis brief ({len(docs)} docs)", elapsed, provider=llm_client.provider)
        return {"brief": response, "doc_count": len(docs)}
    except Exception as e:
        return {"brief": f"Ошибка генерации: {e}", "doc_count": len(docs)}


@router.post("/api/export")
async def export_response(body: dict):
    """Export chat blocks as PDF."""
    from app.services.pdf_generator import ReportPDF
    blocks = body.get("blocks", [])
    title = body.get("title", "Ответ копилота")

    pdf = ReportPDF(title)
    pdf.add_title_page(subtitle=title, date="Март 2026")
    pdf.pdf.add_page()
    for block in blocks:
        btype = block.get("type", "")
        if btype == "text":
            text = block.get("data", "")
            sections = text.split("\n## ")
            for i, part in enumerate(sections):
                if part.strip():
                    lines = part.split("\n")
                    heading = lines[0].strip("# ") if i > 0 else ""
                    body_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else part.strip()
                    if heading:
                        pdf.add_section(heading, body_text)
                    else:
                        pdf.add_section("", body_text)
        elif btype == "table":
            data = block.get("data", {})
            headers = data.get("headers", [])
            rows = data.get("rows", [])
            if headers and rows:
                pdf.add_table(headers, rows)
    report_id, _ = pdf.save()
    return {"report_id": report_id, "url": f"/api/reports/{report_id}"}
