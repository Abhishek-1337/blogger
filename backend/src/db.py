import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.models import LlmUsageEvent, SearchEntry, User

load_dotenv()


def _normalize_db_url(url: str) -> str:
    """Ensure URL uses the asyncpg driver for the app runtime.

    Also drops the ``channel_binding`` query param: cloud providers
    (e.g. Neon) add it, but asyncpg's ``connect()`` takes no such keyword
    and SQLAlchemy forwards URL params as keywords, which raises TypeError.
    ``sslmode`` is left in place — the asyncpg dialect translates it.
    """
    if not url:
        return url
    url = url.strip()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "channel_binding"]
    return urlunsplit(parts._replace(query=urlencode(query)))


_raw_url = os.getenv("DATABASE_URL")
if not _raw_url:
    raise RuntimeError(
        "DATABASE_URL is not set — check backend/.env or docker-compose environment"
    )
_DATABASE_URL = _normalize_db_url(_raw_url)

_ssl_mode = os.getenv("DATABASE_SSL", "").lower().strip()
if _ssl_mode in ("require", "true", "1"):
    _connect_args = {"ssl": "require"}
elif _ssl_mode in ("disable", "false", "0"):
    _connect_args = {}
else:
    _is_local = any(
        h in _DATABASE_URL
        for h in [
            "@db:",
            "@db/",
            "@localhost",
            "@127.0.0.1",
            "localhost:",
            "127.0.0.1:",
        ]
    )
    _needs_ssl = any(
        h in _DATABASE_URL
        for h in ["neon.tech", "supabase.co", "rds.amazonaws.com", "sslmode=require"]
    )
    if _needs_ssl or not _is_local:
        _connect_args = {} if _is_local else {"ssl": "require"}
    else:
        _connect_args = {}

engine = create_async_engine(
    _DATABASE_URL,
    connect_args=_connect_args,
    echo=False,
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def save_search_entry(data: dict, user_id: int | None = None) -> int:
    """Persist one search result. Returns the new row id."""
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


async def list_search_entries(
    limit: int = 50, user_id: int | None = None
) -> list[SearchEntry]:
    """Newest-first search entries, optionally scoped to one user."""
    async with SessionLocal() as session:
        stmt = select(SearchEntry).order_by(
            desc(SearchEntry.created_at), desc(SearchEntry.id)
        )
        if user_id is not None:
            stmt = stmt.where(SearchEntry.user_id == user_id)
        result = await session.execute(stmt.limit(limit))
        return list(result.scalars().all())


async def save_usage_events(
    events: list[dict],
    user_id: int | None = None,
    search_entry_id: int | None = None,
) -> int:
    """Persist one run's collected LLM usage events. Returns rows written."""
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


async def usage_totals(user_id: int | None = None) -> dict:
    """Aggregate token totals, call counts, and per-stage / per-day splits.

    ``user_id=None`` aggregates across all users (global dashboard).
    """
    async with SessionLocal() as session:
        totals_stmt = select(
            func.coalesce(func.sum(LlmUsageEvent.prompt_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.completion_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.total_tokens), 0),
            func.count(LlmUsageEvent.id),
            func.count(func.distinct(LlmUsageEvent.search_entry_id)),
        )
        by_stage_stmt = (
            select(
                LlmUsageEvent.stage,
                func.count(LlmUsageEvent.id),
                func.coalesce(func.sum(LlmUsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(LlmUsageEvent.completion_tokens), 0),
                func.coalesce(func.sum(LlmUsageEvent.total_tokens), 0),
                func.coalesce(func.avg(LlmUsageEvent.latency_ms), 0),
            )
            .group_by(LlmUsageEvent.stage)
            .order_by(func.sum(LlmUsageEvent.total_tokens).desc())
        )
        by_day_stmt = (
            select(
                func.date(LlmUsageEvent.created_at),
                func.count(LlmUsageEvent.id),
                func.coalesce(func.sum(LlmUsageEvent.total_tokens), 0),
                func.count(func.distinct(LlmUsageEvent.search_entry_id)),
            )
            .group_by(func.date(LlmUsageEvent.created_at))
            .order_by(func.date(LlmUsageEvent.created_at).desc())
            .limit(14)
        )
        if user_id is not None:
            scope = LlmUsageEvent.user_id == user_id
            totals_stmt = totals_stmt.where(scope)
            by_stage_stmt = by_stage_stmt.where(scope)
            by_day_stmt = by_day_stmt.where(scope)
        totals = (await session.execute(totals_stmt)).one()
        by_stage = (await session.execute(by_stage_stmt)).all()
        by_day = (await session.execute(by_day_stmt)).all()
    return {
        "prompt_tokens": int(totals[0]),
        "completion_tokens": int(totals[1]),
        "total_tokens": int(totals[2]),
        "llm_calls": int(totals[3]),
        "queries_tracked": int(totals[4]),
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


async def usage_per_query(
    user_id: int | None = None, limit: int = 50
) -> list[dict]:
    """Newest-first per-query token rollups for the dashboard table.

    ``user_id=None`` returns every user's queries (global dashboard).
    """
    async with SessionLocal() as session:
        stmt = (
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
            .outerjoin(
                LlmUsageEvent,
                LlmUsageEvent.search_entry_id == SearchEntry.id,
            )
            .outerjoin(User, User.id == SearchEntry.user_id)
            .group_by(SearchEntry.id, User.email)
            .order_by(desc(SearchEntry.created_at), desc(SearchEntry.id))
            .limit(limit)
        )
        if user_id is not None:
            stmt = stmt.where(SearchEntry.user_id == user_id)
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
    """Per-LLM-call usage rows for one stored query (owner-scoped)."""
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


async def get_search_entry(
    entry_id: int, user_id: int | None = None
) -> SearchEntry | None:
    """One stored search result by id (and owner, when given), or None."""
    async with SessionLocal() as session:
        entry = await session.get(SearchEntry, entry_id)
        if entry is None:
            return None
        if user_id is not None and entry.user_id != user_id:
            return None
        return entry
