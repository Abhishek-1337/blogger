import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from main import app
from src import db as db_module
from src.auth import get_current_user
from src.models import BlogContent, SearchEntry
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
            patch.object(blog_router, "find_or_link_entry_by_query", _no_duplicate),
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
            patch.object(blog_router, "find_or_link_entry_by_query", _duplicate),
            patch.object(blog_router.generate_blog_task, "delay", delay),
        ):
            r = self.client.post("/blog/enqueue", json={"query": "hello"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(), {"task_id": "", "status": "duplicate", "entry_id": 7}
        )
        delay.assert_not_called()

    def test_get_searches_and_detail_read_from_linked_content(self):
        from datetime import datetime, timezone

        content = BlogContent(
            id=10,
            hashed_key=db_module.query_key_hash("hello"),
            query="hello",
            research_brief="brief",
            outline=["Intro"],
            sections=[{"title": "Intro", "bullets": ["Point 1"]}],
            outline_approved=True,
            outline_revisions=1,
            outline_feedback="Approved",
        )
        entry = SearchEntry(
            id=7,
            user_id=1,
            content_id=10,
            query="HELLO",
            created_at=datetime(2026, 11, 26, tzinfo=timezone.utc),
            content=content,
        )

        async def _list(limit, user_id):
            return [entry]

        async def _get(entry_id, user_id):
            return entry if (entry_id == 7 and user_id == 1) else None

        with (
            patch.object(blog_router, "list_search_entries", _list),
            patch.object(blog_router, "get_search_entry", _get),
        ):
            listed = self.client.get("/searches")
            detail = self.client.get("/searches/7")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["id"], 7)
        self.assertEqual(listed.json()[0]["query"], "HELLO")
        self.assertTrue(listed.json()[0]["outline_approved"])

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["id"], 7)
        self.assertEqual(detail.json()["query"], "HELLO")
        self.assertEqual(detail.json()["research_brief"], "brief")
        self.assertEqual(detail.json()["outline"], ["Intro"])
        self.assertTrue(detail.json()["outline_approved"])

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


class _FakeNestedTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeResult:
    def __init__(self, row, scalar=None):
        self._row = row
        self._scalar = scalar

    def first(self):
        return self._row

    def scalar_one_or_none(self):
        return self._scalar


class _FakeSession:
    captured = []
    row = None
    execute_results = []
    added = []
    committed = False
    next_id = 100

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def begin_nested(self):
        return _FakeNestedTx()

    def add(self, obj):
        _FakeSession.added.append(obj)

    async def flush(self):
        for obj in _FakeSession.added:
            if getattr(obj, "id", None) is None:
                _FakeSession.next_id += 1
                obj.id = _FakeSession.next_id

    async def commit(self):
        _FakeSession.committed = True

    async def execute(self, stmt):
        _FakeSession.captured.append(stmt)
        if _FakeSession.execute_results:
            return _FakeSession.execute_results.pop(0)
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
        self.assertIn(db_module.query_key_hash("hello world"), params.values())

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
        _FakeSession.execute_results = []
        _FakeSession.added = []
        _FakeSession.committed = False

    def test_returns_most_recent_entry_id(self):
        _FakeSession.row = (42,)
        self.assertEqual(_run_find_entry_id("hello", 1), 42)

    def test_returns_none_when_no_match(self):
        _FakeSession.row = None
        self.assertIsNone(_run_find_entry_id("hello", 1))


class FindOrLinkEntryTest(unittest.TestCase):
    def setUp(self):
        _FakeSession.captured = []
        _FakeSession.row = None
        _FakeSession.execute_results = []
        _FakeSession.added = []
        _FakeSession.committed = False
        _FakeSession.next_id = 100

    def _run(self, query, user_id):
        with patch.object(db_module, "SessionLocal", lambda: _FakeSession()):
            return asyncio.run(db_module.find_or_link_entry_by_query(query, user_id))

    def test_cache_miss_returns_none(self):
        _FakeSession.execute_results = [_FakeResult(None)]
        self.assertIsNone(self._run("brand new query", 2))
        self.assertEqual(_FakeSession.added, [])
        self.assertFalse(_FakeSession.committed)

    def test_same_user_returns_existing_entry_without_insert(self):
        _FakeSession.execute_results = [_FakeResult((10,)), _FakeResult((55,))]
        self.assertEqual(self._run("hello", 1), 55)
        self.assertEqual(_FakeSession.added, [])
        self.assertTrue(_FakeSession.committed)

    def test_cross_user_hit_creates_user_search_entry_for_existing_content(self):
        _FakeSession.execute_results = [_FakeResult((10,)), _FakeResult(None)]
        new_id = self._run("  Hello  ", 2)
        self.assertEqual(new_id, 101)
        self.assertEqual(len(_FakeSession.added), 1)
        created = _FakeSession.added[0]
        self.assertIsInstance(created, SearchEntry)
        self.assertEqual(created.user_id, 2)
        self.assertEqual(created.content_id, 10)
        self.assertEqual(created.query, "  Hello  ")
        self.assertTrue(_FakeSession.committed)


class SaveSearchEntryTest(unittest.TestCase):
    def setUp(self):
        _FakeSession.captured = []
        _FakeSession.row = None
        _FakeSession.execute_results = []
        _FakeSession.added = []
        _FakeSession.committed = False
        _FakeSession.next_id = 200

    def test_creates_blog_content_and_search_entry_when_uncached(self):
        _FakeSession.execute_results = [
            _FakeResult(None, scalar=None),
            _FakeResult(None),
        ]
        with patch.object(db_module, "SessionLocal", lambda: _FakeSession()):
            entry_id = asyncio.run(
                db_module.save_search_entry(
                    {
                        "query": "Rust async",
                        "research_brief": "brief",
                        "outline": ["A"],
                        "sections": [{"title": "A", "bullets": ["b"]}],
                        "outline_approved": True,
                        "outline_revisions": 1,
                        "outline_feedback": "Good",
                    },
                    user_id=3,
                )
            )
        self.assertEqual(entry_id, 202)
        self.assertEqual(len(_FakeSession.added), 2)
        content, entry = _FakeSession.added
        self.assertIsInstance(content, BlogContent)
        self.assertEqual(content.hashed_key, db_module.query_key_hash("Rust async"))
        self.assertEqual(content.research_brief, "brief")
        self.assertIsInstance(entry, SearchEntry)
        self.assertEqual(entry.user_id, 3)
        self.assertEqual(entry.content_id, content.id)
        self.assertEqual(entry.query, "Rust async")
        self.assertTrue(_FakeSession.committed)

    def test_reuses_existing_blog_content_if_already_saved(self):
        existing_content = BlogContent(
            id=88,
            hashed_key=db_module.query_key_hash("Rust async"),
            query="rust async",
        )
        _FakeSession.execute_results = [
            _FakeResult(None, scalar=existing_content),
            _FakeResult(None),
        ]
        with patch.object(db_module, "SessionLocal", lambda: _FakeSession()):
            entry_id = asyncio.run(
                db_module.save_search_entry({"query": "Rust async"}, user_id=4)
            )
        self.assertEqual(entry_id, 201)
        self.assertEqual(len(_FakeSession.added), 1)
        entry = _FakeSession.added[0]
        self.assertIsInstance(entry, SearchEntry)
        self.assertEqual(entry.user_id, 4)
        self.assertEqual(entry.content_id, 88)


if __name__ == "__main__":
    unittest.main()
