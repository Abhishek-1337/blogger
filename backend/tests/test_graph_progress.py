import asyncio
import unittest
from unittest.mock import patch

import src.graph as graph


class _FakeApp:
    def __init__(self, chunks):
        self._chunks = chunks

    async def astream(self, initial, stream_mode=None):
        assert stream_mode == "updates"
        for chunk in self._chunks:
            yield chunk


def _run(chunks):
    stages = []
    with patch.object(graph, "build_graph", lambda: _FakeApp(chunks)):
        final, _events = asyncio.run(
            graph.arun_blog_with_usage("topic", on_progress=stages.append)
        )
    return stages, final


class GraphProgressTest(unittest.TestCase):
    def test_reports_each_stage_in_order(self):
        stages, final = _run(
            [
                {"research": {"search_results": [{"title": "t"}]}},
                {"summarize": {"research_brief": "brief"}},
                {"outline": {"outline": ["a"], "outline_revisions": 1}},
                {
                    "verify_outline": {
                        "outline_approved": True,
                        "outline_feedback": "",
                    }
                },
            ]
        )
        self.assertEqual(
            stages, ["research", "summarize", "outline", "verify_outline"]
        )
        self.assertEqual(final["research_brief"], "brief")
        self.assertTrue(final["outline_approved"])

    def test_rejected_outline_loops_back_to_outline(self):
        stages, _final = _run(
            [
                {"research": {}},
                {"summarize": {}},
                {"outline": {"outline_revisions": 1}},
                {"verify_outline": {"outline_approved": False}},
                {"outline": {"outline_revisions": 2}},
                {"verify_outline": {"outline_approved": True}},
            ]
        )
        self.assertEqual(
            stages,
            [
                "research",
                "summarize",
                "outline",
                "verify_outline",
                "outline",
                "verify_outline",
            ],
        )

    def test_no_callback_still_returns_final(self):
        with patch.object(
            graph, "build_graph", lambda: _FakeApp([{"research": {"x": 1}}])
        ):
            final, _events = asyncio.run(graph.arun_blog_with_usage("topic"))
        self.assertEqual(final["query"], "topic")


if __name__ == "__main__":
    unittest.main()
