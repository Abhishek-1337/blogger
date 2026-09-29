import os
from typing import TypedDict
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.tools import web_search

load_dotenv()

MODEL = "gpt-4o-mini"

class OutlineSection(BaseModel):
    """One blog section: title plus writer's talking points."""

    title: str = Field(description="Section title, no numbering, no description")
    bullets: list[str] = Field(
        min_length=3,
        max_length=5,
        description="3-5 concrete talking points the writer should cover in this section",
    )


class BlogOutline(BaseModel):
    """Structured outline: 4-6 sections, each with bullets."""

    sections: list[OutlineSection] = Field(
        min_length=4,
        max_length=6,
        description="4-6 blog sections in logical narrative flow order",
    )


class BlogState(TypedDict):
    query: str
    search_results: list[dict]
    research_brief: str
    outline: list[str]
    sections: list[dict]


def _llm(temperature: float = 0.3) -> ChatOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not set.")
    return ChatOpenAI(model=MODEL, temperature=temperature)


def _search_angles(query: str) -> list[str]:
    return [
        f"{query} overview explained",
        f"{query} latest trends 2025 2026",
        f"{query} key statistics and debates",
    ]


def research_node(state: BlogState) -> dict:
    query = state["query"]

    all_results: list[dict] = []
    for angle in _search_angles(query):
        all_results.extend(web_search(angle, max_results=5))

    seen, deduped = set(), []
    for r in all_results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            deduped.append(r)
    return {"search_results": deduped[:12]}


def summarize_node(state: BlogState) -> dict:
    llm = _llm(0.3)
    evidence = "\n".join(
        f"- {r.get('title', '')} ({r.get('url', '')}): {r.get('snippet', '')}"
        for r in state["search_results"]
    ) or "(no search results found)"

    prompt = f"""You are a blog research assistant. Topic: "{state['query']}"

    Web evidence:
    {evidence}

    Write a structured research brief with:
    1. Summary (3-5 sentences)
    2. Key points (5-7 bullets)
    3. Current trends 2025-2026 (3-5 bullets)
    4. Sources (list the URLs used)

    Keep it factual, cite only from the evidence above."""
    brief = llm.invoke(prompt).content
    return {"research_brief": brief}


def outline_node(state: BlogState) -> dict:
    structured_llm = _llm(0.4).with_structured_output(BlogOutline)
    prompt = f"""Based on this research brief, create a blog outline of 4-6 sections.

    Research brief:
    {state['research_brief']}

    Rules:
    - 4-6 sections in logical narrative flow, each building on the previous.
    - Each section: a short title plus 3-5 concrete talking points (facts, examples, stats from the brief).
    - No full prose, bullets only."""
    result = structured_llm.invoke(prompt)
    outline = [s.title.strip() for s in result.sections if s.title.strip()]
    sections = [
        {
            "title": s.title.strip(),
            "bullets": [b.strip() for b in s.bullets if b.strip()],
        }
        for s in result.sections
    ]
    if len(outline) < 4:
        raise ValueError(f"Outline validation failed. LLM returned:\n{result}")
    return {"outline": outline, "sections": sections}


def build_graph():
    graph = StateGraph(BlogState)

    graph.add_node("research", research_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("outline", outline_node)

    graph.set_entry_point("research")

    graph.add_edge("research", "summarize")
    graph.add_edge("summarize", "outline")
    graph.add_edge("outline", END)

    return graph.compile()


def run_blog(query: str) -> dict:
    app = build_graph()
    return app.invoke(
        {
            "query": query,
            "search_results": [],
            "research_brief": "",
            "outline": [],
            "sections": [],
        }
    )


# Backwards compat for Phase 1 callers
def run_research(query: str) -> str:
    return run_blog(query)["research_brief"]
