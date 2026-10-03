import type { BlogResponse, SearchSummary } from "./types";

interface ErrorBody {
  detail?: string | Array<{ msg?: string }>;
}

export async function fetchBlog(query: string, apiUrl: string): Promise<BlogResponse> {
  const res = await fetch(`${apiUrl}/blog`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status}).`;
    try {
      const body = (await res.json()) as ErrorBody;
      if (body && body.detail) {
        detail =
          typeof body.detail === "string"
            ? body.detail
            : body.detail
                .map((d) => d.msg ?? "Invalid input")
                .join("; ");
      }
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return (await res.json()) as BlogResponse;
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const body = (await res.json()) as ErrorBody;
    if (body && body.detail) {
      return typeof body.detail === "string"
        ? body.detail
        : body.detail.map((d) => d.msg ?? "Invalid input").join("; ");
    }
  } catch {
    /* keep fallback */
  }
  return fallback;
}

export async function fetchSearches(apiUrl: string): Promise<SearchSummary[]> {
  const res = await fetch(`${apiUrl}/searches?limit=50`);
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as SearchSummary[];
}

export async function fetchSearch(
  apiUrl: string,
  id: number
): Promise<BlogResponse> {
  const res = await fetch(`${apiUrl}/searches/${id}`);
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as BlogResponse;
}
