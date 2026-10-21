import json
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.schema import BlogState
from src.tools import aweb_search
from src.usage import callback_config, stage

load_dotenv()

MODEL = "gpt-4o-mini"
MAX_RESULTS = 12
MAX_RESEARCH_REVISIONS = 2

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
async def search_web(query: str, max_results: int = 5) -> str:
    """Search the live web for one focused angle of the topic."""
    return json.dumps(await aweb_search(query, max_results=max_results))


tools = [search_web]


def _dedupe(results: list[dict], limit: int = MAX_RESULTS) -> list[dict]:
    seen = set()
    unique = []
    for r in results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)
    return unique[:limit]


class ResearchVerdict(BaseModel):
    approved: bool = Field(description="True if the evidence is good enough to keep")
    feedback: str = Field(
        default="",
        description="If not approved: what is missing and which angles to re-search. Empty if approved.",
    )


async def _verify_results(query: str, search_results: list[dict]) -> ResearchVerdict:
    critic = _llm(0.2).with_structured_output(ResearchVerdict)
    evidence = "\n".join(
        f"{i}. {r.get('title', '')} ({r.get('url', '')}): "
        f"{(r.get('snippet', '') or '')[:400]}"
        for i, r in enumerate(search_results, 1)
    )
    prompt = f"""You are a strict research editor. Topic: "{query}"

Collected evidence ({len(search_results)} results):
{evidence}

Approve only if ALL hold:
- Every result is actually about the topic (no off-topic or generic filler)
- More than one angle is covered (not all results saying the same thing)
- Snippets contain real substance (facts, numbers, examples — not nav text)
- At least 6 usable results

If any fail, approved=false with specific fixes (which angles are missing,
what to re-search)."""
    with stage("verify_research"):
        return await critic.ainvoke(prompt, config=callback_config())


async def _run_research_pass(query: str, feedback: str) -> list[dict]:
    content = f"Research this topic: {query}"
    if feedback:
        content += (
            "\nA previous attempt was rejected — adjust your searches accordingly:\n"
            f"Critic feedback: {feedback}"
        )
    agent = create_agent(_llm(), tools, system_prompt=RESEARCH_PROMPT)
    with stage("research"):
        result = await agent.ainvoke({"messages": [{"role": "user", "content": content}]}, config=callback_config())

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
        collected = await aweb_search(query, max_results=MAX_RESULTS)
    return collected


async def research_agent_node(state: BlogState) -> dict:
    revisions = state.get("research_revisions", 0) or 0
    feedback = state.get("research_feedback", "") or ""
    accumulated: list[dict] = list(state.get("search_results", []) or [])
    approved = False

    for _ in range(MAX_RESEARCH_REVISIONS):
        collected = await _run_research_pass(state["query"], feedback)
        accumulated = _dedupe([*accumulated, *collected])
        verdict = await _verify_results(state["query"], accumulated)
        approved = verdict.approved
        revisions += 1
        feedback = "" if approved else verdict.feedback
        if approved:
            break

    return {
        "search_results": accumulated,
        "research_revisions": revisions,
        "research_approved": approved,
        "research_feedback": feedback,
    }
