import asyncio
from collections.abc import Callable

from src.db import save_search_entry, save_usage_events
from src.graph import arun_blog_with_usage
from src.services.celery_app import celery_app
from src.usage import UsageCollector


async def _run_and_persist(
    query: str,
    user_id: int | None,
    on_progress: Callable[[str], None] | None = None,
) -> dict:
    def progress(message: str) -> None:
        if on_progress is not None:
            on_progress(message)

    progress("Running research workflow...")
    final, usage_events = await arun_blog_with_usage(query)

    if final.get("outline_feedback"):
        feedback = final["outline_feedback"]
    elif final.get("outline_approved"):
        feedback = "Outline approved."
    else:
        feedback = ""

    progress("Saving results...")
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
        user_id,
    )
    await save_usage_events(usage_events, user_id, entry_id)

    collector = UsageCollector(query=query)
    collector.events = usage_events
    summary = collector.summary()
    return {
        "entry_id": entry_id,
        "query": query,
        "outline_approved": bool(final.get("outline_approved", False)),
        "outline_revisions": int(final.get("outline_revisions", 0) or 0),
        "outline_feedback": feedback,
        "llm_calls": summary["calls"],
        "total_tokens": summary["total_tokens"],
        "est_cost_usd": summary["est_cost_usd"],
    }


@celery_app.task(
    bind=True,
    name="tasks.generate_blog",
    max_retries=2,
    time_limit=900,
    soft_time_limit=600,
)
def generate_blog(self, query: str, user_id: int | None = None) -> dict:
    def on_progress(message: str) -> None:
        self.update_state(state="PROGRESS", meta={"message": message})

    try:
        return asyncio.run(_run_and_persist(query.strip(), user_id, on_progress))
    except ValueError:
        raise
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
