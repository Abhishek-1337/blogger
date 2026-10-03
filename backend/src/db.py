import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models import SearchEntry

load_dotenv()


def normalize_database_url(url: str) -> str:
    """Adapt a generic Postgres URL for SQLAlchemy + asyncpg.

    Drops the ``channel_binding`` query param: cloud providers (e.g. Neon)
    add it, but asyncpg's ``connect()`` takes no such keyword and SQLAlchemy
    forwards URL params as keywords, which raises TypeError. Encryption and
    SCRAM auth via ``sslmode`` are unaffected.
    """
    url = url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "channel_binding"]
    return urlunsplit(parts._replace(query=urlencode(query)))


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url.strip():
        raise ValueError("DATABASE_URL not set.")
    return normalize_database_url(url)


_engine = None
_session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_async_engine(get_database_url(), pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


async def save_search_entry(data: dict) -> int:
    """Persist one search result. Returns the new row id."""
    factory = get_session_factory()
    async with factory() as session:
        entry = SearchEntry(
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


async def list_search_entries(limit: int = 50) -> list[SearchEntry]:
    """Newest-first search summaries (full rows; callers pick fields)."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(SearchEntry)
            .order_by(desc(SearchEntry.created_at), desc(SearchEntry.id))
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_search_entry(entry_id: int) -> SearchEntry | None:
    """One stored search result by id, or None."""
    factory = get_session_factory()
    async with factory() as session:
        return await session.get(SearchEntry, entry_id)
