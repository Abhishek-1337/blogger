import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from src.auth import get_current_user
import src.routers.blog as blog_router


class BlogQueueTest(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=1, email="admin@test.com", name="t", picture=None
        )
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(app.dependency_overrides.clear)

    def test_sync_blog_route_removed(self):
        r = self.client.post("/blog", json={"query": "hello"})
        self.assertIn(r.status_code, (404, 405))

    def test_enqueue_returns_task_id(self):
        with patch.object(
            blog_router.generate_blog_task,
            "delay",
            lambda *a: SimpleNamespace(id="task-123"),
        ):
            r = self.client.post("/blog/enqueue", json={"query": "hello"})
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.json(), {"task_id": "task-123", "status": "queued"})

    def test_task_status_success(self):
        with patch.object(
            blog_router,
            "AsyncResult",
            lambda task_id, app=None: SimpleNamespace(
                state="SUCCESS",
                info=None,
                result={
                    "entry_id": 42,
                    "outline_approved": True,
                    "total_tokens": 15,
                    "est_cost_usd": 5e-06,
                },
            ),
        ):
            r = self.client.get("/blog/tasks/task-123")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["entry_id"], 42)

    def test_task_status_failure(self):
        with patch.object(
            blog_router,
            "AsyncResult",
            lambda task_id, app=None: SimpleNamespace(
                state="FAILURE", info=None, result=ValueError("boom")
            ),
        ):
            r = self.client.get("/blog/tasks/task-123")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "FAILURE")
        self.assertIn("boom", body["error"])


if __name__ == "__main__":
    unittest.main()
