import type {
  BlogResponse,
  LoginResponse,
  SearchSummary,
  TaskStatus,
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

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function fetchBlog(
  query: string,
  apiUrl: string,
  token: string,
  onStage?: (stage: string) => void
): Promise<BlogResponse> {
  const res = await fetch(`${apiUrl}/blog/enqueue`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  const { task_id } = (await res.json()) as { task_id: string };
  for (let i = 0; i < 300; i++) {
    await sleep(2000);
    const st = await fetch(`${apiUrl}/blog/tasks/${task_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!st.ok) {
      throw new Error(await readError(st, `Request failed (${st.status}).`));
    }
    const s = (await st.json()) as TaskStatus;
    if (s.stage) onStage?.(s.stage);
    if (s.status === "SUCCESS") {
      if (s.entry_id == null) {
        throw new Error("Task finished without a result.");
      }
      return fetchSearch(apiUrl, s.entry_id, token);
    }
    if (s.status === "FAILURE") {
      throw new Error(s.error || "Blog generation failed.");
    }
  }
  throw new Error("Blog generation timed out.");
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


