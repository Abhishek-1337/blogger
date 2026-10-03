import { useEffect, useState } from "react";
import { fetchBlog } from "./api";
import type { BlogResponse } from "./types";
import Composer from "./components/Composer";
import Header from "./components/Header";
import Outline from "./components/Outline";
import ProgressPill from "./components/ProgressPill";
import ResearchBrief from "./components/ResearchBrief";
import Verdict from "./components/Verdict";

const API_URL = import.meta.env.VITE_API_URL ?? "";

const STAGES = [
  "Searching the web",
  "Writing research brief",
  "Drafting outline",
  "Editor review",
];

export default function App() {
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<BlogResponse | null>(null);
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
      setResult(await fetchBlog(topic, API_URL));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-white font-sans text-ink antialiased">
      <Header />

      <main className="mx-auto max-w-5xl px-5 pb-16 pt-7">
        <Composer
          query={query}
          busy={busy}
          error={error}
          onQueryChange={setQuery}
          onSubmit={generate}
        />

        {busy && <ProgressPill stage={STAGES[activeStage]} />}

        {result && (
          <section className="mt-8">
            <Verdict data={result} />
            <ResearchBrief brief={result.research_brief} />
            <Outline sections={result.sections || []} />
          </section>
        )}
      </main>
    </div>
  );
}
