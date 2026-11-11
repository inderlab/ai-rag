import axios from "axios";

export const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL ?? ""}/api`,
  timeout: 60_000,
});

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

export const getHealth = () => api.get<Health>("/health").then((r) => r.data);

export const getTranscript = (url: string, limit = 50) =>
  api.get<TranscriptResponse>("/transcript", { params: { url, limit } }).then((r) => r.data);

export const testLLM = (prompt: string, provider?: string) =>
  api.post<LLMTestResponse>("/llm/test", { prompt, provider }).then((r) => r.data);

export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) return err.response?.data?.detail ?? err.message;
  return String(err);
}
