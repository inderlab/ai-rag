import { NavLink, Route, Routes } from "react-router-dom";
import HealthBadge from "./components/HealthBadge";
import LibraryPage from "./pages/LibraryPage";
import LLMTestPage from "./pages/LLMTestPage";
import TranscriptPage from "./pages/TranscriptPage";
import VideoPage from "./pages/VideoPage";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-200"}`;

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
          <HealthBadge />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Routes>
          <Route path="/" element={<LibraryPage />} />
          <Route path="/videos/:id" element={<VideoPage />} />
          <Route path="/transcript" element={<TranscriptPage />} />
          <Route path="/llm" element={<LLMTestPage />} />
        </Routes>
      </main>
    </div>
  );
}
