import Markdown from "react-markdown";
import type { BlogResponse } from "../types";

interface VerdictProps {
  data: BlogResponse;
}

export default function Verdict({ data }: VerdictProps) {
  const revs = data.outline_revisions ?? 0;
  const feedback = (data.outline_feedback || "").trim();
  return (
    <div className="mb-6 rounded-lg border border-pine/25 bg-[#edf2ef] px-4 py-3 text-sm shadow-sm dark:border-sage/20 dark:bg-[#121915] dark:bg-gradient-to-b dark:from-sage/[0.09] dark:to-transparent dark:shadow-[0_8px_28px_rgba(0,0,0,0.4)]">
      <strong className="text-pine dark:text-sage">
        {data.outline_approved ? "Approved" : "Draft"}
      </strong>
      <span>
        {" "}
        — outline after {revs} revision{revs === 1 ? "" : "s"}.
      </span>
      {feedback && (
        <div className="md-body mt-1.5">
          <Markdown>{feedback}</Markdown>
        </div>
      )}
    </div>
  );
}
