import { Link } from "react-router-dom";

export default function Home() {
  return (
    <section className="space-y-4">
      <h1 className="text-3xl font-bold">Chat with any video</h1>
      <p className="text-slate-600">
        Paste a YouTube link or upload a video, then ask questions and jump straight to the moment
        that answers them.
      </p>
      <div className="flex gap-3">
        <Link to="/transcript" className="rounded-md bg-slate-900 px-4 py-2 text-white">
          Try transcript preview
        </Link>
        <Link to="/llm" className="rounded-md border px-4 py-2">
          Test LLM connection
        </Link>
      </div>
      <p className="text-sm text-slate-400">Day 1 build · chat, search and upload coming soon.</p>
    </section>
  );
}
