import { useEffect, useRef, useState } from "react";
import ThemeToggle from "./ThemeToggle";
import type { User } from "../types";

interface HeaderProps {
  onMenu?: () => void;
  user?: User | null;
  onSignOut?: () => void;
}

export default function Header({ onMenu, user, onSignOut }: HeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuOpen(false);
    }
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [menuOpen]);

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-white/85 backdrop-blur-md dark:border-white/[0.07] dark:bg-night/85">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5">
        <div className="flex items-center gap-3">
          {onMenu && (
            <button type="button" onClick={onMenu} aria-label="Open previous searches"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-fog transition-colors hover:bg-wash hover:text-ink lg:hidden dark:hover:bg-white/[0.07] dark:hover:text-white">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><line x1="3" y1="5" x2="17" y2="5" /><line x1="3" y1="10" x2="17" y2="10" /><line x1="3" y1="15" x2="17" y2="15" /></svg>
            </button>
          )}
          <a href="#" onClick={(e) => e.preventDefault()} className="flex items-center gap-2.5" aria-label="Blogger home">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-[10px] bg-pinedeep font-serif text-xl font-bold text-white shadow-card dark:bg-sage dark:text-[#0b1511]">B</span>
            <span className="font-serif text-[22px] font-bold leading-none tracking-tight">Blogger</span>
          </a>
          <span className="ml-1 hidden rounded-full border border-line px-2.5 py-1 font-mono text-[11px] font-medium text-fog sm:inline dark:border-white/10">Research → Draft</span>
        </div>

        <div className="flex items-center gap-1.5">
          <ThemeToggle />
          {user && (
            <div ref={menuRef} className="relative">
              <button type="button" onClick={() => setMenuOpen((v) => !v)} aria-haspopup="menu" aria-expanded={menuOpen} aria-label="Account menu"
                className="ml-1 flex items-center gap-2 rounded-full py-1 pl-1 pr-2 outline-none transition-colors hover:bg-wash dark:hover:bg-white/[0.07]">
                {user.picture ? (
                  <img src={user.picture} alt="" referrerPolicy="no-referrer" className="h-8 w-8 rounded-full ring-1 ring-line dark:ring-white/20" />
                ) : (
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-pine text-sm font-bold text-white dark:bg-sage dark:text-[#0b1511]">{(user.name || user.email || "?").charAt(0).toUpperCase()}</span>
                )}
                <span className="hidden max-w-[140px] truncate text-sm font-medium md:block">{user.name?.split(" ")[0] || "Account"}</span>
                <svg width="14" height="14" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true" className="text-fog"><path d="M5 8l5 5 5-5" /></svg>
              </button>
              {menuOpen && (
                <div role="menu" className="absolute right-0 z-50 mt-2 w-64 overflow-hidden rounded-xl border border-line bg-white shadow-lift dark:border-white/10 dark:bg-panel">
                  <div className="border-b border-line px-4 py-3 dark:border-white/[0.07]">
                    <p className="truncate text-sm font-semibold">{user.name || "Signed in"}</p>
                    {user.name && <p className="mt-0.5 truncate text-xs text-fog">{user.email}</p>}
                  </div>
                  <div className="p-1.5">
                    <a href="/docs" role="menuitem" onClick={() => setMenuOpen(false)} className="block rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-wash dark:hover:bg-white/[0.06]">API docs</a>
                    <button type="button" role="menuitem" onClick={() => { setMenuOpen(false); onSignOut?.(); }} className="block w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-clay transition-colors hover:bg-[#f9ece8] dark:text-rose dark:hover:bg-rose/[0.08]">Sign out</button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
