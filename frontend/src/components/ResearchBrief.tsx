import Markdown from "react-markdown";

export default function ResearchBrief({ brief }: { brief: string }) {
  const words = brief ? brief.trim().split(/\s+/).filter(Boolean).length : 0;
  return (
    <article className="mt-6 rounded-2xl border border-line bg-white p-5 shadow-card sm:p-7 dark:border-white/10 dark:bg-panel">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-4 dark:border-white/[0.07]">
        <div>
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-ochre dark:text-ochrebright">Step 01 — Research</p>
          <h2 className="mt-1 font-serif text-[24px] font-bold tracking-tight">Research brief</h2>
        </div>
        {words > 0 && <span className="rounded-full bg-wash px-2.5 py-1 font-mono text-[11px] text-fog dark:bg-white/[0.06]">{words} words</span>}
      </div>
      <div className="md-body mt-4 max-w-[68ch] text-[15.5px]">
        <Markdown>{brief || "(no brief returned)"}</Markdown>
      </div>
    </article>
  );
}
