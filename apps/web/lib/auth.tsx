"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthApi, sessionExpiredEvent } from "./api-client";

interface AuthState {
  user: { id: string; email: string } | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<{ id: string; email: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    AuthApi.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
    const onExpired = () => {
      setUser(null);
      const ret = window.location.pathname;
      router.push(`/login?returnTo=${encodeURIComponent(ret)}&expired=1`);
    };
    window.addEventListener(sessionExpiredEvent, onExpired);
    return () => window.removeEventListener(sessionExpiredEvent, onExpired);
  }, [router]);

  const login = useCallback(async (email: string, password: string) => {
    const u = await AuthApi.login(email, password);
    setUser(u);
  }, []);
  const logout = useCallback(async () => {
    await AuthApi.logout().catch(() => undefined);
    setUser(null);
    router.push("/login");
  }, [router]);

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside provider");
  return v;
}
