"""Focused checks for the token-usage collector (no DB, no network)."""

import unittest
from types import SimpleNamespace
from uuid import uuid4

from src.usage import UsageCollector, estimate_cost_usd, stage


def _llm_output_response(prompt, completion, model="gpt-4o-mini"):
    total = prompt + completion
    return SimpleNamespace(
        llm_output={
            "token_usage": {
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": total,
            },
            "model_name": model,
        },
        generations=[],
    )


class UsageCollectorTest(unittest.TestCase):
    def test_on_llm_end_labels_stage_and_counts_tokens(self):
        collector = UsageCollector(query="composting")
        with collector, stage("outline"):
            collector.on_llm_end(
                _llm_output_response(100, 50), run_id=uuid4()
            )
        (event,) = collector.events
        self.assertEqual(event["stage"], "outline")
        self.assertEqual(event["query"], "composting")
        self.assertEqual(event["prompt_tokens"], 100)
        self.assertEqual(event["completion_tokens"], 50)
        self.assertEqual(event["total_tokens"], 150)

    def test_summary_aggregates_by_stage_with_cost(self):
        collector = UsageCollector(query="q")
        with collector, stage("research"):
            collector.on_llm_end(_llm_output_response(1000, 500), run_id=uuid4())
            collector.on_llm_end(_llm_output_response(1000, 500), run_id=uuid4())
        with collector, stage("outline"):
            collector.on_llm_end(_llm_output_response(2000, 1000), run_id=uuid4())
        summary = collector.summary()
        self.assertEqual(summary["calls"], 3)
        self.assertEqual(summary["prompt_tokens"], 4000)
        self.assertEqual(summary["completion_tokens"], 2000)
        self.assertEqual(summary["total_tokens"], 6000)
        self.assertEqual(
            summary["est_cost_usd"],
            round(estimate_cost_usd("gpt-4o-mini", 4000, 2000), 6),
        )
        by_stage = {r["stage"]: r for r in summary["by_stage"]}
        self.assertEqual(by_stage["research"]["calls"], 2)
        self.assertEqual(by_stage["outline"]["total_tokens"], 3000)

    def test_usage_metadata_fallback(self):
        msg = SimpleNamespace(
            usage_metadata={
                "input_tokens": 30,
                "output_tokens": 10,
                "total_tokens": 40,
            },
            response_metadata={},
        )
        response = SimpleNamespace(
            llm_output={}, generations=[[SimpleNamespace(message=msg)]]
        )
        collector = UsageCollector(query="q")
        with collector, stage("summarize"):
            collector.on_llm_end(response, run_id=uuid4())
        (event,) = collector.events
        self.assertEqual((event["prompt_tokens"], event["completion_tokens"]), (30, 10))
        self.assertEqual(event["total_tokens"], 40)


if __name__ == "__main__":
    unittest.main()
