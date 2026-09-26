"""Phase 2: research -> outline -> sequential section loop.

Flow: research (web) -> summarize (brief) -> outline -> section* -> END
The section node loops over the outline, passing only a rolling
summary + previous section tail forward (not full history).
"""

import os
import re
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.tools import web_search

load_dotenv()

MODEL = "gpt-4o-mini"


class BlogState(TypedDict):
    query: str
    search_results: list[dict]
    research_brief: str
    outline: list[str]
    sections: list[dict]
    rolling_summary: str
    next_index: int


def _llm(temperature: float = 0.3) -> ChatOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not set. Copy .env.example to .env and add your key.")
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


def _parse_outline(text: str) -> list[str]:
    titles = []
    for line in text.strip().splitlines():
        line = line.strip()
        # match "1. Title" / "1) Title" / "- Title"
        m = re.match(r"^(?:\d+[\.\)]\s*|[-*]\s*)(.+)$", line)
        if m:
            titles.append(m.group(1).strip())
        elif line and len(titles) < 6:
            titles.append(line)
    return [t for t in titles if t][:6]


def outline_node(state: BlogState) -> dict:
    llm = _llm(0.4)
    prompt = f"""Based on this research brief, create a blog outline of 4-6 sections.

Research brief:
{state['research_brief']}

Rules:
- Output ONLY a numbered list of section titles, one per line.
- No intro, no descriptions, no extra text.
- Each title must relate to the next (logical narrative flow)."""
    raw = llm.invoke(prompt).content
    outline = _parse_outline(raw)
    if not outline:
        raise ValueError(f"Outline parsing failed. LLM returned:\n{raw}")
    return {
        "outline": outline,
        "sections": [],
        "rolling_summary": "",
        "next_index": 0,
    }


def section_node(state: BlogState) -> dict:
    llm_write = _llm(0.7)
    llm_sum = _llm(0.2)

    idx = state["next_index"]
    title = state["outline"][idx]
    sections = state.get("sections", []) or []
    rolling = state.get("rolling_summary", "") or ""

    prev_tail = ""
    if sections:
        prev_tail = sections[-1]["content"][-800:]

    context = f"""Topic: {state['query']}
Section {idx + 1}/{len(state['outline'])}: {title}
Full outline: {' | '.join(state['outline'])}

Research brief:
{state['research_brief']}

Story so far (summaries of previous sections):
{rolling or '(this is the first section)'}

Tail of previous section (for smooth transition):
{prev_tail or '(none)'}
"""

    content = llm_write.invoke(
        f"{context}\nWrite ONLY the body of section '{title}' (~250-350 words). "
        "Continue the narrative from the story so far. No recap of the whole blog, no conclusion unless it's the final section."
    ).content

    summary = llm_sum.invoke(
        f"Summarize this blog section in 2 lines (facts + narrative position):\n{content}"
    ).content

    new_rolling = (rolling + f"\n- {title}: {summary.strip()}").strip()
    return {
        "sections": sections + [{"title": title, "content": content}],
        "rolling_summary": new_rolling,
        "next_index": idx + 1,
    }


def _should_continue(state: BlogState) -> str:
    if state["next_index"] < len(state["outline"]):
        return "section"
    return END


def build_graph():
    graph = StateGraph(BlogState)
    graph.add_node("research", research_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("outline", outline_node)
    graph.add_node("section", section_node)
    graph.set_entry_point("research")
    graph.add_edge("research", "summarize")
    graph.add_edge("summarize", "outline")
    graph.add_edge("outline", "section")
    graph.add_conditional_edges("section", _should_continue, {"section": "section", END: END})
    return graph.compile()


def run_blog(query: str) -> dict:
    """Run the full pipeline, return final state (brief, outline, sections)."""
    app = build_graph()
    return app.invoke(
        {
            "query": query,
            "search_results": [],
            "research_brief": "",
            "outline": [],
            "sections": [],
            "rolling_summary": "",
            "next_index": 0,
        }
    )


# Backwards compat for Phase 1 callers
def run_research(query: str) -> str:
    return run_blog(query)["research_brief"]
