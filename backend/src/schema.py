from typing import TypedDict

class BlogState(TypedDict):
    query: str
    search_results: list[dict]
    research_brief: str
    research_approved: bool
    research_feedback: str
    research_revisions: int
    outline: list[str]
    sections: list[dict]
    outline_feedback: str
    outline_revisions: int
    outline_approved: bool

