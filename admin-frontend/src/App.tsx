import { useCallback, useEffect, useState } from "react";
import {
  fetchAdminEntryUsage,
  fetchAdminRecent,
  fetchAdminSummary,
} from "./api";
import { AuthProvider, GoogleSignInButton, useAuth } from "./auth";
import type { UsageCall, UsageQueryRow, UsageSummary } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "";

function fmt(n: number): string {
  return n.toLocaleString();
}

function fmtCost(usd: number): string {
  return usd < 0.01 ? `$${usd.toFixed(4)}` : `$${usd.toFixed(2)}`;
}

function Card({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-line bg-white p-4 shadow-sm">
      <p className="text-[13px] font-semibold text-fog">{label}</p>
      <p className="mt-1 font-serif text-2xl font-bold tracking-tight">{value}</p>
      {sub && <p className="mt-1 text-xs text-fog">{sub}</p>}
    </div>
  );
}

function SignInScreen() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col items-center justify-center px-5">
      <div className="w-full rounded-xl border border-line bg-white p-8 text-center shadow-sm">
        <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-md bg-pine font-serif text-2xl font-bold text-white">
          B
        </span>
        <h1 className="mt-4 font-serif text-2xl font-bold tracking-tight">
          Blogger Admin
        </h1>
        <p className="mt-2 text-sm text-fog">
          Token usage and cost observability. Sign in with an admin Google
          account.
        </p>
        <div className="mt-6">
          <GoogleSignInButton />
        </div>
      </div>
    </div>
  );
}

