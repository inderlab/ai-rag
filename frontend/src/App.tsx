import type { ReactNode } from "react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import HealthBadge from "./components/HealthBadge";
import { useAuth } from "./hooks/useAuth";
import LibraryPage from "./pages/LibraryPage";
import LLMTestPage from "./pages/LLMTestPage";
import LoginPage from "./pages/LoginPage";
import TranscriptPage from "./pages/TranscriptPage";
import VideoPage from "./pages/VideoPage";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-200"}`;

function Guard({ children }: { children: ReactNode }) {
  const { user, authRequired, loading } = useAuth();
  if (loading) return <div className="h-40 animate-pulse rounded-lg bg-slate-100" />;
  if (authRequired && !user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function UserMenu() {
  const { user, logout } = useAuth();
  if (!user)
    return (
      <Link to="/login" className="text-sm text-slate-600 hover:underline">
        Log in
      </Link>
    );
  return (
    <span className="flex items-center gap-2 text-sm">
      <span className="text-slate-600">{user.name}</span>
      <button onClick={logout} className="text-slate-400 hover:text-slate-700">
        Log out
      </button>
    </span>
  );
}

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <span className="text-lg font-semibold">VidMind AI</span>
          <nav className="flex gap-1">
            <NavLink to="/" end className={linkClass}>
              Library
            </NavLink>
            <NavLink to="/transcript" className={linkClass}>
              Transcript
            </NavLink>
            <NavLink to="/llm" className={linkClass}>
              LLM test
            </NavLink>
          </nav>
          <div className="flex items-center gap-4">
            <HealthBadge />
            <UserMenu />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <Guard>
                <LibraryPage />
              </Guard>
            }
          />
          <Route
            path="/videos/:id"
            element={
              <Guard>
                <VideoPage />
              </Guard>
            }
          />
          <Route path="/transcript" element={<TranscriptPage />} />
          <Route path="/llm" element={<LLMTestPage />} />
        </Routes>
      </main>
    </div>
  );
}
