"""Phase 2 entrypoint: query -> research -> outline -> sequential sections."""

from src.graph import run_blog


def get_user_query() -> str:
    return input("Enter your query: ").strip()


def main():
    query = get_user_query()
    if not query:
        print("Empty query, exiting.")
        return
    print(f"\nResearching + writing: {query} ...\n")
    final = run_blog(query)

    print("=" * 60)
    print("RESEARCH BRIEF")
    print("=" * 60)
    print(final["research_brief"])

    print("\n" + "=" * 60)
    print("OUTLINE")
    print("=" * 60)
    for i, title in enumerate(final["outline"], 1):
        print(f"{i}. {title}")

    print("\n" + "=" * 60)
    print("BLOG")
    print("=" * 60)
    print(f"# {query}\n")
    for sec in final["sections"]:
        print(f"## {sec['title']}\n{sec['content']}\n")


if __name__ == "__main__":
    main()
