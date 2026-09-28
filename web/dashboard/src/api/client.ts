import { useCallback, useEffect, useState } from "react";

// ─── Tipos Compartilhados ──────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  uptime_seconds: number;
  providers_available: number;
  memory_mb: number;
}

export interface ProviderInfo {
  name: string;
  available: boolean;
  model: string;
}

export interface AgentInfo {
  type: string;
  display_name: string;
  description: string;
  temperature: number;
  max_tokens: number;
}

export interface ChatRequest {
  message: string;
  provider?: string;
  model?: string;
  temperature?: number;
  stream?: boolean;
}

export interface ChatResponse {
  response: string;
  provider: string;
  model: string;
  elapsed_ms: number;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface HistoryEntry {
  id: string;
  role: string;
  content: string;
  timestamp: string;
}

export interface MetricEntry {
  name: string;
  value: number;
  unit: string;
  timestamp: string;
}

export interface AudioStatus {
  enabled: boolean;
  mic_available: boolean;
  device: string | null;
  sample_rate: number;
}

export interface BNCCSkill {
  code: string;
  description: string;
  competence: string;
  year: string;
}

export interface BNCCCompetence {
  code: string;
  name: string;
  description: string;
}

export interface LessonPlan {
  id?: string;
  title: string;
  subject: string;
  year: string;
  duration_minutes: number;
  objectives: string[];
  skills: string[];
  content: string;
  methodology: string;
  resources: string[];
  assessment: string;
  created_at?: string;
  updated_at?: string;
}

export interface Activity {
  id?: string;
  title: string;
  description: string;
  type: string;
  subject: string;
  year: string;
  duration_minutes: number;
  materials: string[];
  instructions: string;
  skills: string[];
  created_at?: string;
}

export interface Evaluation {
  id?: string;
  title: string;
  subject: string;
  year: string;
  type: string;
  weight: number;
  max_score: number;
  criteria: string[];
  created_at?: string;
}

export interface CalendarEntry {
  id?: string;
  title: string;
  date: string;
  type: string;
  description: string;
  subject?: string;
  created_at?: string;
}

export interface OpenVINOHealth {
  available: boolean;
  version?: string;
  devices?: string[];
  models_count?: number;
}

export interface OpenVINOGenerate {
  output: string;
  elapsed_ms: number;
  tokens: number;
}

export interface OpenVINOTranscribe {
  text: string;
  elapsed_ms: number;
}

export interface OpenVINORagQuery {
  answer: string;
  sources: { title: string; score: number }[];
  elapsed_ms: number;
}

export interface ConfigResponse {
  default_provider: string;
  default_model: string;
  temperature: number;
  max_tokens: number;
  providers_count: number;
}

// ─── API Client ────────────────────────────────────────────────────────

const BASE_URL = "/api";

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiFetchText(path: string, options?: RequestInit): Promise<string> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `HTTP ${res.status}`);
  }
  return res.text();
}

