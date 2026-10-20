import contextvars
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


_active_collector: contextvars.ContextVar = contextvars.ContextVar(
    "llm_usage_collector", default=None
)
_current_stage: contextvars.ContextVar = contextvars.ContextVar(
    "llm_usage_stage", default=""
)


def get_active_collector():
    return _active_collector.get()


@contextmanager
def stage(name: str):
    token = _current_stage.set(name)
    try:
        yield
    finally:
        _current_stage.reset(token)


def callback_config() -> dict:
    collector = _active_collector.get()
    if collector is None:
        return {}
    return {"callbacks": [collector]}


def _extract_tokens(response: Any) -> tuple[int, int, int, str]:
    prompt = completion = total = 0
    model = ""

    llm_output = getattr(response, "llm_output", None) or {}
    if isinstance(llm_output, dict):
        usage = llm_output.get("token_usage") or {}
        prompt = int(usage.get("prompt_tokens", 0) or 0)
        completion = int(usage.get("completion_tokens", 0) or 0)
        total = int(usage.get("total_tokens", 0) or 0)
        model = str(llm_output.get("model_name", "") or "")

    if total == 0:
        generations = getattr(response, "generations", None) or []
        for group in generations:
            for gen in group or []:
                message = getattr(gen, "message", None)
                if message is None:
                    continue
                meta = getattr(message, "usage_metadata", None) or {}
                if meta.get("total_tokens"):
                    prompt += int(meta.get("input_tokens", 0) or 0)
                    completion += int(meta.get("output_tokens", 0) or 0)
                    total += int(meta.get("total_tokens", 0) or 0)
                else:
                    tu = (getattr(message, "response_metadata", None) or {}).get(
                        "token_usage", {}
                    )
                    prompt += int(tu.get("prompt_tokens", 0) or 0)
                    completion += int(tu.get("completion_tokens", 0) or 0)
                    total += int(tu.get("total_tokens", 0) or 0)
                if not model:
                    model = str(
                        (getattr(message, "response_metadata", None) or {}).get(
                            "model_name", ""
                        )
                        or ""
                    )

    if total == 0:
        total = prompt + completion
    return prompt, completion, total, model or MODEL


class UsageCollector(BaseCallbackHandler):
    def __init__(self, query: str = ""):
        super().__init__()
        self.query = query
        self.events: list[dict] = []
        self._start_times: dict[str, float] = {}

    def on_llm_start(self, serialized: dict, prompts: list, *, run_id, **kwargs: Any) -> None:
        self._start_times[str(run_id)] = time.perf_counter()

    def on_llm_end(self, response: Any, *, run_id, **kwargs: Any) -> None:
        started = self._start_times.pop(str(run_id), None)
        latency_ms = int((time.perf_counter() - started) * 1000) if started else 0
        prompt, completion, total, model = _extract_tokens(response)
        self.events.append(
            {
                "query": self.query,
                "stage": _current_stage.get() or kwargs.get("run_name") or "unknown",
                "model": model,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": total,
                "latency_ms": latency_ms,
            }
        )

    def __enter__(self):
        self._token = _active_collector.set(self)
        return self

    def __exit__(self, *exc):
        _active_collector.reset(self._token)
        return False

    def summary(self) -> dict:
        by_stage: dict[str, dict] = {}
        for e in self.events:
            row = by_stage.setdefault(
                e["stage"],
                {
                    "stage": e["stage"],
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "latency_ms": 0,
                },
            )
            row["calls"] += 1
            row["prompt_tokens"] += e["prompt_tokens"]
            row["completion_tokens"] += e["completion_tokens"]
            row["total_tokens"] += e["total_tokens"]
            row["latency_ms"] += e["latency_ms"]
        for row in by_stage.values():
            row["avg_latency_ms"] = (
                int(row["latency_ms"] / row["calls"]) if row["calls"] else 0
            )
        return {
            "calls": len(self.events),
            "prompt_tokens": sum(e["prompt_tokens"] for e in self.events),
            "completion_tokens": sum(e["completion_tokens"] for e in self.events),
            "total_tokens": sum(e["total_tokens"] for e in self.events),
            "est_cost_usd": round(
                sum(
                    estimate_cost_usd(e["model"], e["prompt_tokens"], e["completion_tokens"])
                    for e in self.events
                ),
                6,
            ),
            "by_stage": sorted(by_stage.values(), key=lambda r: -r["total_tokens"]),
        }
