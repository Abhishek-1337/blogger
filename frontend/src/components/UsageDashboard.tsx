import { useEffect, useState } from "react";
import { fetchUsageOverview } from "../api";
import type { UsageSummary } from "../types";

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
    <div className="rounded-xl border border-line bg-white p-4 shadow-sm dark:border-white/10 dark:bg-panel">
      <p className="text-[13px] font-semibold text-fog">{label}</p>
      <p className="mt-1 font-serif text-2xl font-bold tracking-tight">{value}</p>
      {sub && <p className="mt-1 text-xs text-fog">{sub}</p>}
    </div>
  );
}

export default function UsageDashboard({
  apiUrl,
  token,
}: {
  apiUrl: string;
  token: string;
}) {
  const [data, setData] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchUsageOverview(apiUrl, token)
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError("");
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load usage.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [apiUrl, token]);

  if (loading) {
    return <p className="py-8 text-center text-sm text-fog">Loading usage…</p>;
  }
  if (error) {
    return (
      <div className="rounded-xl border border-line bg-white p-6 text-center shadow-sm dark:border-white/10 dark:bg-panel">
        <p className="text-sm text-fog">{error}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-3 rounded-lg border border-line px-3 py-1.5 text-[13px] font-semibold transition-colors hover:bg-wash/70 dark:border-white/10 dark:hover:bg-white/[0.06]"
        >
          Retry
        </button>
      </div>
    );
  }
  if (!data || data.totals.llm_calls === 0) {
    return (
      <div className="rounded-xl border border-line bg-white p-6 text-center shadow-sm dark:border-white/10 dark:bg-panel">
        <p className="font-serif text-lg font-bold">No token usage yet</p>
        <p className="mt-1 text-sm text-fog">
          Generate a blog and per-query token usage will show up here.
        </p>
      </div>
    );
  }

  const { totals, by_stage, by_day, recent } = data;
  const maxStage = Math.max(...by_stage.map((s) => s.total_tokens), 1);
  const maxDay = Math.max(...by_day.map((d) => d.total_tokens), 1);
  const days = [...by_day].reverse();
  const showUser = recent.some((r) => (r.user_email ?? "") !== "");

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <Card label="Total tokens" value={fmt(totals.total_tokens)} sub={`${fmt(totals.prompt_tokens)} in · ${fmt(totals.completion_tokens)} out`} />
        <Card label="Est. cost" value={fmtCost(totals.est_cost_usd)} sub="gpt-4o-mini rates" />
        <Card label="Queries tracked" value={fmt(totals.queries_tracked)} sub={`${fmt(totals.llm_calls)} LLM calls`} />
        <Card label="Avg tokens / query" value={fmt(Math.round(totals.avg_tokens_per_query))} />
        <Card label="Input tokens" value={fmt(totals.prompt_tokens)} />
        <Card label="Output tokens" value={fmt(totals.completion_tokens)} />
      </div>

      <section className="rounded-xl border border-line bg-white p-4 shadow-sm dark:border-white/10 dark:bg-panel">
        <h3 className="font-serif text-lg font-bold tracking-tight">
          Tokens by pipeline stage
        </h3>
        <div className="mt-3 space-y-3">
          {by_stage.map((s) => (
            <div key={s.stage}>
              <div className="flex items-baseline justify-between gap-2 text-sm">
                <span className="font-medium">{s.stage}</span>
                <span className="text-fog">
                  {fmt(s.total_tokens)} tok · {s.calls} call{s.calls === 1 ? "" : "s"} · avg{" "}
                  {fmt(s.avg_latency_ms)} ms
                </span>
              </div>
              <div
                className="mt-1 h-2 overflow-hidden rounded-full bg-wash dark:bg-white/[0.07]"
                role="img"
                aria-label={`${s.stage}: ${s.total_tokens} tokens`}
              >
                <div
                  className="h-full rounded-full bg-pine dark:bg-sage"
                  style={{ width: `${(s.total_tokens / maxStage) * 100}%` }}
                />
              </div>
              <p className="mt-0.5 text-xs text-fog">
                {fmt(s.prompt_tokens)} in / {fmt(s.completion_tokens)} out
              </p>
            </div>
          ))}
        </div>
      </section>

      {days.length > 0 && (
        <section className="rounded-xl border border-line bg-white p-4 shadow-sm dark:border-white/10 dark:bg-panel">
          <h3 className="font-serif text-lg font-bold tracking-tight">
            Daily trend <span className="text-sm font-normal text-fog">(last 14 days)</span>
          </h3>
          <div className="mt-3 flex h-28 items-end gap-1.5">
            {days.map((d) => (
              <div key={d.day} className="flex min-w-0 flex-1 flex-col items-center gap-1" title={`${d.day}: ${fmt(d.total_tokens)} tokens, ${d.queries} queries`}>
                <div
                  className="w-full rounded-t bg-pine/80 dark:bg-sage/80"
                  style={{ height: `${Math.max((d.total_tokens / maxDay) * 100, 3)}%` }}
                />
                <span className="w-full truncate text-center text-[10px] text-fog">
                  {d.day.slice(5)}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="overflow-hidden rounded-xl border border-line bg-white shadow-sm dark:border-white/10 dark:bg-panel">
        <h3 className="px-4 pt-4 font-serif text-lg font-bold tracking-tight">
          All queries
        </h3>
        <div className="overflow-x-auto p-4 pt-2">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[13px] text-fog dark:border-white/10">
                <th className="py-2 pr-3 font-medium">Query</th>
                {showUser && <th className="py-2 pr-3 font-medium">User</th>}
                <th className="py-2 pr-3 font-medium">Calls</th>
                <th className="py-2 pr-3 text-right font-medium">Input</th>
                <th className="py-2 pr-3 text-right font-medium">Output</th>
                <th className="py-2 pr-3 text-right font-medium">Total</th>
                <th className="py-2 text-right font-medium">Est. cost</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-line/60 last:border-0 dark:border-white/[0.06]"
                >
                  <td className="max-w-[220px] truncate py-2 pr-3" title={r.query}>
                    {r.query}
                  </td>
                  {showUser && (
                    <td className="max-w-[160px] truncate py-2 pr-3 text-fog" title={r.user_email ?? ""}>
                      {r.user_email || "—"}
                    </td>
                  )}
                  <td className="py-2 pr-3">{r.calls || "—"}</td>
                  <td className="py-2 pr-3 text-right">{fmt(r.prompt_tokens)}</td>
                  <td className="py-2 pr-3 text-right">{fmt(r.completion_tokens)}</td>
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
        <p className="border-t border-line px-4 py-2 text-xs text-fog dark:border-white/[0.07]">
          {data.pricing_note}
        </p>
      </section>
    </div>
  );
}
