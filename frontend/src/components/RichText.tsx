import { Fragment, type ReactNode } from "react";
import { toSeconds } from "../api/client";

const TOKEN = /(\[(?:\d{1,2}:)?\d{1,2}:\d{2}\]|\*\*[^*]+\*\*)/g;

type Props = { text: string; onSeek?: (seconds: number) => void };

function inline(line: string, onSeek?: (seconds: number) => void): ReactNode[] {
  return line.split(TOKEN).map((part, i) => {
    if (/^\[(?:\d{1,2}:)?\d{1,2}:\d{2}\]$/.test(part)) {
      const ts = part.slice(1, -1);
      return (
        <button
          key={i}
          type="button"
          onClick={() => onSeek?.(toSeconds(ts))}
          className="mx-0.5 rounded bg-blue-50 px-1 font-mono text-xs text-blue-700 hover:bg-blue-100"
          title={`Jump to ${ts}`}
        >
          {ts}
        </button>
      );
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

export default function RichText({ text, onSeek }: Props) {
  const blocks: ReactNode[] = [];
  let bullets: string[] = [];

  const flush = () => {
    if (bullets.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="ml-5 list-disc space-y-1">
          {bullets.map((b, i) => (
            <li key={i}>{inline(b, onSeek)}</li>
          ))}
        </ul>,
      );
      bullets = [];
    }
  };

  text.split("\n").forEach((raw) => {
    const line = raw.trimEnd();
    if (/^\s*[-*]\s+/.test(line)) {
      bullets.push(line.replace(/^\s*[-*]\s+/, ""));
      return;
    }
    flush();
    if (line.trim()) blocks.push(<p key={`p-${blocks.length}`}>{inline(line, onSeek)}</p>);
  });
  flush();

  return <div className="space-y-2 leading-relaxed">{blocks}</div>;
}
