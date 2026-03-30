"""Multi-agent supervisor — classifies user intent and routes to appropriate skill."""
from app.services.llm_client import llm_client

SUPERVISOR_PROMPT = """Ты — оркестратор инвестиционного копилота АФК Система.
Определи тип запроса пользователя и выбери подходящего агента.

Доступные агенты:
- portfolio_analytics: вопросы о портфельных компаниях, финансах, росте, долгах, дивидендах, секторах, IPO, событиях, холдинге
- investment_analysis: анализ инвестиционных проектов, NPV, IRR, предпосылки, чувствительность, заключение для комитета
- market_research: анализ рынков, размер рынка, игроки, тренды, M&A, отраслевые обзоры
- benchmarking: сравнение компаний с аналогами, мультипликаторы, EV/EBITDA, маржа
- committee_advisor: анализ материалов комитета, противоречия между документами, риски сделки, рекомендации, красные флаги по портфельным компаниям, долговая нагрузка АФК, логика корпоративных сделок, скоркард, чеклист DD, драфт протокола

Верни ТОЛЬКО id агента (одно слово), ничего больше.
Пример ответа: portfolio_analytics"""

VALID_SKILLS = {"portfolio_analytics", "investment_analysis", "market_research", "benchmarking", "committee_advisor"}


async def classify_intent(message: str, history: list[dict] | None = None) -> str:
    """Classify user intent and return skill_id."""
    try:
        # Include last 2 history messages for context
        context_msgs = []
        if history:
            for h in history[-2:]:
                context_msgs.append({"role": h["role"], "content": h["content"][:200]})
        context_msgs.append({"role": "user", "content": message})

        result = await llm_client.chat(
            system=SUPERVISOR_PROMPT,
            messages=context_msgs,
            temperature=0.0,
        )
        skill_id = result.strip().lower().replace('"', '').replace("'", "")

        # Validate
        if skill_id in VALID_SKILLS:
            return skill_id

        # Try to extract from longer response
        for sid in VALID_SKILLS:
            if sid in skill_id:
                return sid

        # Default
        return "portfolio_analytics"
    except Exception:
        return "portfolio_analytics"
