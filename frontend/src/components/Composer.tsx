interface ComposerProps {
  query: string;
  busy: boolean;
  error: string;
  compact?: boolean;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
}

const EXAMPLES = [
  "Urban composting for apartment dwellers",
  "How remote teams run better standups",
  "The rise of electric cargo bikes",
  "Beginner's guide to sourdough starters",
];

export default function Composer({ query, busy, error, compact = false, onQueryChange, onSubmit }: ComposerProps) {
  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onSubmit();
  }
  const count = query.length;

  return (
    <section aria-label="New blog topic" className="rounded-2xl border border-line bg-white shadow-card dark:border-white/10 dark:bg-panel">
      <div className={compact ? "p-5 sm:p-6" : "p-5 sm:p-7"}>
        {!compact && (
          <>
            <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-ochre dark:text-ochrebright">New post</p>
            <h1 className="mt-2 max-w-xl font-serif text-[30px] font-bold leading-[1.12] tracking-tight text-balance sm:text-[36px]">
              What do you want to write about?
            </h1>
            <p className="mt-2.5 max-w-lg text-[15px] leading-relaxed text-fog">
              Give Blogger a topic. It researches the live web, builds an outline, gets an editor's pass — then drafts the post.
            </p>
          </>
        )}
        {compact && (
          <label htmlFor="query" className="mb-3 block font-serif text-[20px] font-bold tracking-tight">Write another post</label>
        )}

        <label htmlFor="query" className="sr-only">Blog topic</label>
        <textarea
          id="query" value={query} onChange={(e) => onQueryChange(e.target.value)} onKeyDown={onKeyDown}
          disabled={busy} maxLength={300} rows={2} autoComplete="off"
          placeholder="e.g. urban composting for apartment dwellers"
          className="mt-5 block min-h-[64px] w-full resize-none rounded-xl border border-line bg-paper/60 px-4 py-3.5 text-base leading-relaxed shadow-[inset_0_1px_2px_rgba(22,33,28,0.04)] outline-none transition placeholder:text-fog/60 focus:border-pine focus:bg-white focus:ring-4 focus:ring-pine/10 disabled:opacity-60 dark:border-white/10 dark:bg-field dark:focus:border-sage/60 dark:focus:bg-field dark:focus:ring-sage/15"
        />

        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="text-[13px] leading-relaxed text-fog">
              Research takes a minute or two.{" "}
              <span className="hidden md:inline">Press <kbd className="rounded border border-line bg-wash px-1.5 py-0.5 font-mono text-[11px] dark:border-white/10 dark:bg-white/[0.06]">⌘ Enter</kbd> to generate.</span>
            </p>
            <p className="mt-0.5 font-mono text-[11px] text-fog" aria-live="polite">{count}/300</p>
          </div>
          <button type="button" onClick={onSubmit} disabled={busy}
            className="inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-xl bg-pine px-6 py-3 text-base font-semibold text-white shadow-card transition hover:bg-pinedeep active:scale-[0.98] disabled:cursor-wait disabled:opacity-55 sm:w-auto dark:bg-sage dark:text-[#0b1511] dark:hover:bg-[#a6e0bb]">
            {busy ? "Generating…" : (<>Generate <span aria-hidden="true">→</span></>)}
          </button>
        </div>

        {!compact && !busy && (
          <div className="mt-6 border-t border-line pt-4 dark:border-white/[0.07]">
            <p className="text-[13px] font-medium text-fog">Try one of these</p>
            <div className="mt-2.5 flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button key={ex} type="button" onClick={() => onQueryChange(ex)}
                  className="max-w-full rounded-full border border-line bg-white px-3 py-1.5 text-left text-[13px] font-medium transition hover:border-pine/40 hover:bg-wash hover:text-pinedeep dark:border-white/10 dark:bg-white/[0.04] dark:hover:border-sage/40 dark:hover:text-sage">
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && (
          <p role="alert" className="mt-4 flex items-start gap-2 rounded-xl border border-clay/25 bg-[#fbf0ec] px-4 py-3 text-sm text-clay dark:border-rose/25 dark:bg-rose/[0.08] dark:text-rose">
            <span aria-hidden="true" className="mt-0.5 font-bold">!</span><span>{error}</span>
          </p>
        )}
      </div>
    </section>
  );
}
