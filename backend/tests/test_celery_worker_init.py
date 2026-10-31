import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Emulates a spawned (non-forked) prefork child: the pool hands the child an
# unpickled copy of the app, and celery's own process_initializer builds the
# tracers on that copy before sending worker_process_init.
CHILD_SCRIPT = textwrap.dedent(
    """
    import json
    import os
    import pickle

    from celery.app.trace import _localized, fast_trace_task
    from celery.concurrency.prefork import process_initializer

    from src.services.celery_app import celery_app

    os.environ.pop("FORKED_BY_MULTIPROCESSING", None)
    celery_app.conf.task_ignore_result = True

    @celery_app.task(name="tasks.ping_child", ignore_result=True)
    def ping(x):
        return x + 1

    assert _localized == [], f"expected fresh child state, got {_localized}"
    process_initializer(pickle.loads(pickle.dumps(celery_app)), "testhost")
    assert len(_localized) == 3, f"worker_process_init did not populate _localized: {_localized}"

    body = json.dumps([[41], {}, {}]).encode()
    out = fast_trace_task(
        "tasks.ping_child", "probe-1", {"id": "probe-1"},
        body, "application/json", "utf-8",
    )
    assert out[1] == "42", f"task did not run: {out}"
    print("CHILD OK", out)
    """
)


class CeleryWorkerInitTest(unittest.TestCase):
    def test_spawned_child_can_trace_task(self):
        result = subprocess.run(
            [sys.executable, "-c", CHILD_SCRIPT],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CHILD OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
