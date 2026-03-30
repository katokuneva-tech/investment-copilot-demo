from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.document_store import doc_store, DocumentMeta

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
async def list_documents():
    docs = doc_store.list_global()
    return {"documents": [d.model_dump() for d in docs]}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No filename")

    allowed = {"json", "pdf", "docx", "xlsx", "xls", "txt", "md", "csv"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {', '.join(allowed)}")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(400, "File too large (max 10MB)")

    meta = doc_store.add(content, file.filename, scope="global")
    return {"document": meta.model_dump()}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    if not doc_store.delete(doc_id):
        raise HTTPException(404, "Document not found or cannot be deleted")
    return {"status": "deleted"}


@router.get("/{doc_id}")
async def get_document(doc_id: str):
    meta = doc_store.get(doc_id)
    if not meta:
        raise HTTPException(404, "Document not found")
    return {"document": meta.model_dump()}


@router.patch("/{doc_id}/toggle")
async def toggle_document_active(doc_id: str):
    meta = doc_store.toggle_active(doc_id)
    if not meta:
        raise HTTPException(404, "Document not found")
    return {"document": meta.model_dump()}


@router.get("/{doc_id}/content")
async def get_document_content(doc_id: str):
    meta = doc_store.get(doc_id)
    if not meta:
        raise HTTPException(404, "Document not found")
    text = doc_store.get_text(doc_id)
    return {"document": meta.model_dump(), "content": text[:10000]}


@router.post("/session-upload")
async def upload_session_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    if not file.filename:
        raise HTTPException(400, "No filename")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")

    meta = doc_store.add(content, file.filename, scope="session", session_id=session_id)
    return {"document": meta.model_dump()}


@router.get("/session/{session_id}")
async def list_session_documents(session_id: str):
    docs = doc_store.list_session(session_id)
    return {"documents": [d.model_dump() for d in docs]}
