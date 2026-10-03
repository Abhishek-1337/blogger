import Markdown from "react-markdown";

interface ResearchBriefProps {
  brief: string;
}

export default function ResearchBrief({ brief }: ResearchBriefProps) {
  return (
    <article>
      <h2 className="mb-3 border-b border-line pb-2 font-serif text-[22px]">
        Research brief
      </h2>
      <div className="md-body text-[15px]">
        <Markdown>{brief || "(no brief returned)"}</Markdown>
      </div>
    </article>
  );
}