function EntryDrilldown({
  row,
  token,
  onClose,
}: {
  row: UsageQueryRow;
  token: string;
  onClose: () => void;
}) {
  const [calls, setCalls] = useState<UsageCall[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchAdminEntryUsage(API_URL, row.id, token)
      .then((c) => {
        if (!cancelled) {
          setCalls(c);
          setError("");
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [row.id, token]);

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-white shadow-sm">
      <div className="flex items-start justify-between gap-3 px-4 pt-4">
        <div>
          <h3 className="font-serif text-lg font-bold tracking-tight">
            Per-call breakdown
          </h3>
          <p className="mt-0.5 max-w-xl truncate text-sm text-fog" title={row.query}>
            {row.query}
            {row.user_email ? ` · ${row.user_email}` : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-line px-3 py-1.5 text-[13px] font-semibold transition-colors hover:bg-wash/70"
        >
          Close
        </button>
      </div>
      <div className="overflow-x-auto p-4 pt-2">
        {loading ? (
          <p className="py-4 text-center text-sm text-fog">Loading calls…</p>
        ) : error ? (
          <p className="py-4 text-center text-sm text-fog">{error}</p>
        ) : !calls || calls.length === 0 ? (
          <p className="py-4 text-center text-sm text-fog">
            No per-call events stored for this query.
          </p>
        ) : (
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[13px] text-fog">
                <th className="py-2 pr-3 font-medium">Stage</th>
                <th className="py-2 pr-3 font-medium">Model</th>
                <th className="py-2 pr-3 text-right font-medium">Input</th>
                <th className="py-2 pr-3 text-right font-medium">Output</th>
                <th className="py-2 pr-3 text-right font-medium">Total</th>
                <th className="py-2 text-right font-medium">Latency</th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.id} className="border-b border-line/60 last:border-0">
                  <td className="py-2 pr-3">{c.stage}</td>
                  <td className="max-w-[160px] truncate py-2 pr-3 text-fog" title={c.model}>
                    {c.model}
                  </td>
                  <td className="py-2 pr-3 text-right">{fmt(c.prompt_tokens)}</td>
                  <td className="py-2 pr-3 text-right">{fmt(c.completion_tokens)}</td>
                  <td className="py-2 pr-3 text-right font-semibold">
                    {fmt(c.total_tokens)}
                  </td>
                  <td className="py-2 text-right text-fog">{fmt(c.latency_ms)} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

function Dashboard({ token }: { token: string }) {
  const { user, signOut } = useAuth();
  const [data, setData] = useState<UsageSummary | null>(null);
  const [rows, setRows] = useState<UsageQueryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<UsageQueryRow | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [summary, recent] = await Promise.all([
        fetchAdminSummary(API_URL, token),
        fetchAdminRecent(API_URL, token),
      ]);
      setData(summary);
      setRows(recent);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load usage.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="min-h-screen bg-white font-sans text-ink antialiased">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-5 py-3">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-pine font-serif text-lg font-bold text-white">
              B
            </span>
            <div>
              <p className="font-serif text-lg font-bold leading-tight tracking-tight">
                Blogger Admin
              </p>
              <p className="text-xs text-fog">Token &amp; cost observability</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden max-w-[220px] truncate text-sm text-fog sm:block">
              {user?.email}
            </span>
            <button
              type="button"
              onClick={load}
              className="rounded-lg border border-line px-3 py-1.5 text-[13px] font-semibold transition-colors hover:bg-wash/70"
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={signOut}
              className="rounded-lg bg-pine px-3 py-1.5 text-[13px] font-semibold text-white transition-colors hover:bg-pinedeep"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-5 py-7">
        {loading ? (
          <p className="py-8 text-center text-sm text-fog">Loading usage…</p>
        ) : error ? (
          <div className="rounded-xl border border-line bg-white p-6 text-center shadow-sm">
            <p className="text-sm text-fog">{error}</p>
            <button
              type="button"
              onClick={() => void load()}
              className="mt-3 rounded-lg border border-line px-3 py-1.5 text-[13px] font-semibold transition-colors hover:bg-wash/70"
            >
              Retry
            </button>
          </div>
        ) : !data || data.totals.llm_calls === 0 ? (
          <div className="rounded-xl border border-line bg-white p-6 text-center shadow-sm">
            <p className="font-serif text-lg font-bold">No token usage yet</p>
            <p className="mt-1 text-sm text-fog">
              Generate a blog in the main app and usage will show up here.
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              <Card
                label="Total tokens"
                value={fmt(data.totals.total_tokens)}
                sub={`${fmt(data.totals.prompt_tokens)} in · ${fmt(data.totals.completion_tokens)} out`}
              />
              <Card
                label="Est. cost"
                value={fmtCost(data.totals.est_cost_usd)}
                sub="gpt-4o-mini rates"
              />
              <Card
                label="Queries tracked"
                value={fmt(data.totals.queries_tracked)}
                sub={`${fmt(data.totals.llm_calls)} LLM calls`}
              />
              <Card
                label="Avg tokens / query"
                value={fmt(Math.round(data.totals.avg_tokens_per_query))}
              />
              <Card label="Input tokens" value={fmt(data.totals.prompt_tokens)} />
              <Card label="Output tokens" value={fmt(data.totals.completion_tokens)} />
            </div>

            <section className="rounded-xl border border-line bg-white p-4 shadow-sm">
              <h3 className="font-serif text-lg font-bold tracking-tight">
                Tokens by pipeline stage
              </h3>
              <StageBars stages={data.by_stage} />
            </section>

            {data.by_day.length > 0 && (
              <section className="rounded-xl border border-line bg-white p-4 shadow-sm">
                <h3 className="font-serif text-lg font-bold tracking-tight">
                  Daily trend{" "}
                  <span className="text-sm font-normal text-fog">(last 14 days)</span>
                </h3>
                <DayBars days={data.by_day} />
              </section>
            )}

            {selected && (
              <EntryDrilldown
                row={selected}
                token={token}
                onClose={() => setSelected(null)}
              />
            )}

            <section className="overflow-hidden rounded-xl border border-line bg-white shadow-sm">
              <h3 className="px-4 pt-4 font-serif text-lg font-bold tracking-tight">
                All queries
              </h3>
              <p className="px-4 text-xs text-fog">
                Select a row for the per-call breakdown.
              </p>
              <div className="overflow-x-auto p-4 pt-2">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-line text-[13px] text-fog">
                      <th className="py-2 pr-3 font-medium">Query</th>
                      <th className="py-2 pr-3 font-medium">User</th>
                      <th className="py-2 pr-3 font-medium">Calls</th>
                      <th className="py-2 pr-3 text-right font-medium">Input</th>
                      <th className="py-2 pr-3 text-right font-medium">Output</th>
                      <th className="py-2 pr-3 text-right font-medium">Total</th>
                      <th className="py-2 text-right font-medium">Est. cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr
                        key={r.id}
                        onClick={() => setSelected(r)}
                        className={`cursor-pointer border-b border-line/60 last:border-0 hover:bg-wash/60 ${
                          selected?.id === r.id ? "bg-wash/60" : ""
                        }`}
                      >
                        <td className="max-w-[220px] truncate py-2 pr-3" title={r.query}>
                          {r.query}
                        </td>
                        <td
                          className="max-w-[160px] truncate py-2 pr-3 text-fog"
                          title={r.user_email ?? ""}
                        >
                          {r.user_email || "—"}
                        </td>
                        <td className="py-2 pr-3">{r.calls || "—"}</td>
                        <td className="py-2 pr-3 text-right">{fmt(r.prompt_tokens)}</td>
                        <td className="py-2 pr-3 text-right">
                          {fmt(r.completion_tokens)}
                        </td>
                        <td className="py-2 pr-3 text-right font-semibold">
                          {fmt(r.total_tokens)}
                        </td>
                        <td className="py-2 text-right text-fog">
                          {r.total_tokens ? fmtCost(r.est_cost_usd) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="border-t border-line px-4 py-2 text-xs text-fog">
                {data.pricing_note}
              </p>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function StageBars({ stages }: { stages: UsageSummary["by_stage"] }) {
  const max = Math.max(...stages.map((s) => s.total_tokens), 1);
  return (
    <div className="mt-3 space-y-3">
      {stages.map((s) => (
        <div key={s.stage}>
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span className="font-medium">{s.stage}</span>
            <span className="text-fog">
              {fmt(s.total_tokens)} tok · {s.calls} call
              {s.calls === 1 ? "" : "s"} · avg {fmt(s.avg_latency_ms)} ms
            </span>
          </div>
          <div
            className="mt-1 h-2 overflow-hidden rounded-full bg-wash"
            role="img"
            aria-label={`${s.stage}: ${s.total_tokens} tokens`}
          >
            <div
              className="h-full rounded-full bg-pine"
              style={{ width: `${(s.total_tokens / max) * 100}%` }}
            />
          </div>
          <p className="mt-0.5 text-xs text-fog">
            {fmt(s.prompt_tokens)} in / {fmt(s.completion_tokens)} out
          </p>
        </div>
      ))}
    </div>
  );
}

function DayBars({ days }: { days: UsageSummary["by_day"] }) {
  const ordered = [...days].reverse();
  const max = Math.max(...ordered.map((d) => d.total_tokens), 1);
  return (
    <div className="mt-3 flex h-28 items-end gap-1.5">
      {ordered.map((d) => (
        <div
          key={d.day}
          className="flex min-w-0 flex-1 flex-col items-center gap-1"
          title={`${d.day}: ${fmt(d.total_tokens)} tokens, ${d.queries} queries`}
        >
          <div
            className="w-full rounded-t bg-pine/80"
            style={{ height: `${Math.max((d.total_tokens / max) * 100, 3)}%` }}
          />
          <span className="w-full truncate text-center text-[10px] text-fog">
            {d.day.slice(5)}
          </span>
        </div>
      ))}
    </div>
  );
}

function GatedApp() {
  const { user, token, ready } = useAuth();
  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-fog">Loading…</p>
      </div>
    );
  }
  if (!user || !token) return <SignInScreen />;
  return <Dashboard token={token} />;
}

export default function App() {
  return (
    <AuthProvider apiUrl={API_URL}>
      <GatedApp />
    </AuthProvider>
  );
}
