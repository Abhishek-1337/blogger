import os
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.research_agent import research_agent_node, verify_research_node
from src.schema import BlogState

load_dotenv()

MODEL = "gpt-4o-mini"
MAX_RESEARCH_REVISIONS = 2
MAX_OUTLINE_REVISIONS = 2

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


class OutlineVerdict(BaseModel):
    """LLM critique of the outline: approve or request a rewrite."""

    approved: bool = Field(description="True if the outline is good enough to keep")
    feedback: str = Field(
        default="",
        description="If not approved: specific actionable fixes for the rewrite. Empty if approved.",
    )


def _llm(temperature: float = 0.3) -> ChatOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not set.")
    return ChatOpenAI(model=MODEL, temperature=temperature)


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
    structured_llm = _llm(0.7).with_structured_output(BlogOutline)
    feedback = state.get("outline_feedback", "") or ""
    revisions = state.get("outline_revisions", 0) or 0
    previous = ""
    if state.get("sections"):
        previous = "\n".join(
            f"- {s.get('title', '')}: {'; '.join(s.get('bullets', []))}"
            for s in state["sections"]
        )
    retry_block = (
        f"""
    Previous attempt (revise, don't repeat its mistakes):
    {previous}

    Critic feedback to fix:
    {feedback}"""
        if feedback
        else ""
    )
    prompt = f"""Based on this research brief, create a blog outline of 4-6 sections.

    Research brief:
    {state['research_brief']}
{retry_block}
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
    return {
        "outline": outline,
        "sections": sections,
        "outline_revisions": revisions + 1,
        "outline_feedback": "",
    }


def verify_outline_node(state: BlogState) -> dict:
    critic = _llm(0.2).with_structured_output(OutlineVerdict)
    outline_text = "\n".join(
        f"{i}. {s.get('title', '')}\n"
        + "\n".join(f"   - {b}" for b in s.get("bullets", []))
        for i, s in enumerate(state["sections"], 1)
    )
    prompt = f"""You are a strict expertq blog editor. Topic: "{state['query']}"

    Research brief:
    {state['research_brief']}

    Proposed outline ({len(state['sections'])} sections):
    {outline_text}

    Approve only if ALL hold:
    - Covers the brief's key points with no major gap
    - Sections flow logically, no heavy overlap, titles specific (not generic)
    - Bullets are concrete and grounded in the brief (not filler)

    If any fail, approved=false with specific fixes (what to add/drop/merge/split)."""
    verdict = critic.invoke(prompt)
    return {"outline_approved": verdict.approved, "outline_feedback": verdict.feedback}


def _should_retry_research(state: BlogState) -> str:
    if state.get("research_approved"):
        return "summarize"
    if state.get("research_revisions", 0) >= MAX_RESEARCH_REVISIONS:
        return "summarize"
    return "research"


def _should_retry_outline(state: BlogState) -> str:
    if state.get("outline_approved"):
        return END
    if state.get("outline_revisions", 0) >= MAX_OUTLINE_REVISIONS:
        return END
    return "outline"


def build_graph():
    graph = StateGraph(BlogState)

    graph.add_node("research", research_agent_node)
    graph.add_node("verify_research", verify_research_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("outline", outline_node)
    graph.add_node("verify_outline", verify_outline_node)

    graph.set_entry_point("research")

    graph.add_conditional_edges(
        "verify_research",
        _should_retry_research,
        {"research": "research", "summarize": "summarize"},
    )
    graph.add_edge("research", "verify_research")
    graph.add_edge("summarize", "outline")
    graph.add_edge("outline", "verify_outline")

    graph.add_conditional_edges(
        "verify_outline", _should_retry_outline, {"outline": "outline", END: END}
    )

    return graph.compile()


def run_blog(query: str) -> dict:
    app = build_graph()
    return app.invoke(
        {
            "query": query,
            "search_results": [],
            "research_brief": "",
            "research_approved": False,
            "research_feedback": "",
            "research_revisions": 0,
            "outline": [],
            "sections": [],
            "outline_feedback": "",
            "outline_revisions": 0,
            "outline_approved": False,
        }
    )


def run_research(query: str) -> str:
    return run_blog(query)["research_brief"]
