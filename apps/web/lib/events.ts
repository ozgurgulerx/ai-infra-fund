import { apiBaseUrl } from "./api";

const DEFAULT_TIMEOUT_MS = 2500;

export type ExperimentEvent = {
  event_id: string;
  kind: string;
  run_id: string | null;
  severity: "info" | "warn" | "error";
  payload: Record<string, unknown>;
  occurred_at: string;
  created_at: string;
};

export type ExperimentEventsPayload = {
  events: ExperimentEvent[];
  count: number;
};

const EVENT_LABELS: Record<string, string> = {
  signal_computed: "Signal computed",
  weights_generated: "Advisory weights generated",
  recommendation_issued: "Recommendation issued",
  backtest_started: "Backtest started",
  backtest_completed: "Backtest completed",
  shadow_comparison_recorded: "Shadow comparison recorded",
  price_disagreement: "Price source disagreement",
};

export function eventLabel(kind: string): string {
  return EVENT_LABELS[kind] ?? kind;
}

export async function fetchRecentEvents(
  limit = 25,
): Promise<ExperimentEventsPayload> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );
  try {
    const response = await fetch(
      `${apiBaseUrl()}/internal/events/recent?limit=${limit}`,
      { cache: "no-store", method: "GET", signal: controller.signal },
    );
    const payload = (await response.json()) as {
      data?: ExperimentEventsPayload;
    };
    if (!response.ok || !payload.data) {
      return { events: [], count: 0 };
    }
    return payload.data;
  } catch {
    return { events: [], count: 0 };
  } finally {
    window.clearTimeout(timeout);
  }
}
