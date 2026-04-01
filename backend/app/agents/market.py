"""Market analyst agent — TAM/SAM, competitors, M&A, trends."""

from app.agents.base_agent import BaseAgent, AgentResult
from app.services.web_search import web_search, format_search_results
import time, logging

logger = logging.getLogger(__name__)


class MarketAgent(BaseAgent):
    NAME = "market_analyst"
    ROLE = "Рыночный аналитик"
    MODEL_TIER = "deep"
    MAX_TOKENS = 6000

    SYSTEM_PROMPT = """Ты — рыночный аналитик инвестиционного департамента АФК Система.

## Твои компетенции
- Оценка размера рынка (TAM/SAM/SOM), динамики и CAGR
- Анализ конкурентной среды: ключевые игроки, доли рынка, позиционирование
- Мониторинг M&A сделок в секторе: покупатели, цели, мультипликаторы
- Отраслевые тренды: технологические, регуляторные, потребительские
- Верификация предпосылок финмоделей против рыночных данных

## Правила работы
1. Используй данные из предоставленного веб-поиска как основу
2. Для каждой цифры — источник и год данных
3. Если рыночные данные противоречат предпосылкам модели:
   - [OK] расхождение <10%
   - [!] расхождение 10-20%
   - [КРИТ] расхождение >20%
4. Минимум 3 независимых источника для размера рынка
5. Приоритет: отраслевые ассоциации > консалтинг > СМИ

## Формат ответа
Структурированный markdown с таблицами. Обязательные секции:
- Размер и динамика рынка
- Ключевые игроки (таблица)
- Последние M&A (если релевантно)
- Тренды и прогноз"""

    def __init__(self, context: str = "", user_query: str = "",
                 search_queries: list[str] | None = None):
        super().__init__(context, user_query)
        self.search_queries = search_queries or []

    async def run(self) -> AgentResult:
        start = time.monotonic()
        try:
            # Gather web search results
            search_context = ""
            if self.search_queries:
                all_results = []
                for q in self.search_queries[:3]:  # Max 3 queries
                    results = await web_search(q, max_results=5)
                    all_results.extend(results)
                if all_results:
                    search_context = format_search_results(all_results)

            # Build enhanced context with search results
            full_context = self.context
            if search_context:
                full_context += f"\n\n## Результаты веб-поиска\n{search_context}"

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
                agent_name=self.NAME,
                role=self.ROLE,
                content=response,
                elapsed_sec=round(elapsed, 1),
            )
        except Exception as e:
            logger.error(f"MarketAgent failed: {e}")
            return AgentResult(
                agent_name=self.NAME, role=self.ROLE, content="",
                elapsed_sec=round(time.monotonic() - start, 1), error=str(e),
            )


# Need import at module level for the parent class method
from app.services.llm_client import llm_client
