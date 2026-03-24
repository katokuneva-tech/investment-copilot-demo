from abc import ABC, abstractmethod
from app.models.schemas import ChatResponse


class BaseSkill(ABC):
    @abstractmethod
    async def handle(self, message: str, session_id: str) -> ChatResponse:
        ...

    def _match(self, message: str, keywords: list[str]) -> bool:
        msg = message.lower()
        return any(kw in msg for kw in keywords)
