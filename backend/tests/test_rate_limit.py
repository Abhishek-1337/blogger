import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from src import rate_limit
from src.auth import get_current_user
import src.routers.auth as auth_router
import src.routers.blog as blog_router
import src.routers.usage as usage_router


def _user(user_id):
    return SimpleNamespace(id=user_id, email=f"u{user_id}@test.com", name="t", picture=None)


class InMemoryStoreTest(unittest.TestCase):
    def test_allows_up_to_limit_then_rejects_per_key(self):
        import asyncio

        async def run():
            store = rate_limit.InMemoryStore()
            check = lambda key: rate_limit.Check(key=key, limit=2, window_seconds=60)
            self.assertTrue((await store.check_and_hit([check("a")])).allowed)
            self.assertTrue((await store.check_and_hit([check("a")])).allowed)
            denied = await store.check_and_hit([check("a")])
            self.assertFalse(denied.allowed)
            self.assertGreaterEqual(denied.retry_after_seconds, 1)
            # A different key has its own budget.
            self.assertTrue((await store.check_and_hit([check("b")])).allowed)

        asyncio.run(run())

    def test_rejected_hit_does_not_consume_other_windows(self):
        import asyncio

        async def run():
            store = rate_limit.InMemoryStore()
            minute = rate_limit.Check(key="m", limit=1, window_seconds=60)
            day = rate_limit.Check(key="d", limit=10, window_seconds=86400)
            self.assertTrue((await store.check_and_hit([minute, day])).allowed)
            self.assertFalse((await store.check_and_hit([minute, day])).allowed)
            # Day counter must not have been incremented by the rejected hit.
            decision = await store.check_and_hit(
                [rate_limit.Check(key="d", limit=10, window_seconds=86400)]
            )
            self.assertTrue(decision.allowed)
            self.assertEqual(decision.remaining, 8)

        asyncio.run(run())


