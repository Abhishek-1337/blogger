import { useCallback, useEffect, useRef, useState } from "react";
import { fetchBlog, fetchSearch, fetchSearches } from "./api";
import { AuthProvider, GoogleSignInButton, useAuth } from "./auth";
import type { BlogResponse, SearchSummary } from "./types";
import Composer from "./components/Composer";
import Header from "./components/Header";
import History from "./components/History";
import Outline from "./components/Outline";
import ProgressPill from "./components/ProgressPill";
import ResearchBrief from "./components/ResearchBrief";
import Verdict from "./components/Verdict";

const API_URL = import.meta.env.VITE_API_URL ?? "";

const STAGES = ["Searching the web", "Writing research brief", "Drafting outline", "Editor review"];
const STAGE_KEYS = ["research", "summarize", "outline", "verify_outline"];

function toMarkdown(data: BlogResponse): string {
  const parts = [`# ${data.query}`, ""];
  if (data.research_brief) parts.push("## Research brief", "", data.research_brief, "");
  if (data.sections?.length) {
    parts.push("## Outline", "");
    data.sections.forEach((s, i) => {
      parts.push(`### ${i + 1}. ${s.title}`);
      (s.bullets || []).forEach((b) => parts.push(`- ${b}`));
      parts.push("");
    });
  }
  return parts.join("\n").trim() + "\n";
}

function SignInScreen() {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-pinedeep p-10 text-white lg:flex xl:p-14">
        <div className="flex items-center gap-2.5">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-[10px] bg-white font-serif text-xl font-bold text-pinedeep">B</span>
          <span className="font-serif text-[22px] font-bold tracking-tight">Blogger</span>
        </div>
        <div className="max-w-md">
          <h1 className="font-serif text-[42px] font-bold leading-[1.08] tracking-tight">From a topic to a post worth publishing.</h1>
          <p className="mt-4 text-[16px] leading-relaxed text-white/75">Blogger researches the live web, shapes an outline, and puts an editor's eye over it — before a single draft line is written.</p>
          <ol className="mt-8 space-y-3">
            {STAGES.map((s, i) => (
              <li key={s} className="flex items-center gap-3 text-[15px]">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-white/10 font-mono text-[12px] font-semibold ring-1 ring-white/20">{i + 1}</span>
                {s}
              </li>
            ))}
          </ol>
        </div>
        <p className="font-mono text-[12px] text-white/50">Research-backed · Editor-reviewed · Saved to your library</p>
        <span aria-hidden="true" className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full border-[28px] border-white/[0.05]" />
      </div>

      <div className="flex items-center justify-center bg-paper px-5 py-10 dark:bg-night">
        <div className="w-full max-w-sm animate-rise">
          <div className="mb-6 flex items-center gap-2.5 lg:hidden">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-[10px] bg-pinedeep font-serif text-xl font-bold text-white dark:bg-sage dark:text-[#0b1511]">B</span>
            <span className="font-serif text-[22px] font-bold tracking-tight">Blogger</span>
          </div>
          <h2 className="font-serif text-[30px] font-bold leading-tight tracking-tight">Welcome back</h2>
          <p className="mt-2 text-[15px] leading-relaxed text-fog">Sign in to write, research, and reopen everything in your library. Your posts stay private to you.</p>
          <div className="mt-7 rounded-2xl border border-line bg-white p-6 shadow-card dark:border-white/10 dark:bg-panel">
            <GoogleSignInButton />
            <p className="mt-4 text-center text-[13px] leading-relaxed text-fog">Continue with your Google account.<br />No password to remember.</p>
          </div>
          <p className="mt-5 text-center font-mono text-[11px] text-fog">Takes about 10 seconds · Free to start</p>
        </div>
      </div>
    </div>
  );
}

