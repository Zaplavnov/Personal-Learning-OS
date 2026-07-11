const apiBaseUrl = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export type ApiErrorPayload = {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
};

export type ReadinessResponse = {
  status: "ready";
  database: "available";
};

export type MetaResponse = {
  name: string;
  version: string;
  environment: string;
};

export type LearningGoalStatus = "active" | "paused" | "completed";
export type LearningSpaceStatus = "active" | "archived";

export type LearningGoal = {
  id: string;
  learning_space_id: string;
  title: string;
  description: string | null;
  priority: number;
  status: LearningGoalStatus;
  target_date: string | null;
  expected_capabilities: string[];
  completion_criteria: string[];
  created_at: string;
  updated_at: string;
};

export type LearningSpace = {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  color: string | null;
  status: LearningSpaceStatus;
  created_at: string;
  updated_at: string;
  goals: LearningGoal[];
};

export type LearningSpaceCreate = {
  title: string;
  description?: string | null;
  color?: string | null;
};

export type LearningGoalCreate = {
  title: string;
  description?: string | null;
  priority?: number;
  status?: LearningGoalStatus;
  target_date?: string | null;
  expected_capabilities?: string[];
  completion_criteria?: string[];
};

export type MaterialType =
  | "video"
  | "article"
  | "book"
  | "notebook"
  | "repository"
  | "other";
export type MaterialStatus = "active" | "completed" | "archived";
export type LearningSessionStatus = "active" | "completed" | "abandoned";
export type NoteType = "insight" | "question" | "gap" | "example" | "general";

export type LearningSession = {
  id: string;
  material_id: string;
  user_id: string;
  started_at: string;
  ended_at: string | null;
  start_position_seconds: number | null;
  end_position_seconds: number | null;
  reflection: string | null;
  status: LearningSessionStatus;
};

export type Material = {
  id: string;
  user_id: string;
  learning_space_id: string;
  type: MaterialType;
  title: string;
  url: string | null;
  author: string | null;
  description: string | null;
  status: MaterialStatus;
  estimated_minutes: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MaterialDetail = Material & {
  active_session: LearningSession | null;
};

export type MaterialCreate = {
  learning_space_id: string;
  type: MaterialType;
  title: string;
  url?: string | null;
  author?: string | null;
  description?: string | null;
  estimated_minutes?: number | null;
  metadata?: Record<string, unknown>;
};

export type Note = {
  id: string;
  user_id: string;
  learning_space_id: string;
  material_id: string | null;
  learning_session_id: string | null;
  body: string;
  source_position_seconds: number | null;
  note_type: NoteType;
  created_at: string;
  updated_at: string;
};

export type ConceptStatus = "active" | "archived";
export type ConceptRelationType =
  | "prerequisite_of"
  | "depends_on"
  | "part_of"
  | "example_of"
  | "generalization_of"
  | "special_case_of"
  | "contrasts_with"
  | "often_confused_with"
  | "used_in"
  | "derived_from"
  | "analogous_to"
  | "explains"
  | "implemented_by";

export type Concept = {
  id: string;
  user_id: string;
  learning_space_id: string;
  title: string;
  description: string | null;
  aliases: string[];
  status: ConceptStatus;
  created_at: string;
  updated_at: string;
};

export type ConceptRelation = {
  id: string;
  learning_space_id: string;
  source_concept_id: string;
  target_concept_id: string;
  relation_type: ConceptRelationType;
  description: string | null;
};

export type KnowledgeGraph = {
  concepts: Concept[];
  relations: ConceptRelation[];
};

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly details: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response
      .json()
      .catch(() => null)) as ApiErrorPayload | null;
    throw new ApiClientError(
      payload?.error.message ?? "Backend request failed",
      response.status,
      payload?.error.code ?? "unknown_error",
      payload?.error.details ?? {},
    );
  }

  return response.json() as Promise<T>;
}

export const backendApi = {
  getReadiness: (signal?: AbortSignal) =>
    apiRequest<ReadinessResponse>("/health/ready", {
      signal,
      cache: "no-store",
    }),
  getMeta: (signal?: AbortSignal) =>
    apiRequest<MetaResponse>("/api/v1/meta", { signal, cache: "no-store" }),
  listLearningSpaces: (signal?: AbortSignal) =>
    apiRequest<LearningSpace[]>("/api/v1/learning-spaces", {
      signal,
      cache: "no-store",
    }),
  getLearningSpace: (spaceId: string, signal?: AbortSignal) =>
    apiRequest<LearningSpace>(`/api/v1/learning-spaces/${spaceId}`, {
      signal,
      cache: "no-store",
    }),
  createLearningSpace: (payload: LearningSpaceCreate) =>
    apiRequest<LearningSpace>("/api/v1/learning-spaces", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createLearningGoal: (spaceId: string, payload: LearningGoalCreate) =>
    apiRequest<LearningGoal>(`/api/v1/learning-spaces/${spaceId}/goals`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  activateLearningGoal: (goalId: string) =>
    apiRequest<LearningGoal>(`/api/v1/learning-goals/${goalId}/activate`, {
      method: "POST",
    }),
  listMaterials: (
    filters: { learningSpaceId?: string; type?: MaterialType } = {},
    signal?: AbortSignal,
  ) => {
    const params = new URLSearchParams();
    if (filters.learningSpaceId)
      params.set("learning_space_id", filters.learningSpaceId);
    if (filters.type) params.set("type", filters.type);
    const query = params.size ? `?${params.toString()}` : "";
    return apiRequest<Material[]>(`/api/v1/materials${query}`, {
      signal,
      cache: "no-store",
    });
  },
  getMaterial: (materialId: string, signal?: AbortSignal) =>
    apiRequest<MaterialDetail>(`/api/v1/materials/${materialId}`, {
      signal,
      cache: "no-store",
    }),
  createMaterial: (payload: MaterialCreate) =>
    apiRequest<Material>("/api/v1/materials", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  startLearningSession: (
    materialId: string,
    startPositionSeconds: number | null,
  ) =>
    apiRequest<LearningSession>(`/api/v1/materials/${materialId}/sessions`, {
      method: "POST",
      body: JSON.stringify({ start_position_seconds: startPositionSeconds }),
    }),
  completeLearningSession: (
    sessionId: string,
    payload: { end_position_seconds: number | null; reflection: string | null },
  ) =>
    apiRequest<LearningSession>(
      `/api/v1/learning-sessions/${sessionId}/complete`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    ),
  listMaterialNotes: (materialId: string, signal?: AbortSignal) =>
    apiRequest<Note[]>(`/api/v1/materials/${materialId}/notes`, {
      signal,
      cache: "no-store",
    }),
  createNote: (payload: {
    learning_space_id: string;
    material_id: string;
    learning_session_id: string | null;
    body: string;
    source_position_seconds: number | null;
    note_type: NoteType;
  }) =>
    apiRequest<Note>("/api/v1/notes", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getKnowledgeGraph: (learningSpaceId: string, signal?: AbortSignal) =>
    apiRequest<KnowledgeGraph>(
      `/api/v1/knowledge-graph?learning_space_id=${encodeURIComponent(learningSpaceId)}`,
      { signal, cache: "no-store" },
    ),
  createConcept: (payload: {
    learning_space_id: string;
    title: string;
    description: string | null;
    aliases: string[];
  }) =>
    apiRequest<Concept>("/api/v1/concepts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createConceptRelation: (payload: {
    source_concept_id: string;
    target_concept_id: string;
    relation_type: ConceptRelationType;
    description: string | null;
  }) =>
    apiRequest<ConceptRelation>("/api/v1/concept-relations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
