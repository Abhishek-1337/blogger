import time
from contextlib import contextmanager
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

MODEL = "gpt-4o-mini"

PRICING_PER_1M = {
    MODEL: {"input": 0.15, "output": 0.60},
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = PRICING_PER_1M.get(model, PRICING_PER_1M[MODEL])
    return prompt_tokens / 1_000_000 * rates["input"] + completion_tokens / 1_000_000 * rates["output"]


active_collector = None
current_stage = ""


@contextmanager
def stage(name: str):
    global current_stage
    prev, current_stage = current_stage, name
    try:
        yield
    finally:
        current_stage = prev


def callback_config() -> dict:
    if active_collector is None:
        return {}
    return {"callbacks": [active_collector]}


def _num(value) -> int:
    return int(value or 0)


def _extract_tokens(response: Any) -> tuple[int, int, int, str]:
    prompt = completion = total = 0
    model = ""

    out = getattr(response, "llm_output", None) or {}
    if isinstance(out, dict):
        usage = out.get("token_usage") or {}
        prompt = _num(usage.get("prompt_tokens"))
        completion = _num(usage.get("completion_tokens"))
        total = _num(usage.get("total_tokens"))
        model = str(out.get("model_name") or "")

    if total == 0:
        for group in getattr(response, "generations", None) or []:
            for gen in group or []:
                msg = getattr(gen, "message", None)
                if msg is None:
                    continue
                meta = getattr(msg, "usage_metadata", None) or {}
                rm = getattr(msg, "response_metadata", None) or {}
                if meta.get("total_tokens"):
                    prompt += _num(meta.get("input_tokens"))
                    completion += _num(meta.get("output_tokens"))
                    total += _num(meta.get("total_tokens"))
                else:
                    tu = rm.get("token_usage") or {}
                    prompt += _num(tu.get("prompt_tokens"))
                    completion += _num(tu.get("completion_tokens"))
                    total += _num(tu.get("total_tokens"))
                model = model or str(rm.get("model_name") or "")

    if total == 0:
        total = prompt + completion
    return prompt, completion, total, model or MODEL


class UsageCollector(BaseCallbackHandler):
    def __init__(self, query: str = ""):
        super().__init__()
        self.query = query
        self.events: list[dict] = []
        self._start_times: dict[str, float] = {}

    def __enter__(self):
        global active_collector
        self._prev = active_collector
        active_collector = self
        return self

    def __exit__(self, *exc):
        global active_collector
        active_collector = self._prev
        return False

    def on_llm_start(self, serialized: dict, prompts: list, *, run_id, **kwargs: Any) -> None:
        self._start_times[str(run_id)] = time.perf_counter()

    def on_llm_end(self, response: Any, *, run_id, **kwargs: Any) -> None:
        started = self._start_times.pop(str(run_id), None)
        latency_ms = int((time.perf_counter() - started) * 1000) if started else 0
        prompt, completion, total, model = _extract_tokens(response)
        self.events.append(
            {
                "query": self.query,
                "stage": current_stage or kwargs.get("run_name") or "unknown",
                "model": model,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": total,
                "latency_ms": latency_ms,
            }
        )

    def summary(self) -> dict:
        by_stage: dict[str, dict] = {}
        for e in self.events:
            row = by_stage.setdefault(
                e["stage"],
                {"stage": e["stage"], "calls": 0, "prompt_tokens": 0,
                 "completion_tokens": 0, "total_tokens": 0, "latency_ms": 0},
            )
            row["calls"] += 1
            row["prompt_tokens"] += e["prompt_tokens"]
            row["completion_tokens"] += e["completion_tokens"]
            row["total_tokens"] += e["total_tokens"]
            row["latency_ms"] += e["latency_ms"]
        for row in by_stage.values():
            row["avg_latency_ms"] = row["latency_ms"] // row["calls"] if row["calls"] else 0
        return {
            "calls": len(self.events),
            "prompt_tokens": sum(e["prompt_tokens"] for e in self.events),
            "completion_tokens": sum(e["completion_tokens"] for e in self.events),
            "total_tokens": sum(e["total_tokens"] for e in self.events),
            "est_cost_usd": round(
                sum(estimate_cost_usd(e["model"], e["prompt_tokens"], e["completion_tokens"])
                    for e in self.events),
                6,
            ),
            "by_stage": sorted(by_stage.values(), key=lambda r: -r["total_tokens"]),
        }
