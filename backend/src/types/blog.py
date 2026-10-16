"""Request/response types for the blog and stored-search routes."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.types.usage import UsageBlockOut


class BlogRequest(BaseModel):
    query: str = Field(min_length=1, description="Blog topic / user query")


class OutlineSectionOut(BaseModel):
    title: str
    bullets: list[str]


class BlogResponse(BaseModel):
    id: int | None = None
    query: str
    research_brief: str
    outline: list[str]
    sections: list[OutlineSectionOut]
    outline_approved: bool
    outline_revisions: int
    outline_feedback: str


class BlogResponseWithUsage(BlogResponse):
    usage: UsageBlockOut | None = None


class SearchSummaryOut(BaseModel):
    id: int
    query: str
    created_at: datetime
    outline_approved: bool