class RateLimitRoutesTest(unittest.TestCase):
    def setUp(self):
        self.store = rate_limit.InMemoryStore()
        rate_limit.set_store_override(self.store)
        self.addCleanup(rate_limit.set_store_override, None)
        self.env = patch.dict(
            os.environ,
            {
                "RATE_LIMIT_ENABLED": "true",
                "RATE_LIMIT_GEN_PER_USER_PER_MINUTE": "3",
                "RATE_LIMIT_GEN_PER_USER_PER_DAY": "100",
                "RATE_LIMIT_GEN_GLOBAL_PER_MINUTE": "100",
                "RATE_LIMIT_POLL_PER_USER_PER_MINUTE": "2",
                "RATE_LIMIT_POLL_GLOBAL_PER_MINUTE": "100",
                "RATE_LIMIT_READ_PER_USER_PER_MINUTE": "2",
                "RATE_LIMIT_READ_GLOBAL_PER_MINUTE": "100",
                "RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE": "2",
                "RATE_LIMIT_LOGIN_GLOBAL_PER_MINUTE": "100",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        app.dependency_overrides[get_current_user] = lambda: _user(1)
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app, raise_server_exceptions=False)

    def _enqueue(self):
        with patch.object(
            blog_router.generate_blog_task,
            "delay",
            lambda *a: SimpleNamespace(id="task-123"),
        ):
            return self.client.post("/blog/enqueue", json={"query": "hello"})

    def test_generation_per_user_limit_returns_429_with_retry_after(self):
        first = self._enqueue()
        self.assertEqual(first.status_code, 202)
        self.assertIn("X-RateLimit-Limit", first.headers)
        for _ in range(2):
            self.assertEqual(self._enqueue().status_code, 202)
        r = self._enqueue()
        self.assertEqual(r.status_code, 429)
        self.assertIn("Rate limit", r.json()["detail"])
        self.assertGreaterEqual(int(r.headers["Retry-After"]), 1)

    def test_generation_limit_is_per_user_not_shared(self):
        for _ in range(3):
            self.assertEqual(self._enqueue().status_code, 202)
        self.assertEqual(self._enqueue().status_code, 429)
        app.dependency_overrides[get_current_user] = lambda: _user(2)
        self.assertEqual(self._enqueue().status_code, 202)

    def test_generation_global_limit_applies_across_users(self):
        with patch.dict(os.environ, {"RATE_LIMIT_GEN_GLOBAL_PER_MINUTE": "2"}):
            self.assertEqual(self._enqueue().status_code, 202)
            app.dependency_overrides[get_current_user] = lambda: _user(2)
            self.assertEqual(self._enqueue().status_code, 202)
            app.dependency_overrides[get_current_user] = lambda: _user(3)
            self.assertEqual(self._enqueue().status_code, 429)

    def test_generation_daily_cap_applies(self):
        with patch.dict(
            os.environ,
            {
                "RATE_LIMIT_GEN_PER_USER_PER_MINUTE": "100",
                "RATE_LIMIT_GEN_PER_USER_PER_DAY": "2",
            },
        ):
            self.assertEqual(self._enqueue().status_code, 202)
            self.assertEqual(self._enqueue().status_code, 202)
            self.assertEqual(self._enqueue().status_code, 429)

    def test_polling_has_its_own_tier(self):
        fake = lambda task_id, app=None: SimpleNamespace(  # noqa: E731
            state="PENDING", info=None, result=None
        )
        with patch.object(blog_router, "AsyncResult", fake):
            self.assertEqual(self.client.get("/blog/tasks/t1").status_code, 200)
            self.assertEqual(self.client.get("/blog/tasks/t1").status_code, 200)
            self.assertEqual(self.client.get("/blog/tasks/t1").status_code, 429)

    def test_reads_have_own_tier_and_do_not_block_generation(self):
        async def fake_list(limit, user_id):
            return []

        with patch.object(blog_router, "list_search_entries", fake_list):
            self.assertEqual(self.client.get("/searches").status_code, 200)
            self.assertEqual(self.client.get("/searches").status_code, 200)
            self.assertEqual(self.client.get("/searches").status_code, 429)
        # Read budget exhausted, generation budget untouched.
        self.assertEqual(self._enqueue().status_code, 202)

    def test_login_limited_per_ip_before_google_verify(self):
        calls = []

        def fake_verify(token):
            calls.append(token)
            raise ValueError("bad token")

        with patch.object(auth_router, "verify_google_token", fake_verify):
            self.assertEqual(
                self.client.post("/auth/google", json={"id_token": "x"}).status_code, 401
            )
            self.assertEqual(
                self.client.post("/auth/google", json={"id_token": "x"}).status_code, 401
            )
            r = self.client.post("/auth/google", json={"id_token": "x"})
            self.assertEqual(r.status_code, 429)
        self.assertEqual(len(calls), 2)

    def test_admin_reads_have_stricter_tier(self):
        async def fake_recent(user_id, limit):
            return []

        with patch.dict(os.environ, {"RATE_LIMIT_ADMIN_PER_USER_PER_MINUTE": "2"}):
            with patch.object(usage_router, "recent_usage_rows", fake_recent):
                self.assertEqual(self.client.get("/usage/recent").status_code, 200)
                self.assertEqual(self.client.get("/usage/recent").status_code, 200)
                self.assertEqual(self.client.get("/usage/recent").status_code, 429)

    def test_limiter_backend_failure_fails_open_by_default(self):
        class BrokenStore:
            async def check_and_hit(self, checks):
                raise ConnectionError("redis down")

        rate_limit.set_store_override(BrokenStore())
        self.assertEqual(self._enqueue().status_code, 202)

    def test_limiter_backend_failure_fails_closed_when_configured(self):
        class BrokenStore:
            async def check_and_hit(self, checks):
                raise ConnectionError("redis down")

        rate_limit.set_store_override(BrokenStore())
        with patch.dict(os.environ, {"RATE_LIMIT_FAIL_CLOSED": "true"}):
            self.assertEqual(self._enqueue().status_code, 503)

    def test_disabled_limiter_allows_requests(self):
        with patch.dict(os.environ, {"RATE_LIMIT_ENABLED": "false"}):
            for _ in range(5):
                self.assertEqual(self._enqueue().status_code, 202)


if __name__ == "__main__":
    unittest.main()