function HowItWorks() {
  const steps = [
    { n: "01", title: "Research", body: "Live web searches across several angles of your topic." },
    { n: "02", title: "Brief", body: "Findings distilled into a sourced research brief." },
    { n: "03", title: "Outline", body: "A structured, section-by-section plan for the post." },
    { n: "04", title: "Review", body: "An editor model critiques and revises before drafting." },
  ];
  return (
    <section aria-label="How Blogger works" className="mt-6 rounded-2xl border border-line bg-white p-5 shadow-card sm:p-6 dark:border-white/10 dark:bg-panel">
      <h2 className="font-serif text-lg font-bold tracking-tight">How it works</h2>
      <div className="mt-4 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {steps.map((s) => (
          <div key={s.n}>
            <p className="font-mono text-[12px] font-semibold text-ochre dark:text-ochrebright">{s.n}</p>
            <h3 className="mt-1.5 text-[15px] font-semibold">{s.title}</h3>
            <p className="mt-1 text-sm leading-relaxed text-fog">{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Workspace() {
  const { token, signOut } = useAuth();
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
  const [copied, setCopied] = useState(false);
  const resultsRef = useRef<HTMLElement>(null);

  const loadHistory = useCallback(async () => {
    if (!token) return;
    setHistoryLoading(true);
    try {
      setHistory(await fetchSearches(API_URL, token));
      setHistoryUnavailable(false);
    } catch {
      setHistory([]);
      setHistoryUnavailable(true);
    } finally {
      setHistoryLoading(false);
    }
  }, [token]);

  useEffect(() => { void loadHistory(); }, [loadHistory]);

  useEffect(() => {
    if (!sidebarOpen) return;
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") setSidebarOpen(false); }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarOpen]);

  useEffect(() => { if (result) resultsRef.current?.scrollIntoView({ block: "start" }); }, [result]);
  useEffect(() => { if (!copied) return; const t = setTimeout(() => setCopied(false), 2000); return () => clearTimeout(t); }, [copied]);

  function newSearch() {
    setQuery(""); setResult(null); setSelectedId(null); setError(""); setSidebarOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function generate() {
    const topic = query.trim();
    if (!topic) { setError("Enter a topic first — anything you want to write about."); return; }
    if (!token) { setError("Please sign in again."); return; }
    setError(""); setResult(null); setSelectedId(null); setActiveStage(0); setBusy(true);
    try {
      const data = await fetchBlog(topic, API_URL, token, (stage) => {
        const idx = STAGE_KEYS.indexOf(stage);
        if (idx >= 0) setActiveStage(idx);
      });
      setResult(data); setSelectedId(data.id ?? null); void loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally { setBusy(false); }
  }

  async function openEntry(id: number) {
    if (!token) return;
    setError(""); setSelectingId(id);
    try {
      const data = await fetchSearch(API_URL, id, token);
      setResult(data); setSelectedId(data.id ?? id); setQuery(data.query); setSidebarOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally { setSelectingId(null); }
  }

  async function copyResult() {
    if (!result) return;
    try { await navigator.clipboard.writeText(toMarkdown(result)); setCopied(true); } catch { setError("Couldn't copy — your browser blocked clipboard access."); }
  }
  function downloadResult() {
    if (!result) return;
    const slug = result.query.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "blog-post";
    const url = URL.createObjectURL(new Blob([toMarkdown(result)], { type: "text/markdown" }));
    const a = document.createElement("a"); a.href = url; a.download = `${slug}.md`; a.click();
    URL.revokeObjectURL(url);
  }

  const sidebarBody = (
    <History entries={history} loading={historyLoading} unavailable={historyUnavailable} disabled={busy} selectingId={selectingId} selectedId={selectedId} onSelect={openEntry} onRetry={loadHistory} />
  );

  return (
    <Shell onMenu={() => setSidebarOpen(true)} onSignOut={signOut} newSearch={newSearch} sidebarBody={sidebarBody} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} count={history.length}>
      <Composer query={query} busy={busy} error={error} compact={!!result} onQueryChange={setQuery} onSubmit={generate} />

      {busy && <ProgressPill stages={STAGES} active={activeStage} />}
      {!busy && !result && <HowItWorks />}

      {result && (
        <section ref={resultsRef} className="mt-8 animate-rise scroll-mt-20">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="min-w-0">
              <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-ochre dark:text-ochrebright">Your post</p>
              <h2 className="mt-1 truncate font-serif text-[28px] font-bold leading-tight tracking-tight" title={result.query}>{result.query}</h2>
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={copyResult} className="rounded-lg border border-line bg-white px-3.5 py-2 text-sm font-semibold shadow-card transition hover:bg-wash dark:border-white/10 dark:bg-panel dark:hover:bg-white/[0.07]">{copied ? "Copied ✓" : "Copy markdown"}</button>
              <button type="button" onClick={downloadResult} className="rounded-lg bg-pine px-3.5 py-2 text-sm font-semibold text-white shadow-card transition hover:bg-pinedeep dark:bg-sage dark:text-[#0b1511] dark:hover:bg-[#a6e0bb]">Download .md</button>
            </div>
          </div>
          <div className="mt-4"><Verdict data={result} /></div>
          <ResearchBrief brief={result.research_brief} />
          <Outline sections={result.sections || []} />
        </section>
      )}
    </Shell>
  );
}

function Shell({ children, onMenu, onSignOut, newSearch, sidebarBody, sidebarOpen, setSidebarOpen, count }: {
  children: React.ReactNode; onMenu: () => void; onSignOut: () => void; newSearch: () => void;
  sidebarBody: React.ReactNode; sidebarOpen: boolean; setSidebarOpen: (v: boolean) => void; count: number;
}) {
  const { user } = useAuth();
  const sidebarHead = (
    <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-3.5 dark:border-white/[0.07]">
      <h2 className="font-serif text-[17px] font-bold tracking-tight">Library{count > 0 && <span className="ml-2 rounded-full bg-wash px-2 py-0.5 align-middle font-mono text-[11px] font-medium text-fog dark:bg-white/[0.07]">{count}</span>}</h2>
      <button type="button" onClick={newSearch} className="rounded-lg bg-pine px-3 py-1.5 text-[13px] font-semibold text-white transition hover:bg-pinedeep dark:bg-sage dark:text-[#0b1511] dark:hover:bg-[#a6e0bb]">+ New post</button>
    </div>
  );
  return (
    <div className="min-h-screen bg-paper font-sans text-ink antialiased dark:bg-night">
      <Header onMenu={onMenu} user={user} onSignOut={onSignOut} />
      <div className="mx-auto flex max-w-6xl items-start gap-6 px-5 pb-20 pt-6">
        <aside aria-label="Previous searches sidebar" className="sticky top-24 hidden max-h-[calc(100vh-7rem)] w-80 shrink-0 overflow-y-auto rounded-2xl border border-line bg-white shadow-card lg:block dark:border-white/10 dark:bg-panel">
          {sidebarHead}
          {sidebarBody}
        </aside>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px] dark:bg-black/65" onClick={() => setSidebarOpen(false)} aria-hidden="true" />
          <aside role="dialog" aria-modal="true" aria-label="Previous searches" className="absolute inset-y-0 left-0 flex w-80 max-w-[85vw] flex-col bg-white shadow-lift dark:border-r dark:border-white/10 dark:bg-[#101411]">
            <div className="flex items-center gap-2">
              <div className="flex-1">{sidebarHead}</div>
              <button type="button" onClick={() => setSidebarOpen(false)} aria-label="Close previous searches" className="mr-3 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-fog transition hover:bg-wash dark:hover:bg-white/[0.07]">✕</button>
            </div>
            <div className="flex-1 overflow-y-auto">{sidebarBody}</div>
          </aside>
        </div>
      )}
    </div>
  );
}

function GatedApp() {
  const { user, ready } = useAuth();
  if (!ready) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-paper dark:bg-night">
        <span className="inline-flex h-11 w-11 items-center justify-center rounded-[12px] bg-pinedeep font-serif text-2xl font-bold text-white dark:bg-sage dark:text-[#0b1511]">B</span>
        <p className="text-sm text-fog">Opening Blogger…</p>
      </div>
    );
  }
  if (!user) return <SignInScreen />;
  return <Workspace />;
}

export default function App() {
  return (
    <AuthProvider apiUrl={API_URL}>
      <GatedApp />
    </AuthProvider>
  );
}
