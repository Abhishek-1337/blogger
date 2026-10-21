import asyncio

from src.graph import arun_blog_with_usage
from src.services.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="tasks.generate_blog"
)
def generate_blog(self, query: str):
    return asyncio.run(arun_blog_with_usage(query))
