from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException

from src.auth import get_current_user
from src.db import (
    get_search_entry,
    list_search_entries,
)
from src.models import User
from src.services.celery_app import celery_app
from src.types import (
    BlogRequest,
    BlogResponse,
    EnqueueResponse,
    SearchSummaryOut,
    TaskStatusResponse,
)
from src.worker import generate_blog as generate_blog_task

from .shared import db_errors, to_blog_response

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


@router.post("/blog/enqueue", response_model=EnqueueResponse, status_code=202)
@db_errors
async def enqueue_blog(req: BlogRequest, user: User = Depends(get_current_user)):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query must not be empty.")
    try:
        task = generate_blog_task.delay(query, user.id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {e}")
    return EnqueueResponse(task_id=task.id, status="queued")


@router.get("/blog/tasks/{task_id}", response_model=TaskStatusResponse)
@db_errors
async def get_blog_task(task_id: str, user: User = Depends(get_current_user)):
    try:
        result = AsyncResult(task_id, app=celery_app)
        state = result.state
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {e}")
    if state == "SUCCESS":
        payload = result.result or {}
        return TaskStatusResponse(
            task_id=task_id,
            status="SUCCESS",
            entry_id=payload.get("entry_id"),
            outline_approved=payload.get("outline_approved"),
            total_tokens=payload.get("total_tokens"),
            est_cost_usd=payload.get("est_cost_usd"),
        )
    if state == "FAILURE":
        return TaskStatusResponse(
            task_id=task_id, status="FAILURE", error=str(result.result)
        )
    message = None
    stage = None
    if isinstance(result.info, dict):
        message = result.info.get("message")
        stage = result.info.get("stage")
    return TaskStatusResponse(
        task_id=task_id, status=state, stage=stage, message=message
    )
