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


@router.get("/usage/summary", response_model=UsageSummaryOut)
@db_errors
async def get_usage_summary(user: User = Depends(get_admin_user)):
    return await build_usage_summary(user.id, recent_limit=10)


@router.get("/usage/overview", response_model=UsageSummaryOut)
@db_errors
async def get_usage_overview(user: User = Depends(get_admin_user)):
    return await build_usage_summary(None, recent_limit=50)


@router.get("/usage/recent", response_model=list[UsageQueryRowOut])
@db_errors
async def get_usage_recent(limit: int = 50, user: User = Depends(get_admin_user)):
    return await recent_usage_rows(user.id, limit)


@router.get("/searches/{entry_id}/usage", response_model=list[UsageCallOut])
@db_errors
async def get_search_usage(entry_id: int, user: User = Depends(get_admin_user)):
    return await entry_usage_calls(entry_id)
