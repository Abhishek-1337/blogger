export default function Header() {
  return (
    <header className="bg-pine text-white shadow-[inset_0_-1px_0_rgba(0,0,0,0.2)]">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-3">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-white font-serif text-xl font-bold text-pine ring-1 ring-black/10">
            B
          </span>
          <div>
            <p className="font-serif text-[22px] font-bold leading-none tracking-tight">
              Blogger
            </p>
            <p className="mt-1 text-xs text-white/75">
              Research-backed blog outlines
            </p>
          </div>
        </div>
        <a
          href="/docs"
          className="rounded-md px-3 py-1.5 text-[13px] font-semibold text-white/80 underline decoration-ochre decoration-2 underline-offset-4 transition-colors hover:bg-white/10 hover:text-white"
        >
          API docs
        </a>
      </div>
      <div className="h-[3px] bg-ochre" aria-hidden="true" />
    </header>
  );
}
