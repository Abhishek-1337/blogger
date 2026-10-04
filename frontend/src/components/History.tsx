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

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default function History({
  entries,
  loading,
  unavailable,
  disabled = false,
  selectingId,
  selectedId,
  onSelect,
  onRetry,
}: HistoryProps) {
  if (loading) {
    return (
      <ol aria-label="Loading previous searches" className="space-y-2 p-3">
        {[0, 1, 2, 3].map((i) => (
          <li
            key={i}
            className="animate-pulse rounded-lg border border-line bg-wash/50 p-3 dark:border-white/[0.06] dark:bg-white/[0.03]"
          >
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
        <p className="text-sm text-clay dark:text-rose">
          Previous searches are unavailable — the database couldn&apos;t be
          reached.
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-lg border border-line px-3 py-1.5 text-[13px] font-semibold text-ink transition-colors hover:bg-wash/70 dark:border-white/10 dark:bg-white/[0.04] dark:hover:bg-white/[0.08]"
        >
          Retry
        </button>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <p className="p-4 text-sm text-fog">
        No previous searches yet. Generated blogs will appear here.
      </p>
    );
  }

  const busy = disabled || selectingId !== null;

  return (
    <ol aria-label="Previous searches" className="space-y-1 p-2">
      {entries.map((entry) => {
        const selected = selectedId === entry.id;
        const selecting = selectingId === entry.id;
        return (
          <li key={entry.id}>
            <button
              type="button"
              onClick={() => onSelect(entry.id)}
              disabled={busy}
              aria-current={selected ? "true" : undefined}
              title={entry.query}
              className={`flex w-full items-start justify-between gap-3 rounded-lg px-3 py-2.5 text-left transition-colors disabled:cursor-wait ${
                selected
                  ? "bg-wash ring-1 ring-pine/20 dark:bg-sage/[0.1] dark:ring-1 dark:ring-sage/25 dark:shadow-[0_4px_20px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.06)]"
                  : "hover:bg-wash/60 dark:hover:bg-white/[0.05]"
              }`}
            >
              <span className="min-w-0 flex-1">
                <span
                  className={`block truncate text-[14px] font-semibold leading-snug ${
                    selected ? "dark:text-white" : ""
                  }`}
                >
                  {selecting ? "Loading…" : entry.query}
                </span>
                <span className="mt-1 block text-xs text-fog">
                  {formatDate(entry.created_at)}
                </span>
              </span>
              <span
                className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${
                  entry.outline_approved
                    ? "bg-[#edf2ef] text-pine ring-pine/20 dark:bg-sage/[0.12] dark:text-sage dark:ring-sage/25"
                    : "bg-wash text-fog ring-line/60 dark:bg-white/[0.05] dark:text-fog dark:ring-white/10"
                }`}
              >
                {entry.outline_approved ? "Approved" : "Draft"}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
