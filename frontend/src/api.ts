import type { BlogResponse } from "./types";

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
