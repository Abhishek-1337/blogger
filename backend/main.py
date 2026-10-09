from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.auth import (
    create_access_token,
    get_current_user,
    get_or_create_user,
    verify_google_token,
)
from src.db import (
    SessionLocal,
    get_search_entry,
    list_search_entries,
    save_search_entry,
    save_usage_events,
    usage_for_entry,
    usage_per_query,
    usage_totals,
)
from src.graph import run_blog_with_usage
from src.models import SearchEntry, User
from src.usage import PRICING_PER_1M, UsageCollector, estimate_cost_usd

app = FastAPI(title="Blogger API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class BlogResponseWithUsage(BlogResponse):
    usage: UsageBlockOut | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1, description="Google ID token from GIS")


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    picture: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id, email=user.email, name=user.name, picture=user.picture
    )


@app.post("/auth/google", response_model=LoginResponse)
async def google_login(req: GoogleLoginRequest):
    try:
        claims = verify_google_token(req.id_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    async with SessionLocal() as session:
        user = await get_or_create_user(session, claims)
    return LoginResponse(
        token=create_access_token(user.id), user=_to_user_out(user)
    )


@app.get("/auth/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return _to_user_out(user)


class SearchSummaryOut(BaseModel):
    id: int
    query: str
    created_at: datetime
    outline_approved: bool


def _to_blog_response(entry: SearchEntry) -> BlogResponse:
    return BlogResponse(
        id=entry.id,
        query=entry.query,
        research_brief=entry.research_brief,
        outline=list(entry.outline or []),
        sections=list(entry.sections or []),
        outline_approved=entry.outline_approved,
        outline_revisions=entry.outline_revisions,
        outline_feedback=entry.outline_feedback,
    )


@app.get("/searches", response_model=list[SearchSummaryOut])
async def list_searches(limit: int = 50, user: User = Depends(get_current_user)):
    try:
        entries = await list_search_entries(min(max(limit, 1), 200), user.id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return [
        SearchSummaryOut(
            id=e.id,
            query=e.query,
            created_at=e.created_at,
            outline_approved=e.outline_approved,
        )
        for e in entries
    ]


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


def _row_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    return round(estimate_cost_usd("gpt-4o-mini", prompt_tokens, completion_tokens), 6)


async def _build_usage_summary(user_id: int | None, recent_limit: int) -> UsageSummaryOut:
    """Assemble the dashboard payload, optionally scoped to one user.

    ``user_id=None`` aggregates every user's queries (global dashboard).
    """
    totals = await usage_totals(user_id)
    recent = await usage_per_query(user_id, limit=recent_limit)
    tracked = totals["queries_tracked"]
    return UsageSummaryOut(
        totals=UsageTotalsOut(
            prompt_tokens=totals["prompt_tokens"],
            completion_tokens=totals["completion_tokens"],
            total_tokens=totals["total_tokens"],
            llm_calls=totals["llm_calls"],
            queries_tracked=tracked,
            avg_tokens_per_query=round(totals["total_tokens"] / tracked, 1)
            if tracked
            else 0.0,
            est_cost_usd=_row_cost_usd(
                totals["prompt_tokens"], totals["completion_tokens"]
            ),
        ),
        by_stage=[UsageStageOut(**r) for r in totals["by_stage"]],
        by_day=[UsageDayOut(**r) for r in totals["by_day"]],
        recent=[
            UsageQueryRowOut(
                **r,
                est_cost_usd=_row_cost_usd(r["prompt_tokens"], r["completion_tokens"]),
            )
            for r in recent
        ],
        pricing_per_1m_usd=PRICING_PER_1M,
        pricing_note="Cost is an estimate from public gpt-4o-mini rates.",
    )


@app.get("/usage/summary", response_model=UsageSummaryOut)
async def get_usage_summary(user: User = Depends(get_current_user)):
    """Dashboard aggregates for the signed-in user."""
    try:
        return await _build_usage_summary(user.id, recent_limit=10)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/usage/overview", response_model=UsageSummaryOut)
async def get_usage_overview(user: User = Depends(get_current_user)):
    """Global dashboard: every user's queries in one place.

    Still requires login; per-admin restriction is intentionally deferred
    until admin auth is added.
    """
    try:
        return await _build_usage_summary(None, recent_limit=50)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/usage/recent", response_model=list[UsageQueryRowOut])
async def get_usage_recent(
    limit: int = 50, user: User = Depends(get_current_user)
):
    """Per-query token rollup (newest first) for the dashboard table."""
    try:
        rows = await usage_per_query(user.id, min(max(limit, 1), 200))
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return [
        UsageQueryRowOut(
            **r,
            est_cost_usd=_row_cost_usd(r["prompt_tokens"], r["completion_tokens"]),
        )
        for r in rows
    ]


@app.get("/searches/{entry_id}/usage", response_model=list[UsageCallOut])
async def get_search_usage(entry_id: int, user: User = Depends(get_current_user)):
    """Per-LLM-call token breakdown for one stored query."""
    try:
        entry = await get_search_entry(entry_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if entry is None:
        raise HTTPException(status_code=404, detail="Search not found.")
    try:
        events = await usage_for_entry(entry_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return [
        UsageCallOut(
            id=e.id,
            stage=e.stage or "unknown",
            model=e.model or "gpt-4o-mini",
            prompt_tokens=e.prompt_tokens,
            completion_tokens=e.completion_tokens,
            total_tokens=e.total_tokens,
            latency_ms=e.latency_ms,
            created_at=e.created_at,
        )
        for e in events
    ]


@app.get("/searches/{entry_id}", response_model=BlogResponse)
async def get_search(entry_id: int, user: User = Depends(get_current_user)):
    try:
        entry = await get_search_entry(entry_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if entry is None:
        raise HTTPException(status_code=404, detail="Search not found.")
    return _to_blog_response(entry)


@app.post("/blog", response_model=BlogResponseWithUsage)
async def generate_blog(req: BlogRequest, user: User = Depends(get_current_user)):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query must not be empty.")
    try:
        final, usage_events = await run_in_threadpool(run_blog_with_usage, query)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blog generation failed: {e}")

    feedback = final.get("outline_feedback", "") or (
        "Outline approved." if final.get("outline_approved") else ""
    )
    try:
        entry_id = await save_search_entry(
            {
                "query": query,
                "research_brief": final.get("research_brief", ""),
                "outline": final.get("outline", []),
                "sections": final.get("sections", []),
                "outline_approved": final.get("outline_approved", False),
                "outline_revisions": final.get("outline_revisions", 0),
                "outline_feedback": feedback,
            },
            user.id,
        )
    except Exception as e:
        print(f"Warning: failed to persist search entry: {e}")
        entry_id = None
    try:
        await save_usage_events(usage_events, user.id, entry_id)
    except Exception as e:
        print(f"Warning: failed to persist usage events: {e}")
    usage_block = UsageBlockOut(
        **{
            k: v
            for k, v in _collector_summary(usage_events).items()
            if k in UsageBlockOut.model_fields
        }
    )
    return BlogResponseWithUsage(
        id=entry_id,
        query=query,
        research_brief=final.get("research_brief", ""),
        outline=final.get("outline", []),
        sections=final.get("sections", []),
        outline_approved=final.get("outline_approved", False),
        outline_revisions=final.get("outline_revisions", 0),
        outline_feedback=feedback,
        usage=usage_block,
    )


def _collector_summary(events: list[dict]) -> dict:
    """Summarize raw collector events into a UsageBlockOut-compatible dict."""
    collector = UsageCollector()
    collector.events = events
    return collector.summary()