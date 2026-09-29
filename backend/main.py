"""Phase 2 entrypoint: query -> research -> outline with section bullets."""

from src.graph import run_blog


def get_user_query() -> str:
    return input("Enter your query: ").strip()


def main():
    query = get_user_query()
    
    final = run_blog(query)
    print(final)

if __name__ == "__main__":
    main()
