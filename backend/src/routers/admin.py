"""Admin routes: global observability across all users.

Same DB and backend as the /usage routes, admin login required. The payload
builders live in shared so the two URL namespaces cannot drift apart.
"""

from fastapi import APIRouter, Depends
from src.auth import get_admin_user
from src.models import User

from src.types import UsageCallOut, UsageQueryRowOut, UsageSummaryOut

from .shared import (
    build_usage_summary,
    db_errors,
    entry_usage_calls,
    recent_usage_rows,
)

router = APIRouter()


@router.get("/admin/usage/summary", response_model=UsageSummaryOut)
@db_errors
async def get_admin_usage_summary(user: User = Depends(get_admin_user)):
    """Global token/cost aggregates across all users (admin only)."""
    return await build_usage_summary(None, recent_limit=50)


@router.get("/admin/usage/recent", response_model=list[UsageQueryRowOut])
@db_errors
async def get_admin_usage_recent(
    limit: int = 50, user: User = Depends(get_admin_user)
):
    """Global per-query token rollup, newest first (admin only)."""
    return await recent_usage_rows(None, limit)


@router.get("/admin/searches/{entry_id}/usage", response_model=list[UsageCallOut])
@db_errors
async def get_admin_search_usage(
    entry_id: int, user: User = Depends(get_admin_user)
):
    """Per-LLM-call token breakdown for any stored query (admin only)."""
    return await entry_usage_calls(entry_id)
