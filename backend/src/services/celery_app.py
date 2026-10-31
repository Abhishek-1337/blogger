import os

from celery import Celery
from celery.signals import worker_process_init

celery_app = Celery(
    "my_backend",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    include=["src.worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    result_expires=86400,
    timezone="UTC",
    enable_utc=True,
)


@worker_process_init.connect
def _setup_child_optimizations(**_kwargs) -> None:
    # macOS pool children are spawned, not forked, so they never inherit
    # the main process's fast-trace state and fail every task with
    # "not enough values to unpack (expected 3, got 0)".
    # Celery also builds the child's tracers on an unpickled copy of the
    # app, not on this module's instance, so its tasks need their own or
    # they fail with "'NoneType' object is not callable".
    from celery.app.trace import build_tracer, setup_worker_optimizations

    setup_worker_optimizations(celery_app)
    for name, task in celery_app.tasks.items():
        if task.__trace__ is None:
            task.__trace__ = build_tracer(
                name, task, celery_app.loader, app=celery_app
            )