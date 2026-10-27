import { useMemo, useState } from "react";
import type { SearchSummary } from "../types";

interface HistoryProps {
  entries: SearchSummary[];
  loading: boolean;
  unavailable: boolean;
  disabled?: boolean;
  selectingId: number | null;
  selectedId: number | null;
  onSelect: (id: number) => void;
  onRetry: () => void;
}

function relativeTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const mins = Math.floor((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: d.getFullYear() !== new Date().getFullYear() ? "numeric" : undefined });
}

export default function History({ entries, loading, unavailable, disabled = false, selectingId, selectedId, onSelect, onRetry }: HistoryProps) {
  const [filter, setFilter] = useState("");
  const visible = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return q ? entries.filter((e) => e.query.toLowerCase().includes(q)) : entries;
  }, [entries, filter]);

  if (loading) {
    return (
      <ol aria-label="Loading previous searches" className="space-y-2 p-3">
        {[0, 1, 2, 3].map((i) => (
          <li key={i} className="animate-pulse rounded-xl border border-line bg-wash/50 p-3 dark:border-white/[0.06] dark:bg-white/[0.03]">
            <div className="h-4 w-3/4 rounded bg-line dark:bg-white/10" />
            <div className="mt-2 h-3 w-1/2 rounded bg-line dark:bg-white/[0.07]" />
          </li>
        ))}
      </ol>
    );
  }
  if (unavailable) {
    return (
      <div className="p-4">
        <p className="text-sm font-medium text-clay dark:text-rose">Couldn't load your library</p>
        <p className="mt-1 text-sm text-fog">Previous searches are unavailable — the database couldn't be reached.</p>
        <button type="button" onClick={onRetry} className="mt-3 rounded-lg border border-line px-3 py-1.5 text-[13px] font-semibold transition hover:bg-wash dark:border-white/10 dark:hover:bg-white/[0.08]">Retry</button>
      </div>
    );
  }
  if (entries.length === 0) {
    return (
      <div className="px-4 py-8 text-center">
        <span aria-hidden="true" className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-wash font-serif text-lg font-bold text-pine dark:bg-sage/10 dark:text-sage">✎</span>
        <p className="mt-3 text-sm font-semibold">No posts yet</p>
        <p className="mt-1 text-sm leading-relaxed text-fog">Generate your first blog and it will live here.</p>
      </div>
    );
  }

  const busy = disabled || selectingId !== null;
  return (
    <div>
      <div className="px-3 pt-3">
        <label htmlFor="history-filter" className="sr-only">Filter previous searches</label>
        <input id="history-filter" type="search" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter posts…"
          className="w-full rounded-lg border border-line bg-paper/60 px-3 py-2 text-sm outline-none transition placeholder:text-fog/60 focus:border-pine focus:ring-4 focus:ring-pine/10 dark:border-white/10 dark:bg-field dark:focus:border-sage/50 dark:focus:ring-sage/15" />
      </div>
      {visible.length === 0 ? (
        <p className="px-4 py-6 text-sm text-fog">No posts match “{filter}”.</p>
      ) : (
        <ol aria-label="Previous searches" className="space-y-1 p-2">
          {visible.map((entry) => {
            const selected = selectedId === entry.id;
            const selecting = selectingId === entry.id;
            return (
              <li key={entry.id}>
                <button type="button" onClick={() => onSelect(entry.id)} disabled={busy} aria-current={selected ? "true" : undefined} title={entry.query}
                  className={`flex w-full items-start justify-between gap-3 rounded-xl px-3 py-2.5 text-left transition disabled:cursor-wait ${selected ? "bg-wash ring-1 ring-pine/25 dark:bg-sage/[0.1] dark:ring-sage/30" : "hover:bg-wash/70 dark:hover:bg-white/[0.05]"}`}>
                  <span className="min-w-0 flex-1">
                    <span className={`block truncate text-[14px] font-semibold leading-snug ${selected ? "dark:text-white" : ""}`}>{selecting ? "Loading…" : entry.query}</span>
                    <span className="mt-1 block font-mono text-[11px] text-fog">{relativeTime(entry.created_at)}</span>
                  </span>
                  <span className={`mt-0.5 inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${entry.outline_approved ? "bg-[#e9f2ec] text-pine ring-pine/20 dark:bg-sage/[0.12] dark:text-sage dark:ring-sage/25" : "bg-wash text-fog ring-line dark:bg-white/[0.05] dark:ring-white/10"}`}>
                    <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${entry.outline_approved ? "bg-pine dark:bg-sage" : "bg-fog/50"}`} />
                    {entry.outline_approved ? "Approved" : "Draft"}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
