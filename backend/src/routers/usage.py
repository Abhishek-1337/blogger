"""Usage observability routes (admin only, own-query scope)."""

from fastapi import APIRouter, Depends
from src.auth import get_admin_user
from src.models import User

from .shared import (
    UsageQueryRowOut,
    UsageSummaryOut,
    UsageCallOut,
    build_usage_summary,
    db_errors,
    entry_usage_calls,
    recent_usage_rows,
)

router = APIRouter()


@router.get("/usage/summary", response_model=UsageSummaryOut)
@db_errors
async def get_usage_summary(user: User = Depends(get_admin_user)):
    """Dashboard aggregates for the signed-in admin (own queries)."""
    return await build_usage_summary(user.id, recent_limit=10)


@router.get("/usage/overview", response_model=UsageSummaryOut)
@db_errors
async def get_usage_overview(user: User = Depends(get_admin_user)):
    """Global dashboard: every user's queries in one place (admin only)."""
    return await build_usage_summary(None, recent_limit=50)


@router.get("/usage/recent", response_model=list[UsageQueryRowOut])
@db_errors
async def get_usage_recent(
    limit: int = 50, user: User = Depends(get_admin_user)
):
    """Per-query token rollup (newest first) for the admin (own queries)."""
    return await recent_usage_rows(user.id, limit)


@router.get("/searches/{entry_id}/usage", response_model=list[UsageCallOut])
@db_errors
async def get_search_usage(entry_id: int, user: User = Depends(get_admin_user)):
    """Per-LLM-call token breakdown for one stored query (admin only)."""
    return await entry_usage_calls(entry_id)
