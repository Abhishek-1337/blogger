import ThemeToggle from "./ThemeToggle";
import type { User } from "../types";

interface HeaderProps {
  onMenu?: () => void;
  user?: User | null;
  onSignOut?: () => void;
}

export default function Header({ onMenu, user, onSignOut }: HeaderProps) {
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
          <a
            href="/docs"
            className="rounded-md px-3 py-1.5 text-[13px] font-semibold text-white/80 underline decoration-ochre decoration-2 underline-offset-4 transition-colors hover:bg-white/10 hover:text-white"
          >
            API docs
          </a>
          {user && (
            <div className="flex items-center gap-2 pl-1">
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
              <span className="hidden max-w-32 truncate text-[13px] font-semibold text-white/85 sm:inline">
                {user.name || user.email}
              </span>
              <button
                type="button"
                onClick={onSignOut}
                className="rounded-md px-2 py-1.5 text-[13px] font-semibold text-white/80 transition-colors hover:bg-white/10 hover:text-white"
              >
                Sign out
              </button>
            </div>
          )}
          <ThemeToggle />
        </div>
      </div>
      <div className="h-[3px] bg-ochre" aria-hidden="true" />
    </header>
  );
}
