interface ProgressPillProps {
  stages: string[];
  active: number;
}

export default function ProgressPill({ stages, active }: ProgressPillProps) {
  const pct = Math.round(((active + 1) / stages.length) * 100);
  return (
    <section aria-label="Generation progress" className="mt-5 rounded-2xl border border-line bg-white p-5 shadow-card animate-rise sm:p-6 dark:border-white/10 dark:bg-panel">
      <div className="flex items-center justify-between gap-3">
        <p role="status" className="flex items-center gap-2.5 text-sm font-semibold">
          <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full bg-pine animate-pulse-dot dark:bg-sage" />
          {stages[active]}…
        </p>
        <span className="font-mono text-xs text-fog">{pct}%</span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-wash dark:bg-white/[0.07]" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Generation progress">
        <div className="h-full rounded-full bg-pine transition-[width] duration-700 ease-out dark:bg-sage" style={{ width: `${pct}%` }} />
      </div>
      <ol className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stages.map((s, i) => {
          const done = i < active;
          const current = i === active;
          return (
            <li key={s} aria-current={current ? "step" : undefined} className="flex items-start gap-2.5">
              <span aria-hidden="true" className={`mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full font-mono text-[11px] font-semibold ring-1 ${
                done ? "bg-pine text-white ring-pine dark:bg-sage dark:text-[#0b1511] dark:ring-sage"
                : current ? "bg-white text-pine ring-pine dark:bg-sage/15 dark:text-sage dark:ring-sage/50"
                : "bg-wash text-fog ring-line dark:bg-white/[0.05] dark:ring-white/10"}`}>
                {done ? "✓" : i + 1}
              </span>
              <span className={`text-[13px] leading-snug ${current ? "font-semibold" : done ? "font-medium" : "text-fog"}`}>{s}</span>
            </li>
          );
        })}
      </ol>
      <p className="mt-4 text-[13px] text-fog">Hang tight — the brief, outline and editor's verdict will appear below when ready.</p>
    </section>
  );
}
