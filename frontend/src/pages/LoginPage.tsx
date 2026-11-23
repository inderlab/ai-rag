import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "login") await login(email, password);
      else await register(name, email, password);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto max-w-sm space-y-6">
      <div className="flex rounded-lg border bg-white p-1 text-sm">
        {(["login", "register"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`flex-1 rounded-md py-1.5 ${mode === m ? "bg-slate-900 text-white" : "text-slate-600"}`}
          >
            {m === "login" ? "Log in" : "Create account"}
          </button>
        ))}
      </div>
      <form onSubmit={onSubmit} className="space-y-3 rounded-lg border bg-white p-4">
        {mode === "register" && (
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name"
            className="w-full rounded-md border px-3 py-2"
            required
          />
        )}
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          className="w-full rounded-md border px-3 py-2"
          autoComplete="email"
          required
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={mode === "register" ? "Password (8+ characters)" : "Password"}
          className="w-full rounded-md border px-3 py-2"
          autoComplete={mode === "register" ? "new-password" : "current-password"}
          minLength={mode === "register" ? 8 : 1}
          required
        />
        {error && <p className="rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        <button disabled={busy} className="w-full rounded-md bg-slate-900 py-2 text-white disabled:opacity-50">
          {busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
        </button>
      </form>
      <p className="text-center text-xs text-slate-500">
        Your uploads are private to your account. YouTube videos are shared.
      </p>
    </section>
  );
}
