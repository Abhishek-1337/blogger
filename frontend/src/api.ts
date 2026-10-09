import type {
  BlogResponse,
  LoginResponse,
  SearchSummary,
  UsageCall,
  UsageQueryRow,
  UsageSummary,
  User,
} from "./types";

interface ErrorBody {
  detail?: string | Array<{ msg?: string }>;
}

function authHeaders(token: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export async function loginWithGoogle(
  apiUrl: string,
  idToken: string
): Promise<LoginResponse> {
  const res = await fetch(`${apiUrl}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
  });
  if (!res.ok) {
    throw new Error(await readError(res, `Sign-in failed (${res.status}).`));
  }
  return (await res.json()) as LoginResponse;
}

export async function fetchMe(apiUrl: string, token: string): Promise<User> {
  const res = await fetch(`${apiUrl}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(await readError(res, `Session expired (${res.status}).`));
  }
  return (await res.json()) as User;
}

export async function fetchBlog(
  query: string,
  apiUrl: string,
  token: string
): Promise<BlogResponse> {
  const res = await fetch(`${apiUrl}/blog`, {
    method: "POST",
    headers: authHeaders(token),
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

export async function fetchSearches(
  apiUrl: string,
  token: string
): Promise<SearchSummary[]> {
  const res = await fetch(`${apiUrl}/searches?limit=50`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as SearchSummary[];
}

export async function fetchSearch(
  apiUrl: string,
  id: number,
  token: string
): Promise<BlogResponse> {
  const res = await fetch(`${apiUrl}/searches/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as BlogResponse;
}

export async function fetchUsageSummary(
  apiUrl: string,
  token: string
): Promise<UsageSummary> {
  const res = await fetch(`${apiUrl}/usage/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as UsageSummary;
}

export async function fetchUsageOverview(
  apiUrl: string,
  token: string
): Promise<UsageSummary> {
  const res = await fetch(`${apiUrl}/usage/overview`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as UsageSummary;
}

export async function fetchUsageRecent(
  apiUrl: string,
  token: string,
  limit = 50
): Promise<UsageQueryRow[]> {
  const res = await fetch(`${apiUrl}/usage/recent?limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as UsageQueryRow[];
}

export async function fetchEntryUsage(
  apiUrl: string,
  id: number,
  token: string
): Promise<UsageCall[]> {
  const res = await fetch(`${apiUrl}/searches/${id}/usage`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as UsageCall[];
}
