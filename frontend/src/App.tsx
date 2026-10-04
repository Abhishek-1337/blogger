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
  const [sidebarOpen, setSidebarOpen] = useState(false);
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
    if (!sidebarOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setSidebarOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarOpen]);

  useEffect(() => {
    if (result) resultsRef.current?.scrollIntoView({ block: "start" });
  }, [result]);

  function newSearch() {
    setQuery("");
    setResult(null);
    setSelectedId(null);
    setError("");
    setSidebarOpen(false);
  }

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
      setSidebarOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSelectingId(null);
    }
  }

  const sidebarBody = (
    <History
      entries={history}
      loading={historyLoading}
      unavailable={historyUnavailable}
      disabled={busy}
      selectingId={selectingId}
      selectedId={selectedId}
      onSelect={openEntry}
      onRetry={loadHistory}
    />
  );

  return (
    <div className="min-h-screen bg-white font-sans text-ink antialiased dark:bg-night dark:bg-[radial-gradient(1100px_480px_at_50%_-10%,rgba(143,208,174,0.09),transparent),radial-gradient(800px_380px_at_88%_0%,rgba(189,134,54,0.07),transparent)]">
      <Header onMenu={() => setSidebarOpen(true)} />

      <div className="mx-auto flex max-w-6xl items-start gap-8 px-5 pb-16 pt-7">
        {/* Desktop sidebar */}
        <aside
          aria-label="Previous searches sidebar"
          className="sticky top-6 hidden max-h-[calc(100vh-3rem)] w-80 shrink-0 overflow-y-auto rounded-xl border border-line bg-white shadow-sm dark:border-white/10 dark:bg-panel dark:shadow-[0_16px_48px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.05)] lg:block"
        >
          <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-3 dark:border-white/[0.07]">
            <h2 className="font-serif text-lg font-bold tracking-tight">
              Previous searches
            </h2>
            <button
              type="button"
              onClick={newSearch}
              className="rounded-lg bg-pine px-3 py-1.5 text-[13px] font-semibold text-white transition-colors hover:bg-pinedeep dark:bg-sage dark:text-[#0b1511] dark:shadow-[0_4px_16px_rgba(143,208,174,0.25)] dark:hover:bg-[#a6e0bb]"
            >
              + New
            </button>
          </div>
          {sidebarBody}
        </aside>

        <main className="min-w-0 flex-1">
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
        </main>
      </div>

      {/* Mobile drawer */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-[2px] dark:bg-black/65"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Previous searches"
            className="absolute inset-y-0 left-0 flex w-80 max-w-[85vw] flex-col bg-white shadow-xl dark:border-r dark:border-white/10 dark:bg-[#101411] dark:shadow-[24px_0_64px_rgba(0,0,0,0.6)]"
          >
            <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-3 dark:border-white/[0.07]">
              <h2 className="font-serif text-lg font-bold tracking-tight">
                Previous searches
              </h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={newSearch}
                  className="rounded-lg bg-pine px-3 py-1.5 text-[13px] font-semibold text-white transition-colors hover:bg-pinedeep dark:bg-sage dark:text-[#0b1511] dark:hover:bg-[#a6e0bb]"
                >
                  + New
                </button>
                <button
                  type="button"
                  onClick={() => setSidebarOpen(false)}
                  aria-label="Close previous searches"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-fog transition-colors hover:bg-wash/70 dark:hover:bg-white/[0.07]"
                >
                  ✕
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto">{sidebarBody}</div>
          </aside>
        </div>
      )}
    </div>
  );
}
