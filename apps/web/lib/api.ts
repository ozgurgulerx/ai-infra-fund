import type { RuntimeProbe } from "./status-model";

type ProbeEndpoint = "health" | "ready";

const DEFAULT_TIMEOUT_MS = 2500;

export function apiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
}

export async function fetchApiHealth(): Promise<RuntimeProbe> {
  return fetchProbe("health");
}

export async function fetchApiReadiness(): Promise<RuntimeProbe> {
  return fetchProbe("ready");
}

async function fetchProbe(endpoint: ProbeEndpoint): Promise<RuntimeProbe> {
  const checkedAt = new Date().toISOString();
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(`${apiBaseUrl()}/${endpoint}`, {
      cache: "no-store",
      signal: controller.signal
    });
    const payload = (await response.json()) as {
      data?: {
        service?: string;
        status?: string;
        checks?: Record<string, string>;
      };
    };
    const status = payload.data?.status ?? "unknown";
    const databaseStatus = payload.data?.checks?.database;
    const detail =
      endpoint === "ready"
        ? `API readiness ${status}; database ${databaseStatus ?? "not reported"}.`
        : `API health ${status}.`;

    return {
      state: response.ok ? "available" : "unavailable",
      status,
      detail,
      checkedAt,
      sourceLabel: `API /${endpoint}`
    };
  } catch (error) {
    const reason = error instanceof Error ? error.message : "request failed";
    return {
      state: "unavailable",
      status: "unavailable",
      detail: `Backend unavailable: ${reason}`,
      checkedAt,
      sourceLabel: `API /${endpoint}`
    };
  } finally {
    window.clearTimeout(timeout);
  }
}
