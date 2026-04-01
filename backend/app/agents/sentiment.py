"""Sentiment analyst agent — news monitoring, ESG, reputation."""

from app.agents.base_agent import BaseAgent, AgentResult
from app.services.web_search import web_search, format_search_results
import time, logging

logger = logging.getLogger(__name__)


class SentimentAgent(BaseAgent):
    NAME = "sentiment_analyst"
    ROLE = "Аналитик сентимента"
    MODEL_TIER = "standard"  # Sonnet — less critical task
    MAX_TOKENS = 3000

    SYSTEM_PROMPT = """Ты — аналитик информационных рисков инвестиционного департамента АФК Система.

## Твои компетенции
- Мониторинг новостного фона по портфельным компаниям и целям сделок
- Оценка медиа-тональности: positive / neutral / negative
- Идентификация репутационных рисков: иски, скандалы, санкции
- ESG-мониторинг: экология, трудовые отношения, governance
- Оценка рыночного настроения и медиа-восприятия

## Правила работы
1. Используй результаты веб-поиска как основу
2. Для каждого факта — источник, дата, URL
3. Классифицируй каждую новость: [ПОЗИТИВ] / [НЕГАТИВ] / [НЕЙТРАЛ]
4. Выдели алерты: судебные иски, санкции, проверки ФАС/ФНС, экоинциденты
5. НЕ отправляй в поиск конфиденциальные данные из документов
6. Анализируй ТОЛЬКО компании из контекста. НЕ добавляй компании которых нет в портфеле АФК Система. Если не уверен что компания портфельная — не включай её

## Формат ответа
- **Сводка тональности**: X позитивных, Y негативных, Z нейтральных
- **Ключевые новости**: таблица с датой, заголовком, тональностью, источником
- **Алерты**: [КРИТ] / [ВЫСОК] / [СРЕДН] — описание репутационного риска
- **ESG-факторы**: если есть информация
- **Вывод**: 2-3 предложения об информационном фоне"""

    def __init__(self, context: str = "", user_query: str = "",
                 companies: list[str] | None = None):
        super().__init__(context, user_query)
        self.companies = companies or []

    async def run(self) -> AgentResult:
        start = time.monotonic()
        try:
            # Search news for each company
            search_context = ""
            if self.companies:
                all_results = []
                for company in self.companies[:3]:  # Max 3 companies (was 5)
                    results = await web_search(
                        f"{company} новости 2025 2026", max_results=3
                    )
                    all_results.extend(results)
                if all_results:
                    search_context = format_search_results(all_results)

            full_context = self.context
            if search_context:
                full_context += f"\n\n## Новости из веб-поиска\n{search_context}"

            messages = [{"role": "user", "content": f"## Контекст\n{full_context}\n\n## Задача\n{self.user_query}"}]

            response = await llm_client.chat(
                system=self.SYSTEM_PROMPT,
                messages=messages,
                temperature=0.15,
                tier=self.MODEL_TIER,
                max_tokens=self.MAX_TOKENS,
            )
            elapsed = time.monotonic() - start
            return AgentResult(
                agent_name=self.NAME, role=self.ROLE, content=response,
                elapsed_sec=round(elapsed, 1),
            )
        except Exception as e:
            logger.error(f"SentimentAgent failed: {e}")
            return AgentResult(
                agent_name=self.NAME, role=self.ROLE, content="",
                elapsed_sec=round(time.monotonic() - start, 1), error=str(e),
            )


from app.services.llm_client import llm_client
