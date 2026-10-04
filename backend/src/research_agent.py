"""ReAct research agent: one angle in, evidence out.

The agent loop (plan angle -> search -> observe -> repeat) is driven by the
LLM through ``create_react_agent``. The graph never trusts the transcript:
``research_agent_node`` rebuilds ``search_results`` deterministically from the
tool messages, so the downstream pipeline sees the same shape it always has.
``verify_research_node`` then gates quality like the outline critic does.
"""

import json
import os

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from src.schema import BlogState
from src.tools import web_search

load_dotenv()

MODEL = "gpt-4o-mini"
MAX_RESULTS = 12

RESEARCH_PROMPT = """You are a blog research assistant. Research the given topic
thoroughly using the search_web tool.

Run 3-5 searches covering distinct angles (e.g. an overview, current
2025-2026 trends, and key statistics or debates). Use specific queries and
vary them based on what you already found. When you have enough evidence,
stop calling tools and reply with RESEARCH COMPLETE."""


def _llm(temperature: float = 0.3) -> ChatOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not set.")
    return ChatOpenAI(model=MODEL, temperature=temperature)


@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the live web for one focused angle of the topic.

    Args:
        query: A specific search query, e.g. "urban composting odor control".
        max_results: How many hits to return (3-8 is plenty per angle).

    Returns a JSON list of {"title", "url", "snippet"} objects.
    """
    return json.dumps(web_search(query, max_results=max_results))


tools = [search_web]


def _dedupe(results: list[dict], limit: int = MAX_RESULTS) -> list[dict]:
    seen, deduped = set(), []
    for r in results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            deduped.append(r)
    return deduped[:limit]


class ResearchVerdict(BaseModel):
    """LLM critique of the collected evidence: good enough or re-search."""

    approved: bool = Field(description="True if the evidence is good enough to keep")
    feedback: str = Field(
        default="",
        description="If not approved: what is missing and which angles to re-search. Empty if approved.",
    )


def verify_research_node(state: BlogState) -> dict:
    critic = _llm(0.2).with_structured_output(ResearchVerdict)
    evidence = "\n".join(
        f"{i}. {r.get('title', '')} ({r.get('url', '')}): "
        f"{(r.get('snippet', '') or '')[:400]}"
        for i, r in enumerate(state["search_results"], 1)
    )
    prompt = f"""You are a strict research editor. Topic: "{state['query']}"

Collected evidence ({len(state['search_results'])} results):
{evidence}

Approve only if ALL hold:
- Every result is actually about the topic (no off-topic or generic filler)
- More than one angle is covered (not all results saying the same thing)
- Snippets contain real substance (facts, numbers, examples — not nav text)
- At least 6 usable results

If any fail, approved=false with specific fixes (which angles are missing,
what to re-search)."""
    verdict = critic.invoke(prompt)
    return {
        "research_approved": verdict.approved,
        "research_feedback": verdict.feedback,
    }


def research_agent_node(state: BlogState) -> dict:
    """Run the research agent; return evidence plus revision bookkeeping."""
    revisions = state.get("research_revisions", 0) or 0
    feedback = state.get("research_feedback", "") or ""
    retry_block = (
        "\nA previous attempt was rejected — adjust your searches accordingly:\n"
        f"Critic feedback: {feedback}"
        if feedback
        else ""
    )
    agent = create_react_agent(_llm(), tools, prompt=RESEARCH_PROMPT)
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Research this topic: {state['query']}{retry_block}",
                }
            ]
        }
    )

    collected: list[dict] = []
    for m in result["messages"]:
        if m.type != "tool":
            continue
        try:
            payload = json.loads(m.content)
        except (ValueError, TypeError):
            continue
        if isinstance(payload, list):
            collected.extend(r for r in payload if isinstance(r, dict))

    if not collected:
        # Agent answered without searching — never starve the pipeline.
        collected = web_search(state["query"], max_results=MAX_RESULTS)

    return {
        "search_results": _dedupe(collected),
        "research_revisions": revisions + 1,
        "research_feedback": "",
    }
