"""News monitoring API endpoints."""
from fastapi import APIRouter, Query
from app.services.news_service import (
    get_news, get_dashboard, get_alerts, get_companies,
    refresh_news, generate_digest,
)

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/companies")
async def list_companies():
    return get_companies()


@router.get("/feed")
async def news_feed(
    company: str | None = Query(None),
    sentiment: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    return await get_news(company=company, sentiment=sentiment, limit=limit)


@router.get("/dashboard")
async def dashboard():
    return await get_dashboard()


@router.get("/alerts")
async def alerts():
    return await get_alerts()


@router.post("/refresh")
async def force_refresh():
    data = await refresh_news()
    return {
        "articles": data.get("articles", []),
        "last_updated": data.get("last_updated", ""),
        "companies": data.get("companies", []),
    }


@router.post("/digest")
async def digest(body: dict = {}):
    period = body.get("period", "day")
    return await generate_digest(period=period)
