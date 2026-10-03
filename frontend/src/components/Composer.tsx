interface ComposerProps {
  query: string;
  busy: boolean;
  error: string;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
}

export default function Composer({
  query,
  busy,
  error,
  onQueryChange,
  onSubmit,
}: ComposerProps) {
  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") onSubmit();
  }

  return (
    <section
      aria-label="New blog topic"
      className="rounded-xl border border-line bg-wash/60 p-5 sm:p-6"
    >
      <label
        htmlFor="query"
        className="mb-3 block font-serif text-[22px] font-bold tracking-tight"
      >
        What should the blog post be about?
      </label>
      <div className="flex flex-col gap-2.5 sm:flex-row">
        <input
          id="query"
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={busy}
          maxLength={300}
          autoComplete="off"
          placeholder="e.g. urban composting for apartment dwellers"
          className="flex-1 rounded-lg border border-line bg-white px-3.5 py-2.5 text-base shadow-sm outline-none focus:border-pine focus:ring-2 focus:ring-pine/40 disabled:opacity-60"
        />
        <button
          type="button"
          onClick={onSubmit}
          disabled={busy}
          className="rounded-lg bg-pine px-6 py-2.5 text-base font-semibold text-white transition-colors hover:bg-pinedeep disabled:cursor-wait disabled:opacity-55"
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
  );
}
