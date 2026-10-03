from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.db import save_search_entry
from src.graph import run_blog

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


@app.post("/blog", response_model=BlogResponse)
async def generate_blog(req: BlogRequest):
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
            }
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