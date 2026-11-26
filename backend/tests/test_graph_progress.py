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


class _FakeStructuredLLM:
    def __init__(self, captured):
        self._captured = captured

    async def ainvoke(self, prompt, config=None):
        self._captured.append(prompt)
        return graph.BlogOutline(
            sections=[
                graph.OutlineSection(title=f"Section {i}", bullets=["a", "b", "c"])
                for i in range(1, 5)
            ]
        )


class _FakeLLM:
    def __init__(self, captured):
        self._captured = captured

    def with_structured_output(self, _model):
        return _FakeStructuredLLM(self._captured)


def _run_outline(state):
    captured = []
    with patch.object(graph, "_llm", lambda _temp=0.3: _FakeLLM(captured)):
        result = asyncio.run(graph.outline_node(state))
    return captured[0], result


def _base_state(**overrides):
    state = {
        "query": "topic",
        "research_brief": "brief",
        "sections": [],
        "outline": [],
        "outline_feedback": "",
        "outline_revisions": 0,
        "outline_approved": False,
    }
    state.update(overrides)
    return state


class OutlineRetryPromptTest(unittest.TestCase):
    def test_retry_prompt_mentions_failed_approval_and_feedback(self):
        prompt, _result = _run_outline(
            _base_state(
                sections=[{"title": "Old", "bullets": ["x", "y", "z"]}],
                outline_feedback="Add a section on costs; drop the generic intro.",
                outline_revisions=1,
                outline_approved=False,
            )
        )
        self.assertIn("last outline approval failed", prompt.lower())
        self.assertIn("Add a section on costs; drop the generic intro.", prompt)
        self.assertIn("Old", prompt)

    def test_retry_with_empty_feedback_still_mentions_failed_approval(self):
        prompt, _result = _run_outline(
            _base_state(
                sections=[{"title": "Old", "bullets": ["x", "y", "z"]}],
                outline_feedback="",
                outline_revisions=1,
                outline_approved=False,
            )
        )
        self.assertIn("last outline approval failed", prompt.lower())

    def test_first_run_prompt_has_no_failed_approval_mention(self):
        prompt, _result = _run_outline(_base_state())
        self.assertNotIn("last outline approval failed", prompt.lower())


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
