"""Blog routes: generation plus stored-search reads."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from src.auth import get_current_user, is_admin
from src.db import (
    get_search_entry,
    list_search_entries,
    save_search_entry,
    save_usage_events,
)
from src.graph import run_blog_with_usage
from src.models import User

from src.types import (
    BlogRequest,
    BlogResponse,
    BlogResponseWithUsage,
    SearchSummaryOut,
    UsageBlockOut,
)

from .shared import (
    db_errors,
    summarize_collector_events,
    to_blog_response,
)

router = APIRouter()


@router.get("/searches", response_model=list[SearchSummaryOut])
@db_errors
async def list_searches(limit: int = 50, user: User = Depends(get_current_user)):
    entries = await list_search_entries(min(max(limit, 1), 200), user.id)
    return [
        SearchSummaryOut(
            id=e.id,
            query=e.query,
            created_at=e.created_at,
            outline_approved=e.outline_approved,
        )
        for e in entries
    ]


@router.get("/searches/{entry_id}", response_model=BlogResponse)
@db_errors
async def get_search(entry_id: int, user: User = Depends(get_current_user)):
    entry = await get_search_entry(entry_id, user.id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Search not found.")
    return to_blog_response(entry)


@router.post("/blog", response_model=BlogResponseWithUsage)
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
    # Token/cost data is admin-only: regular users get no usage block.
    usage_block = None
    if is_admin(user):
        usage_block = UsageBlockOut(
            **{
                k: v
                for k, v in summarize_collector_events(usage_events).items()
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
