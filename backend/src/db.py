import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models import LlmUsageEvent, SearchEntry, User

load_dotenv()


def _normalize_db_url(url: str) -> str:
    url = url.strip()
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "channel_binding"]
    return urlunsplit(parts._replace(query=urlencode(query)))


raw_url = os.getenv("DATABASE_URL")
if not raw_url:
    raise RuntimeError("DATABASE_URL is not set")
DATABASE_URL = _normalize_db_url(raw_url)

ssl_mode = os.getenv("DATABASE_SSL", "").lower().strip()
if ssl_mode in ("require", "true", "1"):
    connect_args = {"ssl": "require"}
elif ssl_mode in ("disable", "false", "0"):
    connect_args = {}
elif "@localhost" in DATABASE_URL or "@127.0.0.1" in DATABASE_URL or "localhost:" in DATABASE_URL:
    connect_args = {}
else:
    connect_args = {"ssl": "require"}

engine = create_async_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def save_search_entry(data: dict, user_id: int | None = None) -> int:
    async with SessionLocal() as session:
        entry = SearchEntry(
            user_id=user_id,
            query=data.get("query", ""),
            research_brief=data.get("research_brief", ""),
            outline=data.get("outline", []),
            sections=data.get("sections", []),
            outline_approved=data.get("outline_approved", False),
            outline_revisions=data.get("outline_revisions", 0),
            outline_feedback=data.get("outline_feedback", ""),
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return entry.id


async def list_search_entries(limit: int = 50, user_id: int | None = None) -> list[SearchEntry]:
    async with SessionLocal() as session:
        stmt = select(SearchEntry).order_by(desc(SearchEntry.created_at), desc(SearchEntry.id))
        if user_id is not None:
            stmt = stmt.where(SearchEntry.user_id == user_id)
        result = await session.execute(stmt.limit(limit))
        return list(result.scalars().all())


async def get_search_entry(entry_id: int, user_id: int | None = None) -> SearchEntry | None:
    async with SessionLocal() as session:
        entry = await session.get(SearchEntry, entry_id)
        if entry is None:
            return None
        if user_id is not None and entry.user_id != user_id:
            return None
        return entry


async def save_usage_events(
    events: list[dict],
    user_id: int | None = None,
    search_entry_id: int | None = None,
) -> int:
    if not events:
        return 0
    async with SessionLocal() as session:
        session.add_all(
            [
                LlmUsageEvent(
                    user_id=user_id,
                    search_entry_id=search_entry_id,
                    query=str(e.get("query", ""))[:2000],
                    stage=str(e.get("stage", ""))[:100],
                    model=str(e.get("model", ""))[:100],
                    prompt_tokens=int(e.get("prompt_tokens", 0) or 0),
                    completion_tokens=int(e.get("completion_tokens", 0) or 0),
                    total_tokens=int(e.get("total_tokens", 0) or 0),
                    latency_ms=int(e.get("latency_ms", 0) or 0),
                )
                for e in events
            ]
        )
        await session.commit()
        return len(events)


def _scoped(stmt, model_field, user_id):
    if user_id is not None:
        stmt = stmt.where(model_field == user_id)
    return stmt


async def usage_totals(user_id: int | None = None) -> dict:
    async with SessionLocal() as session:
        totals_stmt = _scoped(
            select(
                func.coalesce(func.sum(LlmUsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(LlmUsageEvent.completion_tokens), 0),
                func.coalesce(func.sum(LlmUsageEvent.total_tokens), 0),
                func.count(LlmUsageEvent.id),
                func.count(func.distinct(LlmUsageEvent.search_entry_id)),
            ),
            LlmUsageEvent.user_id,
            user_id,
        )
        by_stage_stmt = _scoped(
            select(
                LlmUsageEvent.stage,
                func.count(LlmUsageEvent.id),
                func.coalesce(func.sum(LlmUsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(LlmUsageEvent.completion_tokens), 0),
                func.coalesce(func.sum(LlmUsageEvent.total_tokens), 0),
                func.coalesce(func.avg(LlmUsageEvent.latency_ms), 0),
            )
            .group_by(LlmUsageEvent.stage)
            .order_by(func.sum(LlmUsageEvent.total_tokens).desc()),
            LlmUsageEvent.user_id,
            user_id,
        )
        by_day_stmt = _scoped(
            select(
                func.date(LlmUsageEvent.created_at),
                func.count(LlmUsageEvent.id),
                func.coalesce(func.sum(LlmUsageEvent.total_tokens), 0),
                func.count(func.distinct(LlmUsageEvent.search_entry_id)),
            )
            .group_by(func.date(LlmUsageEvent.created_at))
            .order_by(func.date(LlmUsageEvent.created_at).desc())
            .limit(14),
            LlmUsageEvent.user_id,
            user_id,
        )
        totals = (await session.execute(totals_stmt)).one()
        by_stage = (await session.execute(by_stage_stmt)).all()
        by_day = (await session.execute(by_day_stmt)).all()
    prompt, completion, total, calls, queries = (int(v) for v in totals)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "llm_calls": calls,
        "queries_tracked": queries,
        "by_stage": [
            {
                "stage": r[0] or "unknown",
                "calls": int(r[1]),
                "prompt_tokens": int(r[2]),
                "completion_tokens": int(r[3]),
                "total_tokens": int(r[4]),
                "avg_latency_ms": int(r[5]),
            }
            for r in by_stage
        ],
        "by_day": [
            {
                "day": str(r[0]),
                "calls": int(r[1]),
                "total_tokens": int(r[2]),
                "queries": int(r[3]),
            }
            for r in by_day
        ],
    }


async def usage_per_query(user_id: int | None = None, limit: int = 50) -> list[dict]:
    async with SessionLocal() as session:
        stmt = _scoped(
            select(
                SearchEntry.id,
                SearchEntry.query,
                SearchEntry.created_at,
                func.count(LlmUsageEvent.id),
                func.coalesce(func.sum(LlmUsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(LlmUsageEvent.completion_tokens), 0),
                func.coalesce(func.sum(LlmUsageEvent.total_tokens), 0),
                func.coalesce(User.email, ""),
            )
            .outerjoin(LlmUsageEvent, LlmUsageEvent.search_entry_id == SearchEntry.id)
            .outerjoin(User, User.id == SearchEntry.user_id)
            .group_by(SearchEntry.id, User.email)
            .order_by(desc(SearchEntry.created_at), desc(SearchEntry.id))
            .limit(limit),
            SearchEntry.user_id,
            user_id,
        )
        rows = (await session.execute(stmt)).all()
    return [
        {
            "id": r[0],
            "query": r[1],
            "created_at": r[2].isoformat() if r[2] else "",
            "calls": int(r[3]),
            "prompt_tokens": int(r[4]),
            "completion_tokens": int(r[5]),
            "total_tokens": int(r[6]),
            "user_email": r[7] or "",
        }
        for r in rows
    ]


async def usage_for_entry(entry_id: int, user_id: int) -> list[LlmUsageEvent]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(LlmUsageEvent)
            .where(
                LlmUsageEvent.search_entry_id == entry_id,
                LlmUsageEvent.user_id == user_id,
            )
            .order_by(LlmUsageEvent.id)
        )
        return list(result.scalars().all())


async def usage_for_entry_any(entry_id: int) -> list[LlmUsageEvent]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(LlmUsageEvent)
            .where(LlmUsageEvent.search_entry_id == entry_id)
            .order_by(LlmUsageEvent.id)
        )
        return list(result.scalars().all())
