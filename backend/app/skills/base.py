from abc import ABC, abstractmethod
from app.models.schemas import ChatResponse, ContentBlock


class BaseSkill(ABC):
    @abstractmethod
    async def handle(self, message: str, session_id: str, extra_context: str = "") -> ChatResponse:
        ...

    def _match(self, message: str, keywords: list[str]) -> bool:
        msg = message.lower()
        return any(kw in msg for kw in keywords)

    def _sources_block(self) -> ContentBlock:
        """Generate sources block dynamically from document store."""
        from app.services.document_store import doc_store
        sources = []
        for doc in doc_store.list_global():
            sources.append({
                "id": f"doc_{doc.id}",
                "title": doc.original_name,
                "type": doc.file_type,
                "page": "",
            })
        if not sources:
            sources.append({"id": "src_none", "title": "Нет загруженных документов", "type": "info", "page": ""})
        return ContentBlock(type="sources", data=sources)
