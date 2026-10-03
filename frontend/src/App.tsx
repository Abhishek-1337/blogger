import { useCallback, useEffect, useRef, useState } from "react";
import { fetchBlog, fetchSearch, fetchSearches } from "./api";
import type { BlogResponse, SearchSummary } from "./types";
import Composer from "./components/Composer";
import Header from "./components/Header";
import History from "./components/History";
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
  const [history, setHistory] = useState<SearchSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyUnavailable, setHistoryUnavailable] = useState(false);
  const [selectingId, setSelectingId] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const resultsRef = useRef<HTMLElement>(null);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      setHistory(await fetchSearches(API_URL));
      setHistoryUnavailable(false);
    } catch {
      setHistory([]);
      setHistoryUnavailable(true);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    if (!busy) return;
    const timer = setInterval(() => {
      setActiveStage((i) => Math.min(i + 1, STAGES.length - 1));
    }, 15000);
    return () => clearInterval(timer);
  }, [busy]);

  useEffect(() => {
    if (result) resultsRef.current?.scrollIntoView({ block: "start" });
  }, [result]);

  async function generate() {
    const topic = query.trim();
    if (!topic) {
      setError("Enter a topic first.");
      return;
    }
    setError("");
    setResult(null);
    setSelectedId(null);
    setActiveStage(0);
    setBusy(true);
    try {
      const data = await fetchBlog(topic, API_URL);
      setResult(data);
      setSelectedId(data.id ?? null);
      void loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function openEntry(id: number) {
    setError("");
    setSelectingId(id);
    try {
      const data = await fetchSearch(API_URL, id);
      setResult(data);
      setSelectedId(data.id ?? id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSelectingId(null);
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
          <section ref={resultsRef} className="mt-8 scroll-mt-4">
            <Verdict data={result} />
            <ResearchBrief brief={result.research_brief} />
            <Outline sections={result.sections || []} />
          </section>
        )}

        {!busy && (
          <History
            entries={history}
            loading={historyLoading}
            unavailable={historyUnavailable}
            selectingId={selectingId}
            selectedId={selectedId}
            onSelect={openEntry}
          />
        )}
      </main>
    </div>
  );
}
