"""Request/response types for the usage observability routes."""

from datetime import datetime

from pydantic import BaseModel


class UsageStageOut(BaseModel):
    stage: str
    calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int = 0
    avg_latency_ms: int = 0


class UsageBlockOut(BaseModel):
    calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    est_cost_usd: float
    by_stage: list[UsageStageOut] = []


class UsageCallOut(BaseModel):
    id: int
    stage: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    created_at: datetime


class UsageQueryRowOut(BaseModel):
    id: int
    query: str
    created_at: str
    calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    est_cost_usd: float
    user_email: str = ""


class UsageTotalsOut(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    llm_calls: int
    queries_tracked: int
    avg_tokens_per_query: float
    est_cost_usd: float


class UsageDayOut(BaseModel):
    day: str
    calls: int
    total_tokens: int
    queries: int


class UsageSummaryOut(BaseModel):
    totals: UsageTotalsOut
    by_stage: list[UsageStageOut]
    by_day: list[UsageDayOut]
    recent: list[UsageQueryRowOut]
    pricing_per_1m_usd: dict[str, dict[str, float]]
    pricing_note: str
