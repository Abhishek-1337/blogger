import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { fetchMe, loginWithGoogle } from "./api";
import type { User } from "./types";

const TOKEN_KEY = "blogger_token";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (opts: {
            client_id: string;
            callback: (resp: { credential?: string }) => void;
            auto_select?: boolean;
          }) => void;
          renderButton: (
            el: HTMLElement,
            opts: { theme?: string; size?: string; width?: number }
          ) => void;
        };
      };
    };
  }
}

interface AuthState {
  user: User | null;
  token: string | null;
  ready: boolean;
  error: string;
  signOut: () => void;
  handleCredential: (idToken: string) => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

function loadGis(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const el = document.querySelector(
      'script[src="https://accounts.google.com/gsi/client"]'
    );
    if (el) {
      el.addEventListener("load", () => resolve(), { once: true });
      el.addEventListener("error", () => reject(new Error("load")), {
        once: true,
      });
      return;
    }
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () =>
      reject(new Error("Could not load Google sign-in. Check connection."));
    document.head.appendChild(s);
  });
}

export function AuthProvider({
  apiUrl,
  children,
}: {
  apiUrl: string;
  children: ReactNode;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY)
  );
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const tokenRef = useRef(token);
  tokenRef.current = token;

  useEffect(() => {
    async function restore() {
      const saved = localStorage.getItem(TOKEN_KEY);
      if (!saved) {
        setReady(true);
        return;
      }
      try {
        setUser(await fetchMe(apiUrl, saved));
        setToken(saved);
      } catch {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
      } finally {
        setReady(true);
      }
    }
    void restore();
  }, [apiUrl]);

  const handleCredential = useCallback(
    async (idToken: string) => {
      setError("");
      try {
        const res = await loginWithGoogle(apiUrl, idToken);
        localStorage.setItem(TOKEN_KEY, res.token);
        setToken(res.token);
        setUser(res.user);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Sign-in failed.");
      }
    },
    [apiUrl]
  );

  const signOut = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, token, ready, error, signOut, handleCredential }),
    [user, token, ready, error, signOut, handleCredential]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function GoogleSignInButton() {
  const { handleCredential, error } = useAuth();
  const divRef = useRef<HTMLDivElement>(null);
  const [gisError, setGisError] = useState("");
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "";

  useEffect(() => {
    if (!clientId) {
      setGisError("Google sign-in is not configured (missing client ID).");
      return;
    }
    let cancelled = false;
    loadGis()
      .then(() => {
        if (cancelled || !divRef.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (resp) => {
            if (resp.credential) void handleCredential(resp.credential);
          },
        });
        window.google.accounts.id.renderButton(divRef.current, {
          theme: "outline",
          size: "large",
        });
      })
      .catch(() =>
        setGisError("Could not load Google sign-in. Check connection.")
      );
    return () => {
      cancelled = true;
    };
  }, [clientId, handleCredential]);

  return (
    <div>
      <div ref={divRef} className="flex justify-center" />
      {(gisError || error) && (
        <p className="mt-3 text-center text-sm text-red-700 dark:text-red-300">
          {gisError || error}
        </p>
      )}
    </div>
  );
}
