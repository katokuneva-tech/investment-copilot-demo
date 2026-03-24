from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any
import uuid


class ChatRequest(BaseModel):
    skill_id: str
    message: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


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
