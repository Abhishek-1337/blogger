import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from main import app
from src import db as db_module
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
        async def _no_duplicate(*a, **k):
            return None

        with (
            patch.object(blog_router, "find_entry_id_by_query", _no_duplicate),
            patch.object(
                blog_router.generate_blog_task,
                "delay",
                lambda *a: SimpleNamespace(id="task-123"),
            ),
        ):
            r = self.client.post("/blog/enqueue", json={"query": "hello"})
        self.assertEqual(r.status_code, 202)
        self.assertEqual(
            r.json(), {"task_id": "task-123", "status": "queued", "entry_id": None}
        )

    def test_enqueue_duplicate_query_returns_saved_entry(self):
        async def _duplicate(*a, **k):
            return 7

        delay = Mock(return_value=SimpleNamespace(id="task-123"))
        with (
            patch.object(blog_router, "find_entry_id_by_query", _duplicate),
            patch.object(blog_router.generate_blog_task, "delay", delay),
        ):
            r = self.client.post("/blog/enqueue", json={"query": "hello"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(), {"task_id": "", "status": "duplicate", "entry_id": 7}
        )
        delay.assert_not_called()

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

    def test_task_status_progress_returns_stage(self):
        with patch.object(
            blog_router,
            "AsyncResult",
            lambda task_id, app=None: SimpleNamespace(
                state="PROGRESS",
                info={"stage": "outline", "message": "Drafting outline"},
                result=None,
            ),
        ):
            r = self.client.get("/blog/tasks/task-123")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "PROGRESS")
        self.assertEqual(body["stage"], "outline")
        self.assertEqual(body["message"], "Drafting outline")

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


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeSession:
    captured = []
    row = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, stmt):
        _FakeSession.captured.append(stmt)
        return _FakeResult(_FakeSession.row)


def _run_has_query(query, user_id):
    with patch.object(db_module, "SessionLocal", lambda: _FakeSession()):
        return asyncio.run(db_module.has_query(query, user_id))


class HasQueryTest(unittest.TestCase):
    def setUp(self):
        _FakeSession.captured = []
        _FakeSession.row = None

    def test_existing_query_returns_true(self):
        _FakeSession.row = (1,)
        self.assertTrue(_run_has_query("hello", 1))

    def test_missing_query_returns_false(self):
        _FakeSession.row = None
        self.assertFalse(_run_has_query("hello", 1))

    def test_match_is_case_and_whitespace_insensitive(self):
        _FakeSession.row = (1,)
        self.assertTrue(_run_has_query("  HELLO World ", 1))
        params = _FakeSession.captured[-1].compile().params
        self.assertIn("hello world", params.values())

    def test_match_is_scoped_to_user(self):
        _FakeSession.row = (1,)
        _run_has_query("hello", 7)
        stmt = _FakeSession.captured[-1]
        self.assertIn("user_id", str(stmt).lower())
        self.assertIn(7, stmt.compile().params.values())

    def test_no_user_scope_when_user_id_none(self):
        _FakeSession.row = None
        self.assertFalse(_run_has_query("hello", None))
        self.assertNotIn("user_id", str(_FakeSession.captured[-1]).lower())


def _run_find_entry_id(query, user_id):
    with patch.object(db_module, "SessionLocal", lambda: _FakeSession()):
        return asyncio.run(db_module.find_entry_id_by_query(query, user_id))


class FindEntryIdTest(unittest.TestCase):
    def setUp(self):
        _FakeSession.captured = []
        _FakeSession.row = None

    def test_returns_most_recent_entry_id(self):
        _FakeSession.row = (42,)
        self.assertEqual(_run_find_entry_id("hello", 1), 42)

    def test_returns_none_when_no_match(self):
        _FakeSession.row = None
        self.assertIsNone(_run_find_entry_id("hello", 1))


if __name__ == "__main__":
    unittest.main()
