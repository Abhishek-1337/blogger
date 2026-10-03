import { useEffect, useState } from "react";
import Markdown from "react-markdown";

const STAGES = [
  "Searching the web",
  "Writing research brief",
  "Drafting outline",
  "Editor review",
];

function Verdict({ data }) {
  const approved = data.outline_approved;
  const revs = data.outline_revisions ?? 0;
  const feedback = (data.outline_feedback || "").trim();
  return (
    <div className="mb-6 rounded-lg border border-line bg-wash px-4 py-3 text-sm">
      <strong className="text-pine">{approved ? "Approved" : "Draft"}</strong>
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

export default function App() {
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    if (!busy) return;
    const timer = setInterval(() => {
      setActiveStage((i) => Math.min(i + 1, STAGES.length - 1));
    }, 15000);
    return () => clearInterval(timer);
  }, [busy]);

  async function generate() {
    const topic = query.trim();
    if (!topic) {
      setError("Enter a topic first.");
      return;
    }
    setError("");
    setResult(null);
    setActiveStage(0);
    setBusy(true);
    try {
      const res = await fetch("/blog", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: topic }),
      });
      if (!res.ok) {
        let detail = `Request failed (${res.status}).`;
        try {
          const body = await res.json();
          if (body && body.detail) {
            detail =
              typeof body.detail === "string"
                ? body.detail
                : body.detail.map((d) => d.msg).join("; ");
          }
        } catch {
          /* keep default */
        }
        throw new Error(detail);
      }
      setResult(await res.json());
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter") generate();
  }

  return (
    <div className="min-h-screen bg-white font-sans text-ink">
      <header className="border-b-[3px] border-double border-ink">
        <div className="mx-auto flex max-w-3xl items-baseline justify-between gap-4 px-5 pb-3.5 pt-5">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-pine font-serif text-2xl font-bold text-white">
              B
            </span>
            <div>
              <p className="font-serif text-[26px] font-bold leading-tight">Blogger</p>
              <p className="text-[13px] text-fog">Research-backed blog outlines</p>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 pb-16 pt-7">
        <section aria-label="New blog topic">
          <label htmlFor="query" className="mb-3 block font-serif text-[22px] font-bold">
            What should the blog post be about?
          </label>
          <div className="flex flex-col gap-2.5 sm:flex-row">
            <input
              id="query"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={busy}
              maxLength={300}
              autoComplete="off"
              placeholder="e.g. urban composting for apartment dwellers"
              className="flex-1 rounded-lg border border-line px-3.5 py-2.5 text-base outline-none focus:border-pine focus:ring-2 focus:ring-pine/40 disabled:opacity-60"
            />
            <button
              type="button"
              onClick={generate}
              disabled={busy}
              className="rounded-lg bg-pine px-6 py-2.5 text-base font-semibold text-white hover:brightness-90 disabled:cursor-wait disabled:opacity-55"
            >
              {busy ? "Generating…" : "Generate"}
            </button>
          </div>
          <p className="mt-2 text-[13px] text-fog">
            Research takes a minute or two — the brief and outline appear below as they
            complete.
          </p>
          {error && (
            <p
              role="alert"
              className="mt-3 rounded-r-lg border-l-4 border-clay bg-[#f9ece8] px-3.5 py-2.5 text-sm text-clay"
            >
              {error}
            </p>
          )}
        </section>

        {busy && (
          <section aria-label="Generation progress" className="mt-7">
            <p
              role="status"
              className="inline-flex items-center gap-2.5 rounded-full border border-pine bg-white px-3.5 py-1.5 text-[13px] font-semibold text-pine"
            >
              <span
                aria-hidden="true"
                className="inline-block h-4 w-4 rounded-full border-2 border-line border-t-pine motion-safe:animate-spin"
              />
              {STAGES[activeStage]}…
            </p>
          </section>
        )}

        {result && (
          <section className="mt-8">
            <Verdict data={result} />

            <article>
              <h2 className="mb-3 border-b border-line pb-2 font-serif text-[22px]">
                Research brief
              </h2>
              <div className="md-body text-[15px]">
                <Markdown>{result.research_brief || "(no brief returned)"}</Markdown>
              </div>
            </article>

            <article className="mt-8">
              <h2 className="mb-3 border-b border-line pb-2 font-serif text-[22px]">
                Outline{" "}
                {result.sections?.length > 0 && (
                  <span className="text-sm font-normal text-fog">
                    · {result.sections.length} sections
                  </span>
                )}
              </h2>
              <ol>
                {(result.sections || []).map((section, i) => (
                  <li
                    key={i}
                    className="border-b border-line py-4 pl-14 pr-0"
                    style={{ position: "relative" }}
                  >
                    <span
                      aria-hidden="true"
                      className="absolute left-0 top-4 font-serif text-xl font-bold text-pine"
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <h3 className="mb-2 text-[17px] font-semibold">
                      {section.title || "Untitled"}
                    </h3>
                    <ul className="list-disc pl-5 text-[14.5px] text-[#33352f]">
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
          </section>
        )}

      </main>
    </div>
  );
}