export const api = {
  // Health & System
  health: () => apiFetch<HealthResponse>("/health"),
  config: () => apiFetch<ConfigResponse>("/api/config"),
  metrics: () => apiFetch<MetricEntry[]>("/api/metrics"),
  providers: () => apiFetch<ProviderInfo[]>("/api/providers"),
  agents: () => apiFetch<AgentInfo[]>("/api/agents"),

  // Chat
  chat: (req: ChatRequest) =>
    apiFetch<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  chatStream: (req: ChatRequest): Promise<Response> =>
    fetch(`${BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...req, stream: true }),
    }),

  // History
  history: () => apiFetch<HistoryEntry[]>("/api/history"),
  historyClear: () => apiFetch<{ status: string }>("/api/history", { method: "DELETE" }),

  // Audio
  audioStatus: () => apiFetch<AudioStatus>("/api/audio/status"),
  audioDevices: () => apiFetch<string[]>("/api/audio/devices"),
  audioConfig: () =>
    apiFetch<{ enabled: boolean; sample_rate: number; channels: number }>("/api/audio/config"),
  audioMicStatus: () => apiFetch<{ available: boolean; device: string }>("/api/audio/mic/status"),

  // Coraci v2
  v2Config: () => apiFetch<Record<string, unknown>>("/api/v2/chat/config"),
  v2UpdateConfig: (cfg: Record<string, unknown>) =>
    apiFetch<{ status: string }>("/api/v2/chat/config", {
      method: "POST",
      body: JSON.stringify(cfg),
    }),
  v2Conversations: () => apiFetch<ConversationSummary[]>("/api/v2/conversations"),
  v2ClearConversations: () =>
    apiFetch<{ status: string; deleted: number }>("/api/v2/conversations", {
      method: "DELETE",
    }),

  // Education
  educationHealth: () => apiFetch<{ status: string; modules: number }>("/api/v2/education/health"),
  bnccSkills: (params?: { year?: string; competence?: string; query?: string }) => {
    const search = new URLSearchParams();
    if (params?.year) search.set("year", params.year);
    if (params?.competence) search.set("competence", params.competence);
    if (params?.query) search.set("query", params.query);
    const qs = search.toString();
    return apiFetch<BNCCSkill[]>(`/api/v2/education/bncc/skills${qs ? `?${qs}` : ""}`);
  },
  bnccCompetences: () => apiFetch<BNCCCompetence[]>("/api/v2/education/bncc/competences"),

  lessonPlans: {
    list: () => apiFetch<LessonPlan[]>("/api/v2/education/lesson-plans"),
    get: (id: string) => apiFetch<LessonPlan>(`/api/v2/education/lesson-plans/${id}`),
    create: (data: LessonPlan) =>
      apiFetch<LessonPlan>("/api/v2/education/lesson-plans", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<LessonPlan>) =>
      apiFetch<LessonPlan>(`/api/v2/education/lesson-plans/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ status: string }>(`/api/v2/education/lesson-plans/${id}`, {
        method: "DELETE",
      }),
  },

  activities: {
    list: () => apiFetch<Activity[]>("/api/v2/education/activities"),
    get: (id: string) => apiFetch<Activity>(`/api/v2/education/activities/${id}`),
    create: (data: Activity) =>
      apiFetch<Activity>("/api/v2/education/activities", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<Activity>) =>
      apiFetch<Activity>(`/api/v2/education/activities/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ status: string }>(`/api/v2/education/activities/${id}`, {
        method: "DELETE",
      }),
  },

  evaluations: {
    list: () => apiFetch<Evaluation[]>("/api/v2/education/evaluations"),
    get: (id: string) => apiFetch<Evaluation>(`/api/v2/education/evaluations/${id}`),
    create: (data: Evaluation) =>
      apiFetch<Evaluation>("/api/v2/education/evaluations", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<Evaluation>) =>
      apiFetch<Evaluation>(`/api/v2/education/evaluations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ status: string }>(`/api/v2/education/evaluations/${id}`, {
        method: "DELETE",
      }),
  },

  calendar: {
    list: () => apiFetch<CalendarEntry[]>("/api/v2/education/calendar"),
    create: (data: CalendarEntry) =>
      apiFetch<CalendarEntry>("/api/v2/education/calendar", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ status: string }>(`/api/v2/education/calendar/${id}`, {
        method: "DELETE",
      }),
  },

  // OpenVINO
  openvino: {
    health: () => apiFetch<OpenVINOHealth>("/api/v2/openvino/health"),
    models: () => apiFetch<string[]>("/api/v2/openvino/models"),
    generate: (prompt: string) =>
      apiFetch<OpenVINOGenerate>("/api/v2/openvino/generate", {
        method: "POST",
        body: JSON.stringify({ prompt }),
      }),
    transcribe: (audioPath: string) =>
      apiFetch<OpenVINOTranscribe>("/api/v2/openvino/transcribe", {
        method: "POST",
        body: JSON.stringify({ audio_path: audioPath }),
      }),
    ragQuery: (question: string) =>
      apiFetch<OpenVINORagQuery>("/api/v2/openvino/rag/query", {
        method: "POST",
        body: JSON.stringify({ question }),
      }),
  },

  // Logs
  logs: () => apiFetchText("/api/logs"),
};

// ─── Hook ──────────────────────────────────────────────────────────────

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(() => {
    setLoading(true);
    setError(null);
    fetcher()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
