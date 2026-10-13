import type { LoginResponse, UsageCall, UsageQueryRow, UsageSummary, User } from "./types";

interface ErrorBody {
  detail?: string | Array<{ msg?: string }>;
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

export async function loginWithGoogle(apiUrl: string, idToken: string): Promise<LoginResponse> {
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

export async function fetchAdminSummary(apiUrl: string, token: string): Promise<UsageSummary> {
  const res = await fetch(`${apiUrl}/admin/usage/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 403) {
    throw new Error("This account is not an admin. Ask an admin to add your email to ADMIN_EMAILS on the backend.");
  }
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as UsageSummary;
}

export async function fetchAdminRecent(
  apiUrl: string,
  token: string,
  limit = 100
): Promise<UsageQueryRow[]> {
  const res = await fetch(`${apiUrl}/admin/usage/recent?limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 403) {
    throw new Error("This account is not an admin.");
  }
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as UsageQueryRow[];
}

export async function fetchAdminEntryUsage(
  apiUrl: string,
  id: number,
  token: string
): Promise<UsageCall[]> {
  const res = await fetch(`${apiUrl}/admin/searches/${id}/usage`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 403) {
    throw new Error("This account is not an admin.");
  }
  if (!res.ok) {
    throw new Error(await readError(res, `Request failed (${res.status}).`));
  }
  return (await res.json()) as UsageCall[];
}
