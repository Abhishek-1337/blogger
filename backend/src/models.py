from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SearchEntry(Base):
    """One stored blog search and its generated result."""

    __tablename__ = "search_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    research_brief: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outline: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    outline_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outline_revisions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outline_feedback: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
