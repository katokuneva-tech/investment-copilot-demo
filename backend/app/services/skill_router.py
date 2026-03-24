from app.models.schemas import ChatResponse, ContentBlock
from app.skills.portfolio_analytics import PortfolioAnalyticsSkill
from app.skills.investment_analysis import InvestmentAnalysisSkill
from app.skills.market_research import MarketResearchSkill
from app.skills.benchmarking import BenchmarkingSkill
from app.skills.committee_advisor import CommitteeAdvisorSkill

SKILL_MAP = {
    "portfolio_analytics": PortfolioAnalyticsSkill(),
    "investment_analysis": InvestmentAnalysisSkill(),
    "market_research": MarketResearchSkill(),
    "benchmarking": BenchmarkingSkill(),
    "committee_advisor": CommitteeAdvisorSkill(),
}


async def route(skill_id: str, message: str, session_id: str) -> ChatResponse:
    skill = SKILL_MAP.get(skill_id)
    if not skill:
        return ChatResponse(
            session_id=session_id,
            blocks=[ContentBlock(type="text", data=f"Скилл '{skill_id}' не найден. Доступные: {', '.join(SKILL_MAP.keys())}")]
        )
    response = await skill.handle(message, session_id)
    response.session_id = session_id
    return response
