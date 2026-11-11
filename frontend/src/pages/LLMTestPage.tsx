import { useState, type FormEvent } from "react";
import { errorMessage, testLLM, type LLMTestResponse } from "../api/client";

const PROVIDERS = [
  { value: "", label: "Default (.env)" },
  { value: "openai", label: "ChatGPT (OpenAI)" },
  { value: "claude", label: "Claude (Anthropic)" },
];

export default function LLMTestPage() {
  const [prompt, setPrompt] = useState("RAG kya hota hai? 2 line mein batao.");
  const [provider, setProvider] = useState("");
  const [result, setResult] = useState<LLMTestResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await testLLM(prompt, provider || undefined));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-semibold">LLM connection test</h1>

      <form onSubmit={onSubmit} className="space-y-3">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          className="w-full rounded-md border px-3 py-2"
        />
        <div className="flex gap-2">
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="rounded-md border px-3 py-2"
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <button disabled={loading} className="rounded-md bg-slate-900 px-4 py-2 text-white disabled:opacity-50">
            {loading ? "Asking…" : "Send"}
          </button>
        </div>
      </form>

      {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {result && (
        <div className="space-y-2 rounded-lg border bg-white p-4">
          <p className="whitespace-pre-wrap">{result.answer}</p>
          <p className="text-xs text-slate-500">
            answered by {result.provider} · {result.model} · {result.latency_ms} ms
          </p>
        </div>
      )}
    </section>
  );
}
