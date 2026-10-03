import Markdown from "react-markdown";
import type { BlogResponse } from "../types";

interface VerdictProps {
  data: BlogResponse;
}

export default function Verdict({ data }: VerdictProps) {
  const revs = data.outline_revisions ?? 0;
  const feedback = (data.outline_feedback || "").trim();
  return (
    <div className="mb-6 rounded-lg border border-pine/25 bg-[#edf2ef] px-4 py-3 text-sm">
      <strong className="text-pine">
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
