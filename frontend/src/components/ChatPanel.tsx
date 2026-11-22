import { useRef, useState, type FormEvent } from "react";
import { streamChat, type ChatResult, type HistoryMessage } from "../api/client";
import ProviderSelect from "./ProviderSelect";
import QuizView from "./QuizView";
import RichText from "./RichText";

type Message = {
  role: "user" | "assistant";
  text: string;
  steps?: string[];
  result?: ChatResult;
  error?: string;
  pending?: boolean;
};

type Props = {
  videoId: number | null;
  onSeek?: (seconds: number, videoId?: number) => void;
  suggestions?: string[];
};

export default function ChatPanel({ videoId, onSeek, suggestions = [] }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [provider, setProvider] = useState("");
  const [busy, setBusy] = useState(false);
  const abort = useRef<AbortController | null>(null);

  function update(patch: (m: Message) => Message) {
    setMessages((all) => [...all.slice(0, -1), patch(all[all.length - 1])]);
  }

  async function send(question: string) {
    if (!question.trim() || busy) return;
    const history: HistoryMessage[] = messages
      .filter((m) => !m.error && !m.pending)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.text }));
    setMessages((all) => [
      ...all,
      { role: "user", text: question },
      { role: "assistant", text: "", steps: [], pending: true },
    ]);
    setInput("");
    setBusy(true);
    abort.current = new AbortController();
    try {
      await streamChat(
        { question, video_id: videoId, provider, history },
        (event) => {
          if (event.type === "step") {
            update((m) => ({ ...m, steps: [...(m.steps ?? []), ...event.steps] }));
          } else if (event.type === "token") {
            update((m) => ({ ...m, text: m.text + event.text }));
          } else if (event.type === "retry") {
            update((m) => ({ ...m, text: "" }));
          } else if (event.type === "done") {
            update((m) => ({ ...m, text: event.result.answer, result: event.result, pending: false }));
          } else if (event.type === "error") {
            update((m) => ({ ...m, error: event.detail, pending: false }));
          }
        },
        abort.current.signal,
      );
    } catch (err) {
      update((m) => ({ ...m, error: err instanceof Error ? err.message : String(err), pending: false }));
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    send(input);
  }

  return (
    <div className="flex h-full flex-col rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
        <span className="text-sm font-medium">{videoId ? "Ask this video" : "Ask your library"}</span>
        <ProviderSelect value={provider} onChange={setProvider} />
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-3 text-sm">
        {messages.length === 0 && (
          <div className="space-y-2 text-slate-500">
            <p>Ask anything. Answers cite timestamps you can click.</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send(s)}
                  className="rounded-full border px-3 py-1 text-xs hover:bg-slate-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="ml-auto max-w-[85%] rounded-lg bg-slate-900 px-3 py-2 text-white">
              {m.text}
            </div>
          ) : (
            <div key={i} className="max-w-[95%] space-y-2">
              {m.steps && m.steps.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {m.steps.map((s, j) => (
                    <span key={j} className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-500">
                      {s}
                    </span>
                  ))}
                </div>
              )}
              {m.result?.quiz && m.result.quiz.questions.length > 0 ? (
                <QuizView quiz={m.result.quiz} onSeek={(s) => onSeek?.(s)} />
              ) : (
                m.text && (
                  <RichText
                    text={m.text}
                    onSeek={(s) => onSeek?.(s, m.result?.sources.find((x) => x.start <= s + 2 && s <= x.end + 2)?.video_id)}
                  />
                )
              )}
              {m.pending && !m.text && <p className="animate-pulse text-slate-400">Thinking…</p>}
              {m.error && <p className="rounded bg-red-50 p-2 text-red-700">{m.error}</p>}
              {m.result && (
                <p className="text-[11px] text-slate-400">
                  {m.result.intent} · {m.result.verified ? "citations verified" : "not verified"} ·{" "}
                  {m.result.provider} · {m.result.latency_ms} ms
                </p>
              )}
            </div>
          ),
        )}
      </div>

      <form onSubmit={onSubmit} className="flex gap-2 border-t p-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={videoId ? "Is video mein ... kya bataya?" : "Kaunsi video ... ke baare mein hai?"}
          className="flex-1 rounded-md border px-3 py-2 text-sm"
        />
        {busy ? (
          <button type="button" onClick={() => abort.current?.abort()} className="rounded-md border px-3 text-sm">
            Stop
          </button>
        ) : (
          <button className="rounded-md bg-slate-900 px-4 text-sm text-white disabled:opacity-50" disabled={!input.trim()}>
            Send
          </button>
        )}
      </form>
    </div>
  );
}
