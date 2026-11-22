import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  addVideo,
  deleteVideo,
  errorMessage,
  listVideos,
  retryVideo,
  searchLibrary,
  type SearchHit,
  type Video,
} from "../api/client";
import ChatPanel from "../components/ChatPanel";
import StatusBadge from "../components/StatusBadge";

const BUSY = new Set(["pending", "processing", "indexing"]);

export default function LibraryPage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const navigate = useNavigate();

  const refresh = useCallback(() => {
    listVideos()
      .then(setVideos)
      .catch((err) => setError(errorMessage(err)));
  }, []);

  useEffect(refresh, [refresh]);

  useEffect(() => {
    if (!videos.some((v) => BUSY.has(v.status))) return;
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, [videos, refresh]);

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    setAdding(true);
    setError("");
    try {
      await addVideo(url);
      setUrl("");
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setAdding(false);
    }
  }

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    if (query.trim().length < 2) return;
    try {
      setHits(await searchLibrary(query));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function onDelete(v: Video) {
    if (!confirm(`Delete "${v.title ?? v.youtube_id}"?`)) return;
    await deleteVideo(v.id);
    refresh();
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Your videos</h1>
          <p className="text-sm text-slate-500">Paste a YouTube link. It gets a transcript, chunks, vectors and a summary.</p>
        </div>

        <form onSubmit={onAdd} className="flex gap-2">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            className="flex-1 rounded-md border px-3 py-2"
            required
          />
          <button disabled={adding} className="rounded-md bg-slate-900 px-4 py-2 text-white disabled:opacity-50">
            {adding ? "Adding…" : "Add video"}
          </button>
        </form>
        {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        <form onSubmit={onSearch} className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search all videos by meaning…"
            className="flex-1 rounded-md border px-3 py-2 text-sm"
          />
          <button className="rounded-md border px-4 text-sm">Search</button>
        </form>
        {hits && (
          <ul className="divide-y rounded-lg border bg-white text-sm">
            {hits.length === 0 && <li className="p-3 text-slate-500">No matches.</li>}
            {hits.map((h) => (
              <li key={`${h.video_id}-${h.start}`}>
                <button
                  type="button"
                  onClick={() => navigate(`/videos/${h.video_id}?t=${Math.floor(h.start)}`)}
                  className="w-full p-3 text-left hover:bg-slate-50"
                >
                  <span className="font-mono text-blue-700">{h.timestamp}</span>{" "}
                  <span className="font-medium">{h.title}</span>
                  <span className="ml-2 text-xs text-slate-400">score {h.score.toFixed(2)}</span>
                  <p className="mt-1 line-clamp-2 text-slate-600">{h.text}</p>
                </button>
              </li>
            ))}
          </ul>
        )}

        <ul className="grid gap-4 sm:grid-cols-2">
          {videos.length === 0 && <li className="text-sm text-slate-500">No videos yet.</li>}
          {videos.map((v) => (
            <li key={v.id} className="overflow-hidden rounded-lg border bg-white">
              <Link to={`/videos/${v.id}`}>
                <img src={v.thumbnail_url} alt="" className="aspect-video w-full object-cover" />
              </Link>
              <div className="space-y-1 p-3">
                <div className="flex items-start justify-between gap-2">
                  <Link to={`/videos/${v.id}`} className="line-clamp-2 font-medium hover:underline">
                    {v.title ?? v.youtube_id}
                  </Link>
                  <StatusBadge status={v.status} />
                </div>
                <p className="text-xs text-slate-500">
                  {v.channel ?? "…"} · {v.duration ?? "--:--"} · {v.chunk_count} chunks
                </p>
                {v.error && <p className="text-xs text-red-700">{v.error}</p>}
                <div className="flex gap-3 pt-1 text-xs">
                  {v.status === "failed" && (
                    <button onClick={() => retryVideo(v.id).then(refresh)} className="text-blue-700">
                      Retry
                    </button>
                  )}
                  <button onClick={() => onDelete(v)} className="text-slate-500 hover:text-red-700">
                    Delete
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="h-[70vh] lg:sticky lg:top-6">
        <ChatPanel
          videoId={null}
          onSeek={(s, vid) => vid && navigate(`/videos/${vid}?t=${Math.floor(s)}`)}
          suggestions={["Kaunsi video jailbreak ke baare mein hai?", "Which video explains fine-tuning?"]}
        />
      </div>
    </section>
  );
}
