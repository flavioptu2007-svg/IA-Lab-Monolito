export interface PresentationSlide {
  layout: "title" | "content" | "comparison" | "closing";
  title: string;
  subtitle: string;
  bullets: string[];
  speaker_notes: string;
  sources: string[];
}
export interface EducationTools {
  plugins: {
    id: string;
    name: string;
    license: string;
    installed: boolean;
    cost: string;
    format: string;
  }[];
  agents: { id: string; name: string; provider: string }[];
  skills: { id: string; content: string }[];
}
export type MaterialType =
  "lesson_plan" | "activity" | "evaluation" | "presentation";
export interface Moment {
  moment: string;
  title: string;
  description: string;
  duration_minutes: number;
  methodology: string;
  resources: string[];
  order: number;
}
export interface Question {
  number: number;
  type: string;
  command: string;
  options: string[];
  correct_answer: string;
  score: number;
  skill_code: string;
  feedback: string;
}
export interface Material {
  id: string;
  title: string;
  academic_year: string;
  subject: string;
  duration_minutes: number;
  bncc_skills: string[];
  updated_at: string;
  created_at: string;
  reviewed_at: string | null;
  status: string;
  is_ai_generated: boolean;
  topic?: string;
  trimester?: string;
  learning_objectives?: string[];
  resources?: string[];
  assessment_type?: string;
  moments?: Moment[];
  activity_type?: string;
  description?: string;
  content?: Record<string, unknown>;
  difficulty?: string;
  instructions?: string;
  evaluation_type?: string;
  total_score?: number;
  passing_score?: number;
  questions?: Question[];
  slides?: PresentationSlide[];
  theme?: "navy" | "paper";
}
export interface SavedMaterial {
  material_type: MaterialType;
  material: Material;
}
export interface GenerateRequest {
  material_type: MaterialType;
  topic: string;
  academic_year: string;
  duration_minutes: number;
  learning_objectives: string[];
  bncc_skills: string[];
  instructions: string;
  slide_count?: number;
  theme?: "navy" | "paper";
}
const FIELDS: Record<MaterialType, string[]> = {
  presentation: [
    "title",
    "academic_year",
    "subject",
    "duration_minutes",
    "bncc_skills",
    "theme",
    "slides",
  ],
  lesson_plan: [
    "title",
    "topic",
    "academic_year",
    "trimester",
    "subject",
    "learning_objectives",
    "bncc_skills",
    "resources",
    "assessment_type",
    "duration_minutes",
    "moments",
  ],
  activity: [
    "title",
    "activity_type",
    "description",
    "content",
    "difficulty",
    "duration_minutes",
    "academic_year",
    "subject",
    "bncc_skills",
    "instructions",
  ],
  evaluation: [
    "title",
    "evaluation_type",
    "description",
    "academic_year",
    "trimester",
    "subject",
    "bncc_skills",
    "total_score",
    "passing_score",
    "duration_minutes",
    "instructions",
    "questions",
  ],
};
export function editableContent(
  kind: MaterialType,
  material: Material,
): Record<string, unknown> {
  const values = { ...material } as unknown as Record<string, unknown>;
  if (kind === "presentation" && material.slides) {
    values.slides = material.slides.map((slide) => ({
      ...slide,
      bullets: slide.bullets.map((value) => value.trim()).filter(Boolean),
      sources: slide.sources.map((value) => value.trim()).filter(Boolean),
    }));
  }
  return Object.fromEntries(
    FIELDS[kind]
      .filter((key) => values[key] !== undefined)
      .map((key) => [key, values[key]]),
  );
}
export function educationStudioApi(token: string) {
  async function request<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`/api/v2/education${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "X-API-Key": token } : {}),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401)
        throw new Error(
          "Informe a chave de acesso da escola para abrir ou salvar materiais.",
        );
      const detail =
        typeof data.detail === "string"
          ? data.detail
          : "Confira os campos do formulário e tente novamente.";
      throw new Error(detail);
    }
    return data as T;
  }
  return {
    tools: () => request<EducationTools>("/tools"),
    checks: (id: string) =>
      request<{ issues: string[]; fact_checked: boolean }>(
        `/materials/presentation/${encodeURIComponent(id)}/checks`,
      ),
    download: async (id: string, format: "html" | "pptx") => {
      const response = await fetch(
        `/api/v2/education/materials/presentation/${encodeURIComponent(id)}/export/${format}`,
        { headers: token ? { "X-API-Key": token } : {} },
      );
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(
          typeof error.detail === "string"
            ? error.detail
            : "Não foi possível exportar a apresentação.",
        );
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `apresentacao-${id.slice(0, 8)}.${format}`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    generate: (body: GenerateRequest) =>
      request<SavedMaterial>("/generate", body),
    list: (offset = 0) =>
      request<{ materials: SavedMaterial[] }>(
        `/materials?limit=20&offset=${offset}`,
      ),
    review: (item: SavedMaterial, material: Material, approve: boolean) =>
      request<SavedMaterial>(
        `/materials/${item.material_type}/${encodeURIComponent(item.material.id)}/review`,
        {
          content: editableContent(item.material_type, material),
          expected_updated_at: item.material.updated_at,
          approve,
        },
      ),
  };
}
