import type { OutlineSection } from "../types";

export default function Outline({ sections }: { sections: OutlineSection[] }) {
  return (
    <article className="mt-6 rounded-2xl border border-line bg-white p-5 shadow-card sm:p-7 dark:border-white/10 dark:bg-panel">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-4 dark:border-white/[0.07]">
        <div>
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-ochre dark:text-ochrebright">Step 02 — Structure</p>
          <h2 className="mt-1 font-serif text-[24px] font-bold tracking-tight">Outline</h2>
        </div>
        {sections.length > 0 && <span className="rounded-full bg-wash px-2.5 py-1 font-mono text-[11px] text-fog dark:bg-white/[0.06]">{sections.length} section{sections.length === 1 ? "" : "s"}</span>}
      </div>

      {sections.length === 0 ? (
        <p className="py-6 text-sm text-fog">No outline sections returned for this post.</p>
      ) : (
        <ol className="relative mt-2">
          <span aria-hidden="true" className="absolute bottom-4 left-[15px] top-4 w-px bg-line dark:bg-white/10" />
          {sections.map((section, i) => (
            <li key={i} className="relative flex gap-4 py-4 sm:gap-5">
              <span aria-hidden="true" className="relative z-10 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-pine font-mono text-[12px] font-semibold text-white ring-4 ring-white dark:bg-sage dark:text-[#16241b] dark:ring-panel">
                {i + 1}
              </span>
              <div className="min-w-0 pt-0.5">
                <h3 className="font-serif text-[19px] font-bold leading-snug tracking-tight">{section.title || "Untitled section"}</h3>
                {(section.bullets || []).length > 0 && (
                  <ul className="mt-2 space-y-1.5">
                    {section.bullets.map((b, j) => (
                      <li key={j} className="flex gap-2 text-[14.5px] leading-relaxed text-ink/80 dark:text-[#cdd2c4]">
                        <span aria-hidden="true" className="mt-[9px] h-1 w-4 shrink-0 rounded-full bg-ochre/70 dark:bg-ochrebright/70" />{b}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}
