import type { UsageBlock, UsageCall } from "../types";

function fmt(n: number): string {
  return n.toLocaleString();
}

interface StripSummary {
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  est_cost_usd: number;
  by_stage: {
    stage: string;
    calls: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    avg_latency_ms?: number;
  }[];
}

function fromCalls(calls: UsageCall[]): StripSummary {
  const by_stage = new Map<string, StripSummary["by_stage"][number]>();
  for (const c of calls) {
    const row = by_stage.get(c.stage) ?? {
      stage: c.stage,
      calls: 0,
      prompt_tokens: 0,
      completion_tokens: 0,
      total_tokens: 0,
      avg_latency_ms: 0,
    };
    row.calls += 1;
    row.prompt_tokens += c.prompt_tokens;
    row.completion_tokens += c.completion_tokens;
    row.total_tokens += c.total_tokens;
    row.avg_latency_ms = (row.avg_latency_ms ?? 0) + c.latency_ms;
    by_stage.set(c.stage, row);
  }
  for (const row of by_stage.values()) {
    if (row.calls > 0) row.avg_latency_ms = Math.round((row.avg_latency_ms ?? 0) / row.calls);
  }
  const prompt = calls.reduce((a, c) => a + c.prompt_tokens, 0);
  const completion = calls.reduce((a, c) => a + c.completion_tokens, 0);
  return {
    calls: calls.length,
    prompt_tokens: prompt,
    completion_tokens: completion,
    total_tokens: prompt + completion,
    est_cost_usd: (prompt / 1_000_000) * 0.15 + (completion / 1_000_000) * 0.6,
    by_stage: [...by_stage.values()].sort((a, b) => b.total_tokens - a.total_tokens),
  };
}

export default function QueryUsage({
  block,
  calls,
  loading,
}: {
  block?: UsageBlock | null;
  calls?: UsageCall[] | null;
  loading?: boolean;
}) {
  if (loading) {
    return <p className="mb-6 text-sm text-fog">Loading token usage…</p>;
  }
  const summary: StripSummary | null = block
    ? { ...block }
    : calls && calls.length > 0
      ? fromCalls(calls)
      : null;
  if (!summary || summary.calls === 0) return null;

  return (
    <div className="mb-6 rounded-lg border border-line bg-white px-4 py-3 text-sm shadow-sm dark:border-white/10 dark:bg-panel">
      <details>
        <summary className="cursor-pointer list-none">
          <span className="font-semibold">Token usage</span>
          <span className="text-fog">
            {" "}
            — {fmt(summary.total_tokens)} tokens ({fmt(summary.prompt_tokens)} in /{" "}
            {fmt(summary.completion_tokens)} out) · {summary.calls} LLM call
            {summary.calls === 1 ? "" : "s"} · ~${summary.est_cost_usd.toFixed(4)} est.
          </span>
        </summary>
        <table className="mt-2 w-full text-left text-[13px]">
          <thead>
            <tr className="border-b border-line text-fog dark:border-white/10">
              <th className="py-1 pr-3 font-medium">Stage</th>
              <th className="py-1 pr-3 text-right font-medium">Calls</th>
              <th className="py-1 pr-3 text-right font-medium">Input</th>
              <th className="py-1 pr-3 text-right font-medium">Output</th>
              <th className="py-1 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {summary.by_stage.map((s) => (
              <tr
                key={s.stage}
                className="border-b border-line/60 last:border-0 dark:border-white/[0.06]"
              >
                <td className="py-1 pr-3">{s.stage}</td>
                <td className="py-1 pr-3 text-right">{s.calls}</td>
                <td className="py-1 pr-3 text-right">{fmt(s.prompt_tokens)}</td>
                <td className="py-1 pr-3 text-right">{fmt(s.completion_tokens)}</td>
                <td className="py-1 text-right font-semibold">{fmt(s.total_tokens)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
