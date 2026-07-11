const apiBaseUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

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
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ApiErrorPayload | null;
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
    apiRequest<ReadinessResponse>("/health/ready", { signal, cache: "no-store" }),
  getMeta: (signal?: AbortSignal) =>
    apiRequest<MetaResponse>("/api/v1/meta", { signal, cache: "no-store" }),
};
