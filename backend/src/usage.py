"""Token-usage tracking for every LLM call in the blog pipeline.

A single :class:`UsageCollector` (a LangChain callback handler) lives for one
``run_blog`` execution. Each graph node sets the current *stage* and passes
the active collector as a callback, so even LLM calls hidden inside the
research agent are captured with per-call token counts and latency.

Token extraction tries, in order:
1. ``LLMResult.llm_output["token_usage"]`` (OpenAI-style dict)
2. ``generation.message.usage_metadata`` (LangChain ``input/output/total``)
3. ``generation.message.response_metadata["token_usage"]`` (OpenAI names)
"""

import contextvars
import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

# Pricing in USD per 1M tokens (gpt-4o-mini, public OpenAI pricing).
PRICING_PER_1M = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}
DEFAULT_MODEL = "gpt-4o-mini"


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = PRICING_PER_1M.get(model, PRICING_PER_1M[DEFAULT_MODEL])
    return prompt_tokens / 1_000_000 * rates["input"] + completion_tokens / 1_000_000 * rates["output"]


_active_collector: contextvars.ContextVar["UsageCollector | None"] = contextvars.ContextVar(
    "llm_usage_collector", default=None
)
_current_stage: contextvars.ContextVar[str] = contextvars.ContextVar(
    "llm_usage_stage", default=""
)


def get_active_collector() -> "UsageCollector | None":
    return _active_collector.get()


def get_current_stage() -> str:
    return _current_stage.get()


class _Stage:
    """``with stage("outline"):`` labels every LLM call inside the block."""

    def __init__(self, name: str):
        self._name = name
        self._token = None

    def __enter__(self):
        self._token = _current_stage.set(self._name)
        return self

    def __exit__(self, *exc):
        _current_stage.reset(self._token)
        return False


def stage(name: str) -> _Stage:
    return _Stage(name)


def _extract_tokens(response: Any) -> tuple[int, int, int, str]:
    """Return (prompt, completion, total, model) from an LLMResult."""
    prompt = completion = total = 0
    model = ""

    llm_output = getattr(response, "llm_output", None) or {}
    if isinstance(llm_output, dict):
        usage = llm_output.get("token_usage") or {}
        if isinstance(usage, dict):
            prompt = int(usage.get("prompt_tokens", 0) or 0)
            completion = int(usage.get("completion_tokens", 0) or 0)
            total = int(usage.get("total_tokens", 0) or 0)
        model = str(llm_output.get("model_name", "") or "")

    if total == 0:
        try:
            generations = getattr(response, "generations", []) or []
            flat = [g for sub in generations for g in (sub or [])]
            for gen in flat:
                msg = getattr(gen, "message", None)
                if msg is None:
                    continue
                meta = getattr(msg, "usage_metadata", None) or {}
                if meta.get("total_tokens"):
                    prompt += int(meta.get("input_tokens", 0) or 0)
                    completion += int(meta.get("output_tokens", 0) or 0)
                    total += int(meta.get("total_tokens", 0) or 0)
                else:
                    tu = (getattr(msg, "response_metadata", None) or {}).get(
                        "token_usage", {}
                    )
                    if tu.get("total_tokens"):
                        prompt += int(tu.get("prompt_tokens", 0) or 0)
                        completion += int(tu.get("completion_tokens", 0) or 0)
                        total += int(tu.get("total_tokens", 0) or 0)
                if not model:
                    model = str(
                        (getattr(msg, "response_metadata", None) or {}).get("model_name", "")
                        or ""
                    )
        except Exception:
            pass

    if total == 0 and (prompt or completion):
        total = prompt + completion
    return prompt, completion, total, model or DEFAULT_MODEL


class UsageCollector(BaseCallbackHandler):
    """LangChain callback that records token usage for every LLM response."""

    def __init__(self, query: str = ""):
        super().__init__()
        self.query = query
        self.events: list[dict] = []
        self._start_times: dict[str, float] = {}

    # -- LangChain callback API -------------------------------------------
    def on_llm_start(
        self, serialized: dict, prompts: list, *, run_id, **kwargs: Any
    ) -> None:
        try:
            self._start_times[str(run_id)] = time.perf_counter()
        except Exception:
            pass

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id,
        parent_run_id=None,
        tags: list | None = None,
        run_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        started = self._start_times.pop(str(run_id), None)
        latency_ms = (
            int((time.perf_counter() - started) * 1000) if started else 0
        )
        prompt, completion, total, model = _extract_tokens(response)
        tags = tags or kwargs.get("tags") or []
        run_name = run_name or kwargs.get("run_name") or ""
        self.events.append(
            {
                "query": self.query,
                "stage": get_current_stage() or run_name or "unknown",
                "model": model,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": total,
                "latency_ms": latency_ms,
                "tags": list(tags),
            }
        )

    # -- run-scoped helpers -------------------------------------------------
    def __enter__(self) -> "UsageCollector":
        self._token = _active_collector.set(self)
        return self

    def __exit__(self, *exc):
        _active_collector.reset(self._token)
        return False

    @property
    def callbacks(self) -> list["UsageCollector"]:
        """Pass ``collector.callbacks`` as LangChain ``callbacks=``."""
        return [self]

    def summary(self) -> dict:
        prompt = sum(e["prompt_tokens"] for e in self.events)
        completion = sum(e["completion_tokens"] for e in self.events)
        total = sum(e["total_tokens"] for e in self.events)
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
            row["avg_latency_ms"] = (
                int(row["latency_ms"] / row["calls"]) if row["calls"] else 0
            )
        return {
            "calls": len(self.events),
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            "est_cost_usd": round(
                sum(
                    estimate_cost_usd(e["model"], e["prompt_tokens"], e["completion_tokens"])
                    for e in self.events
                ),
                6,
            ),
            "by_stage": sorted(by_stage.values(), key=lambda r: -r["total_tokens"]),
        }
