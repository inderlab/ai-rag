import { useState, type FormEvent } from "react";
import { errorMessage, getTranscript, type TranscriptResponse } from "../api/client";

export default function TranscriptPage() {
  const [url, setUrl] = useState("");
  const [data, setData] = useState<TranscriptResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setData(null);
    try {
      setData(await getTranscript(url));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-semibold">Transcript preview</h1>

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          className="flex-1 rounded-md border px-3 py-2"
          required
        />
        <button disabled={loading} className="rounded-md bg-slate-900 px-4 py-2 text-white disabled:opacity-50">
          {loading ? "Loading…" : "Get transcript"}
        </button>
      </form>

      {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {data && (
        <div className="space-y-3">
          <div className="aspect-video overflow-hidden rounded-lg bg-black">
            <iframe
              className="h-full w-full"
              src={`https://www.youtube.com/embed/${data.video_id}`}
              title="YouTube player"
              allowFullScreen
            />
          </div>
          <p className="text-sm text-slate-500">
            {data.segment_count} segments · showing first {data.segments.length}
          </p>
          <ul className="divide-y rounded-lg border bg-white">
            {data.segments.map((s) => (
              <li key={s.start} className="flex gap-3 px-3 py-2 text-sm">
                <span className="w-16 shrink-0 font-mono text-blue-600">{s.timestamp}</span>
                <span>{s.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
