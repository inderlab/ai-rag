import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import {
  getAuthConfig,
  getMe,
  getToken,
  login as apiLogin,
  register as apiRegister,
  setToken,
  type User,
} from "../api/client";

type AuthState = {
  user: User | null;
  authRequired: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [authRequired, setAuthRequired] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const config = getAuthConfig()
      .then((c) => setAuthRequired(c.auth_required))
      .catch(() => setAuthRequired(false));
    const me = getToken()
      ? getMe()
          .then(setUser)
          .catch(() => setToken(null))
      : Promise.resolve();
    Promise.all([config, me]).finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (name: string, email: string, password: string) => {
    const res = await apiRegister(name, email, password);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, authRequired, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
