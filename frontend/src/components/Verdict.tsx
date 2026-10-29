import Markdown from "react-markdown";
import type { BlogResponse } from "../types";

export default function Verdict({ data }: { data: BlogResponse }) {
  const revs = data.outline_revisions ?? 0;
  const feedback = (data.outline_feedback || "").trim();
  const approved = data.outline_approved;
  return (
    <div className={`rounded-2xl border p-5 shadow-card sm:p-6 ${approved ? "border-pine/25 bg-[#eaf3ed] dark:border-sage/25 dark:bg-sage/[0.08]" : "border-ochre/30 bg-[#fbf4e4] dark:border-ochrebright/25 dark:bg-ochrebright/[0.07]"}`}>
      <div className="flex flex-wrap items-center gap-2.5">
        <span aria-hidden="true" className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-sm font-bold text-white ${approved ? "bg-pine dark:bg-sage dark:text-[#16241b]" : "bg-ochre"}`}>{approved ? "✓" : "◐"}</span>
        <p className="font-serif text-lg font-bold tracking-tight">{approved ? "Editor approved" : "Editor draft"}</p>
        <span className="rounded-full bg-white/70 px-2.5 py-1 font-mono text-[11px] font-medium text-fog ring-1 ring-black/5 dark:bg-white/[0.06] dark:ring-white/10">
          {revs} revision{revs === 1 ? "" : "s"}
        </span>
      </div>
      {feedback ? (
        <div className="md-body mt-3 text-[15px]"><Markdown>{feedback}</Markdown></div>
      ) : (
        <p className="mt-2 text-sm text-fog">{approved ? "The outline passed review and is ready to read below." : "The outline is shown below as a working draft."}</p>
      )}
    </div>
  );
}
