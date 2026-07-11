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
};
