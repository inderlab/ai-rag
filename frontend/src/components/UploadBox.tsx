import { useRef, useState, type FormEvent } from "react";
import { errorMessage, uploadVideo } from "../api/client";

const ACCEPT = ".mp4,.mov,.webm,.mkv,.mp3,.m4a,.wav,.ogg";

export default function UploadBox({ onDone }: { onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError("");
    setProgress(0);
    try {
      await uploadVideo(file, title, setProgress);
      setFile(null);
      setTitle("");
      if (input.current) input.current.value = "";
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setProgress(null);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-2 rounded-lg border border-dashed bg-white p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="flex-1 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5"
        />
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title (optional)"
          className="w-48 rounded-md border px-2 py-1.5"
        />
        <button
          disabled={!file || progress !== null}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-white disabled:opacity-50"
        >
          Upload
        </button>
      </div>
      {progress !== null && (
        <div className="h-1.5 overflow-hidden rounded bg-slate-100">
          <div className="h-full bg-blue-600 transition-all" style={{ width: `${progress}%` }} />
        </div>
      )}
      <p className="text-xs text-slate-500">Video or audio file. Whisper makes the transcript on the server.</p>
      {error && <p className="text-red-700">{error}</p>}
    </form>
  );
}
