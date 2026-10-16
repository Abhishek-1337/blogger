"""Shared web-layer helpers: converters, cost math, and error mapping.

Response/request types live in :mod:`src.types`, grouped by the routes
that use them (auth, blog, usage).
"""

import functools

from fastapi import HTTPException

from src.db import (
    get_search_entry,
    usage_for_entry_any,
    usage_per_query,
    usage_totals,
)
from src.models import SearchEntry, User
from src.types import (
    UsageBlockOut,
    UsageCallOut,
    UsageQueryRowOut,
    UsageStageOut,
    UsageSummaryOut,
    UsageDayOut,
    UsageTotalsOut,
    UserOut,
    BlogResponse,
)
from src.usage import PRICING_PER_1M, UsageCollector, estimate_cost_usd


def db_errors(fn):
    """Map ValueError from the DB layer to HTTP 500.

    Every handler previously repeated the same try/except; one decorator
    preserves that behavior. HTTPException (e.g. 404s) passes through.
    """

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))

    return wrapper


def to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id, email=user.email, name=user.name, picture=user.picture
    )


def to_blog_response(entry: SearchEntry) -> BlogResponse:
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


def to_usage_call_out(e) -> UsageCallOut:
    return UsageCallOut(
        id=e.id,
        stage=e.stage or "unknown",
        model=e.model or "gpt-4o-mini",
        prompt_tokens=e.prompt_tokens,
        completion_tokens=e.completion_tokens,
        total_tokens=e.total_tokens,
        latency_ms=e.latency_ms,
        created_at=e.created_at,
    )


def row_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    return round(estimate_cost_usd("gpt-4o-mini", prompt_tokens, completion_tokens), 6)


def summarize_collector_events(events: list[dict]) -> dict:
    """Summarize raw collector events into a UsageBlockOut-compatible dict."""
    collector = UsageCollector()
    collector.events = events
    return collector.summary()


async def build_usage_summary(
    user_id: int | None, recent_limit: int
) -> UsageSummaryOut:
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
            est_cost_usd=row_cost_usd(
                totals["prompt_tokens"], totals["completion_tokens"]
            ),
        ),
        by_stage=[UsageStageOut(**r) for r in totals["by_stage"]],
        by_day=[UsageDayOut(**r) for r in totals["by_day"]],
        recent=[
            UsageQueryRowOut(
                **r,
                est_cost_usd=row_cost_usd(r["prompt_tokens"], r["completion_tokens"]),
            )
            for r in recent
        ],
        pricing_per_1m_usd=PRICING_PER_1M,
        pricing_note="Cost is an estimate from public gpt-4o-mini rates.",
    )


async def recent_usage_rows(
    user_id: int | None, limit: int
) -> list[UsageQueryRowOut]:
    """Newest-first per-query token rollups, optionally scoped to one user."""
    rows = await usage_per_query(user_id, min(max(limit, 1), 200))
    return [
        UsageQueryRowOut(
            **r,
            est_cost_usd=row_cost_usd(r["prompt_tokens"], r["completion_tokens"]),
        )
        for r in rows
    ]


async def entry_usage_calls(entry_id: int) -> list[UsageCallOut]:
    """Per-LLM-call token breakdown for one stored query (any owner)."""
    entry = await get_search_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Search not found.")
    events = await usage_for_entry_any(entry_id)
    return [to_usage_call_out(e) for e in events]
