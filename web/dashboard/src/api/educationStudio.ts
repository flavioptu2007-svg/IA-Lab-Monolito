export type MaterialType = "lesson_plan" | "activity" | "evaluation";
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
}
const FIELDS: Record<MaterialType, string[]> = {
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
  const values = material as unknown as Record<string, unknown>;
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
