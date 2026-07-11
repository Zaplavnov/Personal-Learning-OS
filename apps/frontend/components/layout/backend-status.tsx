"use client";

import { useEffect, useState } from "react";
import { backendApi } from "@/lib/api/client";

type BackendState = "checking" | "ready" | "unavailable";

const labels: Record<BackendState, string> = {
  checking: "Проверяем backend",
  ready: "Backend готов",
  unavailable: "Backend недоступен",
};

export function BackendStatus() {
  const [state, setState] = useState<BackendState>("checking");

  useEffect(() => {
    const controller = new AbortController();

    backendApi
      .getReadiness(controller.signal)
      .then(() => setState("ready"))
      .catch(() => {
        if (!controller.signal.aborted) setState("unavailable");
      });

    return () => controller.abort();
  }, []);

  return (
    <div className={`backend-status ${state}`} role="status">
      <span className="status-dot" /> {labels[state]}
    </div>
  );
}
