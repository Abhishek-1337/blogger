import { useCallback, useEffect, useState } from "react";
import { fetchAdminEntryUsage, fetchAdminRecent, fetchAdminSummary } from "./api";
import { AuthProvider, GoogleSignInButton, useAuth } from "./auth";
import type { UsageCall, UsageQueryRow, UsageSummary } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "";

function fmt(n: number): string { return n.toLocaleString(); }
function fmtCost(usd: number): string { return usd < 0.01 ? `$${usd.toFixed(4)}` : `$${usd.toFixed(2)}`; }
function fmtLatency(ms: number): string { return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${fmt(ms)} ms`; }

function Card({ label, value, sub, accent = false }: { label: string; value: string; sub?: string; accent?: boolean }) {
  if (accent) {
    return (
      <div className="rounded-2xl bg-pinedeep p-5 text-white shadow-card dark:bg-sage dark:text-[#0b1511]">
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-white/60 dark:text-[#0b1511]/60">{label}</p>
        <p className="mt-1.5 font-serif text-[32px] font-bold leading-none tracking-tight">{value}</p>
        {sub && <p className="mt-2 text-[13px] text-white/70 dark:text-[#0b1511]/70">{sub}</p>}
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-line bg-white p-5 shadow-card dark:border-white/10 dark:bg-panel">
      <p className="font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-fog">{label}</p>
      <p className="mt-1.5 font-serif text-[28px] font-bold leading-none tracking-tight">{value}</p>
      {sub && <p className="mt-2 text-[13px] text-fog">{sub}</p>}
    </div>
  );
}

function SignInScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-5 py-10 dark:bg-night">
      <div className="w-full max-w-sm animate-rise">
        <div className="flex items-center gap-2.5">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-[10px] bg-pinedeep font-serif text-xl font-bold text-white dark:bg-sage dark:text-[#0b1511]">B</span>
          <span className="font-serif text-[22px] font-bold tracking-tight">Blogger <span className="font-sans text-sm font-semibold text-fog">Admin</span></span>
        </div>
        <h1 className="mt-6 font-serif text-[30px] font-bold leading-tight tracking-tight">Usage &amp; cost observability</h1>
        <p className="mt-2 text-[15px] leading-relaxed text-fog">Sign in with an admin Google account to see tokens, cost, and latency across every generation.</p>
        <div className="mt-7 rounded-2xl border border-line bg-white p-6 shadow-card dark:border-white/10 dark:bg-panel">
          <GoogleSignInButton />
          <p className="mt-4 text-center text-[13px] text-fog">Admin allowlist applies. Non-admin accounts are rejected.</p>
        </div>
      </div>
    </div>
  );
}

function EntryDrilldown({ row, token, onClose }: { row: UsageQueryRow; token: string; onClose: () => void }) {
  const [calls, setCalls] = useState<UsageCall[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchAdminEntryUsage(API_URL, row.id, token)
      .then((c) => { if (!cancelled) { setCalls(c); setError(""); } })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [row.id, token]);

  const totalLatency = calls?.reduce((a, c) => a + c.latency_ms, 0) ?? 0;

  return (
    <section className="overflow-hidden rounded-2xl border border-pine/25 bg-white shadow-card animate-rise dark:border-sage/25 dark:bg-panel" aria-label="Per-call breakdown">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4 dark:border-white/[0.07]">
        <div className="min-w-0">
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-ochre dark:text-ochrebright">Drill-down</p>
          <h3 className="mt-1 font-serif text-lg font-bold tracking-tight">Per-call breakdown</h3>
          <p className="mt-0.5 max-w-xl truncate text-sm text-fog" title={row.query}>{row.query}{row.user_email ? ` · ${row.user_email}` : ""}</p>
        </div>
        <div className="flex items-center gap-2">
          {calls && calls.length > 0 && <span className="rounded-full bg-wash px-2.5 py-1 font-mono text-[11px] text-fog dark:bg-white/[0.06]">{calls.length} calls · {fmtLatency(totalLatency)} total</span>}
          <button type="button" onClick={onClose} className="rounded-lg border border-line px-3 py-1.5 text-[13px] font-semibold transition hover:bg-wash dark:border-white/10 dark:hover:bg-white/[0.07]">Close ✕</button>
        </div>
      </div>
      <div className="overflow-x-auto p-4 pt-2">
        {loading ? <p className="py-6 text-center text-sm text-fog">Loading calls…</p>
        : error ? <p role="alert" className="py-6 text-center text-sm text-clay dark:text-rose">{error}</p>
        : !calls || calls.length === 0 ? <p className="py-6 text-center text-sm text-fog">No per-call events stored for this query.</p>
        : (
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead><tr className="border-b border-line font-mono text-[11px] uppercase tracking-wide text-fog dark:border-white/[0.07]">
              <th className="py-2.5 pr-3 font-medium">Stage</th><th className="py-2.5 pr-3 font-medium">Model</th>
              <th className="py-2.5 pr-3 text-right font-medium">Input</th><th className="py-2.5 pr-3 text-right font-medium">Output</th>
              <th className="py-2.5 pr-3 text-right font-medium">Total</th><th className="py-2.5 text-right font-medium">Latency</th>
            </tr></thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.id} className="border-b border-line/60 last:border-0 dark:border-white/[0.05]">
                  <td className="py-2.5 pr-3"><span className="rounded-full bg-wash px-2 py-0.5 text-[12px] font-semibold dark:bg-white/[0.06]">{c.stage}</span></td>
                  <td className="max-w-[160px] truncate py-2.5 pr-3 font-mono text-[12px] text-fog" title={c.model}>{c.model}</td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">{fmt(c.prompt_tokens)}</td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">{fmt(c.completion_tokens)}</td>
                  <td className="py-2.5 pr-3 text-right font-semibold tabular-nums">{fmt(c.total_tokens)}</td>
                  <td className="py-2.5 text-right tabular-nums text-fog">{fmtLatency(c.latency_ms)}</td>
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
      const [summary, recent] = await Promise.all([fetchAdminSummary(API_URL, token), fetchAdminRecent(API_URL, token)]);
      setData(summary); setRows(recent); setError("");
    } catch (e) { setError(e instanceof Error ? e.message : "Failed to load usage."); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="min-h-screen bg-paper font-sans text-ink antialiased dark:bg-night">
      <header className="sticky top-0 z-40 border-b border-line bg-white/85 backdrop-blur-md dark:border-white/[0.07] dark:bg-night/85">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-5">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-[10px] bg-pinedeep font-serif text-xl font-bold text-white dark:bg-sage dark:text-[#0b1511]">B</span>
            <div>
              <p className="font-serif text-[19px] font-bold leading-none tracking-tight">Blogger <span className="font-sans text-[13px] font-semibold text-fog">Admin</span></p>
              <p className="mt-1 font-mono text-[11px] text-fog">Token &amp; cost observability</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden max-w-[220px] truncate text-sm text-fog md:block">{user?.email}</span>
            <button type="button" onClick={load} disabled={loading} className="rounded-lg border border-line bg-white px-3 py-2 text-[13px] font-semibold shadow-card transition hover:bg-wash disabled:opacity-60 dark:border-white/10 dark:bg-panel dark:hover:bg-white/[0.07]">{loading ? "Refreshing…" : "↻ Refresh"}</button>
            <button type="button" onClick={signOut} className="rounded-lg bg-pine px-3 py-2 text-[13px] font-semibold text-white transition hover:bg-pinedeep dark:bg-sage dark:text-[#0b1511]">Sign out</button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-5 px-5 py-7 pb-16">
        <div>
          <h1 className="font-serif text-[30px] font-bold tracking-tight">Overview</h1>
          <p className="mt-1 text-[15px] text-fog">What generation costs, where tokens go, and how the pipeline spends its time.</p>
        </div>

        {loading && !data ? (
          <div aria-label="Loading usage" className="space-y-5">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{[0,1,2,3].map((i) => <div key={i} className="h-28 animate-pulse rounded-2xl border border-line bg-white dark:border-white/[0.06] dark:bg-white/[0.03]" />)}</div>
            <div className="h-44 animate-pulse rounded-2xl border border-line bg-white dark:border-white/[0.06] dark:bg-white/[0.03]" />
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-clay/25 bg-white p-8 text-center shadow-card dark:border-rose/25 dark:bg-panel">
            <p className="font-serif text-lg font-bold">Couldn't load usage</p>
            <p role="alert" className="mx-auto mt-1 max-w-md text-sm text-fog">{error}</p>
            <button type="button" onClick={() => void load()} className="mt-4 rounded-lg bg-pine px-4 py-2 text-sm font-semibold text-white transition hover:bg-pinedeep dark:bg-sage dark:text-[#0b1511]">Retry</button>
          </div>
        ) : !data || data.totals.llm_calls === 0 ? (
          <div className="rounded-2xl border border-dashed border-line bg-white p-10 text-center shadow-card dark:border-white/15 dark:bg-panel">
            <span aria-hidden="true" className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-wash font-serif text-xl font-bold text-pine dark:bg-sage/10 dark:text-sage">◔</span>
            <p className="mt-4 font-serif text-xl font-bold">No token usage yet</p>
            <p className="mx-auto mt-1 max-w-sm text-sm leading-relaxed text-fog">Generate a blog in the main app and cost, tokens, and latency will show up here automatically.</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Card accent label="Est. cost" value={fmtCost(data.totals.est_cost_usd)} sub={`${fmt(data.totals.llm_calls)} LLM calls tracked`} />
              <Card label="Total tokens" value={fmt(data.totals.total_tokens)} sub={`${fmt(data.totals.prompt_tokens)} in · ${fmt(data.totals.completion_tokens)} out`} />
              <Card label="Queries tracked" value={fmt(data.totals.queries_tracked)} sub={`${fmt(Math.round(data.totals.avg_tokens_per_query))} avg tokens / query`} />
              <Card label="Output tokens" value={fmt(data.totals.completion_tokens)} sub={`${fmt(data.totals.prompt_tokens)} input tokens`} />
            </div>

            <div className="grid gap-5 lg:grid-cols-2">
              <section className="rounded-2xl border border-line bg-white p-5 shadow-card dark:border-white/10 dark:bg-panel">
                <h3 className="font-serif text-lg font-bold tracking-tight">Tokens by pipeline stage</h3>
                <p className="mt-0.5 text-[13px] text-fog">Where each generation spends its budget.</p>
                <StageBars stages={data.by_stage} />
              </section>
              {data.by_day.length > 0 && (
                <section className="rounded-2xl border border-line bg-white p-5 shadow-card dark:border-white/10 dark:bg-panel">
                  <h3 className="font-serif text-lg font-bold tracking-tight">Daily trend <span className="font-sans text-sm font-normal text-fog">last 14 days</span></h3>
                  <p className="mt-0.5 text-[13px] text-fog">Tokens per day. Hover a bar for detail.</p>
                  <DayBars days={data.by_day} />
                </section>
              )}
            </div>

            {selected && <EntryDrilldown row={selected} token={token} onClose={() => setSelected(null)} />}

            <section className="overflow-hidden rounded-2xl border border-line bg-white shadow-card dark:border-white/10 dark:bg-panel">
              <div className="flex flex-wrap items-center justify-between gap-2 px-5 pt-5">
                <div>
                  <h3 className="font-serif text-lg font-bold tracking-tight">All queries</h3>
                  <p className="mt-0.5 text-[13px] text-fog">Select a row for the per-call breakdown. {rows.length} shown.</p>
                </div>
                {selected && <span className="rounded-full bg-wash px-2.5 py-1 font-mono text-[11px] text-fog dark:bg-white/[0.06]">Selected: #{selected.id}</span>}
              </div>
              <div className="overflow-x-auto p-4 pt-3">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead><tr className="border-b border-line font-mono text-[11px] uppercase tracking-wide text-fog dark:border-white/[0.07]">
                    <th className="py-2.5 pr-3 font-medium">Query</th><th className="py-2.5 pr-3 font-medium">User</th><th className="py-2.5 pr-3 font-medium">Calls</th>
                    <th className="py-2.5 pr-3 text-right font-medium">Input</th><th className="py-2.5 pr-3 text-right font-medium">Output</th>
                    <th className="py-2.5 pr-3 text-right font-medium">Total</th><th className="py-2.5 text-right font-medium">Est. cost</th>
                  </tr></thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id} onClick={() => setSelected(r)} aria-selected={selected?.id === r.id}
                        className={`cursor-pointer border-b border-line/60 transition last:border-0 hover:bg-wash/70 dark:border-white/[0.05] dark:hover:bg-white/[0.04] ${selected?.id === r.id ? "bg-wash dark:bg-sage/[0.08]" : ""}`}>
                        <td className="max-w-[240px] truncate py-3 pr-3 font-medium" title={r.query}>{r.query}</td>
                        <td className="max-w-[160px] truncate py-3 pr-3 text-fog" title={r.user_email ?? ""}>{r.user_email || "—"}</td>
                        <td className="py-3 pr-3 tabular-nums">{r.calls || "—"}</td>
                        <td className="py-3 pr-3 text-right tabular-nums">{fmt(r.prompt_tokens)}</td>
                        <td className="py-3 pr-3 text-right tabular-nums">{fmt(r.completion_tokens)}</td>
                        <td className="py-3 pr-3 text-right font-semibold tabular-nums">{fmt(r.total_tokens)}</td>
                        <td className="py-3 text-right tabular-nums text-fog">{r.total_tokens ? fmtCost(r.est_cost_usd) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="border-t border-line px-5 py-3 font-mono text-[11px] leading-relaxed text-fog dark:border-white/[0.07]">{data.pricing_note}</p>
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
    <div className="mt-4 space-y-4">
      {stages.map((s) => (
        <div key={s.stage}>
          <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
            <span className="font-semibold capitalize">{s.stage}</span>
            <span className="font-mono text-[12px] text-fog">{fmt(s.total_tokens)} tok · {s.calls} call{s.calls === 1 ? "" : "s"} · avg {fmtLatency(s.avg_latency_ms)}</span>
          </div>
          <div className="mt-1.5 h-2.5 overflow-hidden rounded-full bg-wash dark:bg-white/[0.07]" role="img" aria-label={`${s.stage}: ${s.total_tokens} tokens`}>
            <div className="h-full rounded-full bg-pine transition-[width] duration-500 dark:bg-sage" style={{ width: `${(s.total_tokens / max) * 100}%` }} />
          </div>
          <p className="mt-1 font-mono text-[11px] text-fog">{fmt(s.prompt_tokens)} in / {fmt(s.completion_tokens)} out</p>
        </div>
      ))}
    </div>
  );
}

function DayBars({ days }: { days: UsageSummary["by_day"] }) {
  const ordered = [...days].reverse();
  const max = Math.max(...ordered.map((d) => d.total_tokens), 1);
  return (
    <div className="mt-4 flex h-32 items-end gap-1.5">
      {ordered.map((d) => (
        <div key={d.day} className="group flex min-w-0 flex-1 flex-col items-center gap-1.5" title={`${d.day}: ${fmt(d.total_tokens)} tokens, ${d.queries} queries`}>
          <span className="font-mono text-[10px] text-fog opacity-0 transition group-hover:opacity-100">{fmt(d.total_tokens)}</span>
          <div className="w-full rounded-t-md bg-pine/85 transition group-hover:bg-pine dark:bg-sage/70 dark:group-hover:bg-sage" style={{ height: `${Math.max((d.total_tokens / max) * 100, 4)}%` }} />
          <span className="w-full truncate text-center font-mono text-[10px] text-fog">{d.day.slice(5)}</span>
        </div>
      ))}
    </div>
  );
}

function GatedApp() {
  const { user, token, ready } = useAuth();
  if (!ready) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-paper dark:bg-night">
        <span className="inline-flex h-11 w-11 items-center justify-center rounded-[12px] bg-pinedeep font-serif text-2xl font-bold text-white dark:bg-sage dark:text-[#0b1511]">B</span>
        <p className="text-sm text-fog">Opening Blogger Admin…</p>
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
