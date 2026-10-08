import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.models import SearchEntry

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
