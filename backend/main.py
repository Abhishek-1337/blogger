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
from src.db import SessionLocal, get_search_entry, list_search_entries, save_search_entry
from src.graph import run_blog
from src.models import SearchEntry, User

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


@app.get("/searches/{entry_id}", response_model=BlogResponse)
async def get_search(entry_id: int, user: User = Depends(get_current_user)):
    try:
        entry = await get_search_entry(entry_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if entry is None:
        raise HTTPException(status_code=404, detail="Search not found.")
    return _to_blog_response(entry)


@app.post("/blog", response_model=BlogResponse)
async def generate_blog(req: BlogRequest, user: User = Depends(get_current_user)):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query must not be empty.")
    try:
        final = await run_in_threadpool(run_blog, query)
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
    return BlogResponse(
        id=entry_id,
        query=query,
        research_brief=final.get("research_brief", ""),
        outline=final.get("outline", []),
        sections=final.get("sections", []),
        outline_approved=final.get("outline_approved", False),
        outline_revisions=final.get("outline_revisions", 0),
        outline_feedback=feedback,
    )