import type { OutlineSection } from "../types";

interface OutlineProps {
  sections: OutlineSection[];
}

export default function Outline({ sections }: OutlineProps) {
  return (
    <article className="mt-8">
      <h2 className="mb-3 border-b border-line pb-2 font-serif text-[22px]">
        Outline{" "}
        {sections.length > 0 && (
          <span className="text-sm font-normal text-fog">
            · {sections.length} sections
          </span>
        )}
      </h2>
      <ol>
        {sections.map((section, i) => (
          <li
            key={i}
            className="relative border-b border-line py-4 pl-14 pr-0"
          >
            <span
              aria-hidden="true"
              className="absolute left-0 top-3.5 font-serif text-[26px] font-bold leading-none text-ochre dark:text-[#d9a44a] dark:drop-shadow-[0_0_12px_rgba(217,164,74,0.25)]"
            >
              {String(i + 1).padStart(2, "0")}
            </span>
            <h3 className="mb-2 font-serif text-[19px] font-bold tracking-tight">
              {section.title || "Untitled"}
            </h3>
            <ul className="list-disc pl-5 text-[14.5px] text-[#33352f] dark:text-[#cdd2c4]">
              {(section.bullets || []).map((b, j) => (
                <li key={j} className="mb-1">
                  {b}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </article>
  );
}
