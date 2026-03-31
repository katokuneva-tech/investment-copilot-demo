from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any
import uuid


class ChatRequest(BaseModel):
    skill_id: str
    message: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    attachment_ids: list[str] = []
    history: list[dict] = []  # [{role: "user"|"assistant", content: "..."}]


class ContentBlock(BaseModel):
    type: str  # text | table | chart | pdf_link | sources
    data: Any


class ChatResponse(BaseModel):
    blocks: list[ContentBlock]
    session_id: str


class TableData(BaseModel):
    headers: list[str]
    rows: list[list[Any]]
    caption: str = ""


class ChartData(BaseModel):
    chart_type: str  # bar | line
    title: str
    x_key: str
    series: list[dict]
    data: list[dict]


class PdfLink(BaseModel):
    report_id: str
    title: str
    description: str


class SourceRef(BaseModel):
    id: str
    title: str
    type: str
    page: str = ""


# --- News Monitoring ---

class PortfolioImpact(BaseModel):
    company_slug: str
    metric: str
    direction: str  # "positive" | "negative" | "risk" | "opportunity"
    context: str


class NewsArticle(BaseModel):
    id: str
    company_slug: str
    company_name: str
    title: str
    url: str
    snippet: str
    source: str  # domain extracted from url
    published_approx: str = ""
    sentiment: str = "neutral"  # "positive" | "negative" | "neutral"
    summary: str = ""
    alert_type: str | None = None  # "ipo" | "management" | "legal" | "rating" | "deal" | "debt"
    portfolio_impact: PortfolioImpact | None = None


class NewsAlert(BaseModel):
    id: str
    company_slug: str
    company_name: str
    alert_type: str
    title: str
    description: str
    severity: str = "medium"  # "high" | "medium" | "low"


class NewsDashboard(BaseModel):
    total: int
    positive: int
    negative: int
    neutral: int
    sentiment_by_company: list[dict]  # [{slug, name, positive, negative, neutral}]
    alerts: list[NewsAlert]
    top_companies: list[dict]  # [{slug, name, count}]


class NewsResponse(BaseModel):
    articles: list[NewsArticle]
    last_updated: str
    companies: list[dict]  # [{slug, name, article_count}]


class DigestResponse(BaseModel):
    digest: str  # markdown
    period: str
    article_count: int
    generated_at: str
