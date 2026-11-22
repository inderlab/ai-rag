import type { VideoStatus } from "../api/client";

const STYLES: Record<VideoStatus, string> = {
  pending: "bg-slate-100 text-slate-700",
  processing: "bg-amber-100 text-amber-800",
  indexing: "bg-blue-100 text-blue-800",
  ready: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-700",
};

export default function StatusBadge({ status }: { status: VideoStatus }) {
  const busy = status === "pending" || status === "processing" || status === "indexing";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[status]}`}>
      {busy && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />}
      {status}
    </span>
  );
}
