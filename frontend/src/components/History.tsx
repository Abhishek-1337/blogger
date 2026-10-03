import type { SearchSummary } from "../types";

interface HistoryProps {
  entries: SearchSummary[];
  loading: boolean;
  unavailable: boolean;
  selectingId: number | null;
  selectedId: number | null;
  onSelect: (id: number) => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default function History({
  entries,
  loading,
  unavailable,
  selectingId,
  selectedId,
  onSelect,
}: HistoryProps) {
  return (
    <section aria-label="Previous searches" className="mt-8">
      <h2 className="mb-3 border-b border-line pb-2 font-serif text-[22px] tracking-tight">
        Previous searches
      </h2>
      {loading ? (
        <p className="text-sm text-fog">Loading history…</p>
      ) : unavailable ? (
        <p className="text-sm text-clay">
          Previous searches are unavailable — the database couldn&apos;t be
          reached.
        </p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-fog">No previous searches yet.</p>
      ) : (
        <ol>
          {entries.map((entry) => (
            <li key={entry.id} className="border-b border-line last:border-0">
              <button
                type="button"
                onClick={() => onSelect(entry.id)}
                disabled={selectingId !== null}
                className={`flex w-full items-baseline justify-between gap-4 py-2.5 text-left transition-colors hover:bg-wash/60 disabled:cursor-wait ${
                  selectedId === entry.id ? "bg-wash/60" : ""
                }`}
              >
                <span className="min-w-0">
                  <span className="block truncate text-[15px] font-semibold">
                    {selectingId === entry.id ? "Loading…" : entry.query}
                  </span>
                  <span className="mt-0.5 block text-[13px] text-fog">
                    {formatDate(entry.created_at)}
                  </span>
                </span>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    entry.outline_approved
                      ? "bg-[#edf2ef] text-pine"
                      : "bg-wash text-fog"
                  }`}
                >
                  {entry.outline_approved ? "Approved" : "Draft"}
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
