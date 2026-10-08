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
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [menuOpen]);
  return (
    <header className="bg-pine text-white shadow-[inset_0_-1px_0_rgba(0,0,0,0.2)] dark:bg-[#0e1a15] dark:shadow-[0_1px_0_rgba(255,255,255,0.07),0_12px_32px_rgba(0,0,0,0.45)]">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3">
        <div className="flex items-center gap-3">
          {onMenu && (
            <button
              type="button"
              onClick={onMenu}
              aria-label="Open previous searches"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md text-white/85 transition-colors hover:bg-white/10 hover:text-white lg:hidden"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <line x1="3" y1="5" x2="17" y2="5" />
                <line x1="3" y1="10" x2="17" y2="10" />
                <line x1="3" y1="15" x2="17" y2="15" />
              </svg>
            </button>
          )}
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-white font-serif text-xl font-bold text-pine ring-1 ring-black/10 dark:bg-sage dark:text-[#0b1511] dark:shadow-[0_0_20px_rgba(143,208,174,0.35)] dark:ring-sage/40">
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
        <div className="flex items-center gap-1">
          <ThemeToggle />
          {user && (
            <div ref={menuRef} className="relative">
              <button
                type="button"
                onClick={() => setMenuOpen((v) => !v)}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                aria-label="Account menu"
                className="ml-1 flex items-center rounded-full outline-none transition-shadow hover:ring-2 hover:ring-white/40 focus-visible:ring-2 focus-visible:ring-white/60"
              >
                {user.picture ? (
                  <img
                    src={user.picture}
                    alt=""
                    referrerPolicy="no-referrer"
                    className="h-8 w-8 rounded-full ring-1 ring-white/30"
                  />
                ) : (
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-white/15 text-sm font-bold">
                    {(user.name || user.email || "?").charAt(0).toUpperCase()}
                  </span>
                )}
              </button>
              {menuOpen && (
                <div
                  role="menu"
                  className="absolute right-0 z-50 mt-2 w-60 overflow-hidden rounded-xl border border-line bg-white text-ink shadow-lg dark:border-white/10 dark:bg-panel dark:shadow-[0_16px_48px_rgba(0,0,0,0.5)]"
                >
                  <div className="border-b border-line px-4 py-3 dark:border-white/[0.07]">
                    <p className="truncate text-sm font-semibold">
                      {user.name || "Signed in"}
                    </p>
                    {user.name && (
                      <p className="mt-0.5 truncate text-xs text-fog">
                        {user.email}
                      </p>
                    )}
                  </div>
                  <div className="p-1.5">
                    <a
                      href="/docs"
                      role="menuitem"
                      onClick={() => setMenuOpen(false)}
                      className="block rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-wash dark:hover:bg-white/[0.06]"
                    >
                      API docs
                    </a>
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        setMenuOpen(false);
                        onSignOut?.();
                      }}
                      className="block w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors hover:bg-wash dark:hover:bg-white/[0.06]"
                    >
                      Sign out
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="h-[3px] bg-ochre" aria-hidden="true" />
    </header>
  );
}
