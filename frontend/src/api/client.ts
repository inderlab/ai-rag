import axios from "axios";

const BASE = `${import.meta.env.VITE_API_URL ?? ""}/api`;

export const api = axios.create({ baseURL: BASE, timeout: 120_000 });

export type Health = { status: string; app: string; llm_provider: string };

export type Segment = { text: string; start: number; end: number; timestamp: string };

export type TranscriptResponse = {
  video_id: string;
  segment_count: number;
  segments: Segment[];
};

export type LLMTestResponse = {
  provider: string;
  model: string;
  answer: string;
  latency_ms: number;
};

export type Provider = {
  name: string;
  model: string;
  configured: boolean;
  default: boolean;
  supports_temperature: boolean;
};

export type VideoStatus = "pending" | "processing" | "indexing" | "ready" | "failed";

export type Video = {
  id: number;
  youtube_id: string;
  url: string;
  title: string | null;
  channel: string | null;
  status: VideoStatus;
  error: string | null;
  language: string | null;
  is_generated: boolean | null;
  segment_count: number;
  chunk_count: number;
  duration_seconds: number | null;
  duration: string | null;
  thumbnail_url: string;
  created_at: string;
  updated_at: string;
};

export type Chapter = { start: string; title: string; seconds: number };

export type Insights = {
  video_id: number;
  title: string;
  summary: string;
  chapters: Chapter[];
  tags: string[];
  key_points: string[];
  provider: string;
  model: string;
};

export type SearchHit = {
  rank: number;
  video_id: number;
  title: string;
  start: number;
  timestamp: string;
  end_timestamp: string;
  url: string;
  score: number;
  text: string;
};

export type Citation = { timestamp: string; seconds: number };

export type Source = {
  video_id: number;
  title: string;
  timestamp: string;
  end_timestamp: string;
  start: number;
  end: number;
  score: number;
  text: string;
};

export type QuizQuestion = {
  question: string;
  options: string[];
  answer: number;
  explanation: string;
  timestamp: string;
};

export type Quiz = { questions: QuizQuestion[]; notes: string[] };

export type ChatResult = {
  question: string;
  video_id: number | null;
  answer: string;
  found: boolean;
  citations: Citation[];
  sources: Source[];
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  intent: string;
  route_reason: string;
  search_query: string;
  steps: string[];
  verified: boolean;
  verify_notes: string[];
  quiz: Quiz | null;
  latency_ms: number;
};

export type HistoryMessage = { role: "user" | "assistant"; content: string };

export type ChatRequest = {
  question: string;
  video_id: number | null;
  provider?: string;
  history?: HistoryMessage[];
};

export type StreamEvent =
  | { type: "start"; provider: string; model: string }
  | { type: "step"; node: string; steps: string[] }
  | { type: "token"; text: string }
  | { type: "retry"; notes: string[] }
  | { type: "done"; result: ChatResult }
  | { type: "error"; detail: string };

export const getHealth = () => api.get<Health>("/health").then((r) => r.data);

export const getTranscript = (url: string, limit = 50) =>
  api.get<TranscriptResponse>("/transcript", { params: { url, limit } }).then((r) => r.data);

export const testLLM = (prompt: string, provider?: string) =>
  api.post<LLMTestResponse>("/llm/test", { prompt, provider }).then((r) => r.data);

export const getProviders = () => api.get<Provider[]>("/llm/providers").then((r) => r.data);

export const listVideos = () => api.get<Video[]>("/videos").then((r) => r.data);

export const getVideo = (id: number) => api.get<Video>(`/videos/${id}`).then((r) => r.data);

export const addVideo = (url: string) => api.post<Video>("/videos", { url }).then((r) => r.data);

export const retryVideo = (id: number) =>
  api.post<Video>(`/videos/${id}/retry`).then((r) => r.data);

export const deleteVideo = (id: number) => api.delete(`/videos/${id}`);

export const getInsights = (id: number) =>
  api.get<Insights>(`/videos/${id}/insights`).then((r) => r.data);

export const generateInsights = (id: number, provider?: string) =>
  api.post<Insights>(`/videos/${id}/insights`, { provider: provider || null }).then((r) => r.data);

export const searchLibrary = (q: string, videoId?: number) =>
  api
    .get<{ results: SearchHit[] }>("/search", { params: { q, video_id: videoId, k: 8 } })
    .then((r) => r.data.results);

export async function streamChat(
  body: ChatRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, provider: body.provider || null }),
    signal,
  });
  if (!res.ok || !res.body) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? `Request failed (${res.status})`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (line) onEvent(JSON.parse(line.slice(6)) as StreamEvent);
    }
  }
}

export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) return err.response?.data?.detail ?? err.message;
  if (err instanceof Error) return err.message;
  return String(err);
}

export function toSeconds(ts: string): number {
  return ts.split(":").reduce((acc, part) => acc * 60 + Number(part), 0);
}
