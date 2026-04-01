"""Benchmark analyst agent — peer comparison, multiples, valuation."""

from app.agents.base_agent import BaseAgent, AgentResult
from app.services.web_search import web_search, format_search_results
import time, logging

logger = logging.getLogger(__name__)


class BenchmarkAgent(BaseAgent):
    NAME = "benchmark_analyst"
    ROLE = "Бенчмарк-аналитик"
    MODEL_TIER = "standard"  # Sonnet
    MAX_TOKENS = 2500

    SYSTEM_PROMPT = """Ты — аналитик по оценке компаний инвестиционного департамента АФК Система.

## Твои компетенции
- Подбор аналогов (peers) для портфельных компаний и целей M&A
- Расчёт и сравнение мультипликаторов: EV/EBITDA, EV/Revenue, P/E, P/BV
- Implied valuation: применение медианного мультипликатора аналогов к EBITDA компании
- Анализ премий/дисконтов к медиане peers
- Расчёт GAP analysis: в чём компания лучше/хуже медианы

## Правила работы
1. Минимум 3-5 аналогов для каждой компании (Россия + международные)
2. Данные из публичной отчётности, MOEX, годовых отчётов
3. Для каждой цифры — источник и период
4. Расчёт premium/discount = (company_multiple / peer_median - 1) * 100%
5. Маркировка:
   - Премия >20%: [ПЕРЕОЦ]
   - Дисконт >15%: [НЕДООЦ]
   - В пределах ±10%: [СПРАВЕДЛ]

## Формат ответа
1. **Таблица аналогов**: Компания | Сектор | Выручка | EBITDA | Маржа | EV/EBITDA | Рост | Источник
2. **Медианные мультипликаторы**: EV/EBITDA, EV/Revenue, P/E
3. **Implied valuation**: Implied EV = EBITDA * медианный мультипликатор
4. **Премия/дисконт**: расчёт + обоснование (рост? маржа? качество актива?)
5. **Вывод**: справедливая оценка / недооценена / переоценена"""

    def __init__(self, context: str = "", user_query: str = "",
                 search_queries: list[str] | None = None):
        super().__init__(context, user_query)
        self.search_queries = search_queries or []

    async def run(self) -> AgentResult:
        start = time.monotonic()
        try:
            search_context = ""
            if self.search_queries:
                all_results = []
                for q in self.search_queries[:2]:  # Max 2 queries (was 3)
                    results = await web_search(q, max_results=3)
                    all_results.extend(results)
                if all_results:
                    search_context = format_search_results(all_results)

            full_context = self.context
            if search_context:
                full_context += f"\n\n## Данные аналогов (веб-поиск)\n{search_context}"

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
            logger.error(f"BenchmarkAgent failed: {e}")
            return AgentResult(
                agent_name=self.NAME, role=self.ROLE, content="",
                elapsed_sec=round(time.monotonic() - start, 1), error=str(e),
            )


from app.services.llm_client import llm_client
