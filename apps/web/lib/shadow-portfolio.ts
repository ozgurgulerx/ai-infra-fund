import { apiBaseUrl } from "./api";

const DEFAULT_TIMEOUT_MS = 2500;

export type ShadowDriftRow = {
  ticker: string;
  current_weight: string;
  target_weight: string;
  drift: string;
  notes?: string;
};

export type ShadowDriftPayload = {
  as_of: string;
  rows: ShadowDriftRow[];
  advisory_label: string;
  status?: string;
};

export type ShadowCurvePoint = {
  date: string;
  shadow_value: string;
  benchmark_value?: string;
};

export type ShadowSimulationPayload = {
  as_of: string;
  horizon_days?: number;
  curve: ShadowCurvePoint[];
  metrics: Record<string, string>;
  advisory_label: string;
  status?: string;
};

const EMPTY_DRIFT: ShadowDriftPayload = {
  as_of: new Date().toISOString(),
  rows: [],
  advisory_label: "advisory_only",
  status: "unavailable",
};

const EMPTY_SIMULATION: ShadowSimulationPayload = {
  as_of: new Date().toISOString(),
  curve: [],
  metrics: {},
  advisory_label: "advisory_only",
  status: "unavailable",
};

export async function fetchShadowDrift(): Promise<ShadowDriftPayload> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );
  try {
    const response = await fetch(
      `${apiBaseUrl()}/internal/shadow-portfolio/drift`,
      { cache: "no-store", method: "GET", signal: controller.signal },
    );
    const payload = (await response.json()) as { data?: ShadowDriftPayload };
    if (!response.ok || !payload.data) {
      return { ...EMPTY_DRIFT, status: "unavailable" };
    }
    return payload.data;
  } catch {
    return { ...EMPTY_DRIFT, status: "unavailable" };
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function fetchShadowSimulation(
  horizonDays = 30,
): Promise<ShadowSimulationPayload> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );
  try {
    const response = await fetch(
      `${apiBaseUrl()}/internal/shadow-portfolio/simulation?horizon_days=${horizonDays}`,
      { cache: "no-store", method: "GET", signal: controller.signal },
    );
    const payload = (await response.json()) as {
      data?: ShadowSimulationPayload;
    };
    if (!response.ok || !payload.data) {
      return { ...EMPTY_SIMULATION, status: "unavailable" };
    }
    return payload.data;
  } catch {
    return { ...EMPTY_SIMULATION, status: "unavailable" };
  } finally {
    window.clearTimeout(timeout);
  }
}
