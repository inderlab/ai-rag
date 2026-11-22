import { useEffect, useState } from "react";
import { errorMessage, generateInsights, getInsights, type Insights } from "../api/client";

type Props = { videoId: number; onSeek: (seconds: number) => void };

export default function InsightsPanel({ videoId, onSeek }: Props) {
  const [data, setData] = useState<Insights | null>(null);
  const [missing, setMissing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    setMissing(false);
    getInsights(videoId)
      .then(setData)
      .catch(() => setMissing(true));
  }, [videoId]);

  async function generate() {
    setBusy(true);
    setError("");
    try {
      setData(await generateInsights(videoId));
      setMissing(false);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (missing && !data) {
    return (
      <div className="rounded-lg border bg-white p-4 text-sm">
        <p className="text-slate-600">No summary or chapters yet.</p>
        <button
          onClick={generate}
          disabled={busy}
          className="mt-2 rounded-md bg-slate-900 px-3 py-1.5 text-white disabled:opacity-50"
        >
          {busy ? "Generating…" : "Generate summary & chapters"}
        </button>
        {error && <p className="mt-2 text-red-700">{error}</p>}
      </div>
    );
  }
  if (!data) return <div className="h-24 animate-pulse rounded-lg bg-slate-100" />;

  return (
    <div className="space-y-4 rounded-lg border bg-white p-4 text-sm">
      <div>
        <h2 className="text-base font-semibold">{data.title}</h2>
        <p className="mt-1 text-slate-700">{data.summary}</p>
        <div className="mt-2 flex flex-wrap gap-1">
          {data.tags.map((t) => (
            <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              #{t}
            </span>
          ))}
        </div>
      </div>
      <div>
        <h3 className="mb-1 font-medium">Chapters</h3>
        <ol className="space-y-0.5">
          {data.chapters.map((c) => (
            <li key={c.start}>
              <button
                type="button"
                onClick={() => onSeek(c.seconds)}
                className="flex w-full gap-3 rounded px-1 py-0.5 text-left hover:bg-slate-50"
              >
                <span className="w-14 shrink-0 font-mono text-blue-700">{c.start}</span>
                <span>{c.title}</span>
              </button>
            </li>
          ))}
        </ol>
      </div>
      {data.key_points.length > 0 && (
        <div>
          <h3 className="mb-1 font-medium">Key points</h3>
          <ul className="ml-5 list-disc space-y-0.5 text-slate-700">
            {data.key_points.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-[11px] text-slate-400">
        {data.provider} · {data.model}
      </p>
    </div>
  );
}
