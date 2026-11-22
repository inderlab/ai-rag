import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { errorMessage, getVideo, type Video } from "../api/client";
import ChatPanel from "../components/ChatPanel";
import InsightsPanel from "../components/InsightsPanel";
import StatusBadge from "../components/StatusBadge";
import YouTubePlayer, { type PlayerHandle } from "../components/YouTubePlayer";

const BUSY = new Set(["pending", "processing", "indexing"]);

export default function VideoPage() {
  const id = Number(useParams().id);
  const [params] = useSearchParams();
  const start = Number(params.get("t") ?? 0);
  const [video, setVideo] = useState<Video | null>(null);
  const [error, setError] = useState("");
  const player = useRef<PlayerHandle>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getVideo(id)
      .then(setVideo)
      .catch((err) => setError(errorMessage(err)));
  }, [id]);

  useEffect(() => {
    if (!video || !BUSY.has(video.status)) return;
    const timer = setInterval(() => getVideo(id).then(setVideo), 2000);
    return () => clearInterval(timer);
  }, [video, id]);

  function seek(seconds: number, videoId?: number) {
    if (videoId && videoId !== id) {
      navigate(`/videos/${videoId}?t=${Math.floor(seconds)}`);
      return;
    }
    player.current?.seekTo(seconds);
  }

  if (error) return <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>;
  if (!video) return <div className="h-64 animate-pulse rounded-lg bg-slate-100" />;

  const ready = video.status === "ready";

  return (
    <section className="grid gap-6 lg:grid-cols-[1fr_400px]">
      <div className="space-y-4">
        <Link to="/" className="text-sm text-slate-500 hover:underline">
          ← Library
        </Link>
        <YouTubePlayer ref={player} videoId={video.youtube_id} start={start} />
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">{video.title ?? video.youtube_id}</h1>
            <p className="text-sm text-slate-500">
              {video.channel} · {video.duration} · {video.segment_count} segments · {video.chunk_count} chunks
              {video.language ? ` · ${video.language}` : ""}
            </p>
          </div>
          <StatusBadge status={video.status} />
        </div>
        {video.error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{video.error}</p>}
        {ready && <InsightsPanel videoId={video.id} onSeek={(s) => seek(s)} />}
      </div>

      <div className="h-[80vh] lg:sticky lg:top-6">
        {ready ? (
          <ChatPanel
            key={video.id}
            videoId={video.id}
            onSeek={seek}
            suggestions={["Is video ka summary do", "3 MCQ banao", "Main point kya hai?"]}
          />
        ) : (
          <div className="rounded-lg border bg-white p-4 text-sm text-slate-500">
            Chat opens when the video is ready ({video.status}).
          </div>
        )}
      </div>
    </section>
  );
}
