import { useState } from "react";
import type { Quiz } from "../api/client";
import { toSeconds } from "../api/client";

type Props = { quiz: Quiz; onSeek?: (seconds: number) => void };

export default function QuizView({ quiz, onSeek }: Props) {
  const [picked, setPicked] = useState<Record<number, number>>({});
  const answered = Object.keys(picked).length;
  const correct = quiz.questions.filter((q, i) => picked[i] === q.answer).length;

  return (
    <div className="space-y-4">
      {quiz.questions.map((q, i) => {
        const choice = picked[i];
        return (
          <div key={i} className="rounded-lg border bg-white p-3">
            <p className="font-medium">
              {i + 1}. {q.question}
            </p>
            <div className="mt-2 grid gap-1.5">
              {q.options.map((opt, j) => {
                const chosen = choice === j;
                const show = choice !== undefined;
                const tone = !show
                  ? "hover:bg-slate-50"
                  : j === q.answer
                    ? "border-green-500 bg-green-50"
                    : chosen
                      ? "border-red-400 bg-red-50"
                      : "opacity-60";
                return (
                  <button
                    key={j}
                    type="button"
                    disabled={show}
                    onClick={() => setPicked((p) => ({ ...p, [i]: j }))}
                    className={`rounded-md border px-3 py-1.5 text-left text-sm ${tone}`}
                  >
                    {"abcd"[j]}) {opt}
                  </button>
                );
              })}
            </div>
            {choice !== undefined && (
              <p className="mt-2 text-sm text-slate-600">
                {q.explanation}
                {q.timestamp && (
                  <button
                    type="button"
                    onClick={() => onSeek?.(toSeconds(q.timestamp))}
                    className="ml-2 rounded bg-blue-50 px-1 font-mono text-xs text-blue-700"
                  >
                    {q.timestamp}
                  </button>
                )}
              </p>
            )}
          </div>
        );
      })}
      {answered > 0 && (
        <p className="text-sm font-medium">
          Score: {correct} / {answered}
        </p>
      )}
      {quiz.notes.length > 0 && (
        <div className="rounded-lg bg-amber-50 p-3 text-sm">
          <p className="mb-1 font-medium">Notes</p>
          <ul className="ml-5 list-disc space-y-1">
            {quiz.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
