export type ModuleStatus = "passing" | "degraded" | "failing" | "planned";
export type StatusTone = "green" | "yellow" | "red" | "gray";
export type StatusSourceType =
  | "health_check"
  | "readiness_check"
  | "test_result"
  | "policy_check"
  | "run_artifact"
  | "static_scaffold";

export type ModuleStatusRecord = {
  id: string;
  name: string;
  plane: string;
  status: ModuleStatus;
  sourceType: StatusSourceType;
  sourceLabel: string;
  detail: string;
  specRefs: string[];
  dependencies: string[];
};

export type RuntimeProbe = {
  state: "available" | "unavailable";
  status: string;
  detail: string;
  checkedAt: string;
  sourceLabel: string;
};

export const STATUS_TONE_MAP: Record<
  ModuleStatus,
  { tone: StatusTone; label: string; cssClass: string }
> = {
  passing: {
    tone: "green",
    label: "Passing",
    cssClass: "status-green"
  },
  degraded: {
    tone: "yellow",
    label: "Degraded",
    cssClass: "status-yellow"
  },
  failing: {
    tone: "red",
    label: "Failing",
    cssClass: "status-red"
  },
  planned: {
    tone: "gray",
    label: "Planned",
    cssClass: "status-gray"
  }
};

export const BASE_MODULES: ModuleStatusRecord[] = [
  {
    id: "api",
    name: "API Boundary",
    plane: "Runtime",
    status: "degraded",
    sourceType: "health_check",
    sourceLabel: "Waiting for /health",
    detail: "FastAPI service status is checked from the local API health endpoint.",
    specRefs: ["0015", "deployment_harness"],
    dependencies: ["postgres"]
  },
  {
    id: "worker",
    name: "Worker",
    plane: "Runtime",
    status: "degraded",
    sourceType: "static_scaffold",
    sourceLabel: "Verified by compose smoke, no live worker endpoint",
    detail: "Worker startup is verified by smoke tests; scheduled jobs remain stubbed.",
    specRefs: ["0015"],
    dependencies: ["postgres", "model-router"]
  },
  {
    id: "postgres",
    name: "PostgreSQL + pgvector",
    plane: "Storage",
    status: "degraded",
    sourceType: "readiness_check",
    sourceLabel: "Waiting for /ready database check",
    detail: "Database readiness is inferred from the API readiness endpoint.",
    specRefs: ["0012", "0015"],
    dependencies: []
  },
  {
    id: "ui",
    name: "Control-Room UI",
    plane: "Analyst UI",
    status: "passing",
    sourceType: "test_result",
    sourceLabel: "Phase 8 UI acceptance tests",
    detail: "Read-only dashboard shell with advisory labels and policy checks.",
    specRefs: ["0005", "0011"],
    dependencies: ["api"]
  },
  {
    id: "data-plane",
    name: "Data Plane",
    plane: "Data",
    status: "passing",
    sourceType: "test_result",
    sourceLabel: "Phase 2 migration and repository tests",
    detail: "Canonical records, snapshots, model runs, and audit tables are in PostgreSQL.",
    specRefs: ["0003", "0012"],
    dependencies: ["postgres"]
  },
  {
    id: "evidence-plane",
    name: "Evidence Plane",
    plane: "Evidence",
    status: "passing",
    sourceType: "test_result",
    sourceLabel: "Phase 5 and 5b evidence tests",
    detail: "Local evidence ingestion, chunking, embeddings, and claim extraction foundations exist.",
    specRefs: ["0003", "0013"],
    dependencies: ["postgres", "model-router"]
  },
  {
    id: "signal-plane",
    name: "Signal Plane",
    plane: "Signals",
    status: "passing",
    sourceType: "test_result",
    sourceLabel: "Phase 4 deterministic signal tests",
    detail: "Strategic, technical, forward, and risk scores are deterministic.",
    specRefs: ["0003", "0008"],
    dependencies: ["data-plane"]
  },
  {
    id: "portfolio-engine",
    name: "Portfolio Engine",
    plane: "Portfolio",
    status: "passing",
    sourceType: "policy_check",
    sourceLabel: "Phase 4 target-weight policy tests",
    detail: "Target weights are produced by deterministic portfolio code only.",
    specRefs: ["0002", "0003"],
    dependencies: ["signal-plane"]
  },
  {
    id: "model-router",
    name: "Model Router",
    plane: "LLM Governance",
    status: "passing",
    sourceType: "test_result",
    sourceLabel: "Phase 3 model-routing tests",
    detail: "Model profiles, task routing, data-class policy, and ModelRun ledger exist.",
    specRefs: ["0008", "0013"],
    dependencies: ["postgres"]
  },
  {
    id: "recommendation-artifacts",
    name: "Recommendation Artifacts",
    plane: "Recommendations",
    status: "passing",
    sourceType: "test_result",
    sourceLabel: "Phase 6 recommendation audit tests",
    detail: "Artifacts are advisory-only and require evidence, model run, signal, and target-weight IDs.",
    specRefs: ["0002", "0008"],
    dependencies: ["evidence-plane", "signal-plane", "portfolio-engine"]
  },
  {
    id: "evaluation-harness",
    name: "Evaluation Harness",
    plane: "Evaluation",
    status: "passing",
    sourceType: "test_result",
    sourceLabel: "Phase 7 evaluation tests",
    detail: "Walk-forward, leakage checks, costs, stress, benchmark, and shadow records exist.",
    specRefs: ["0009"],
    dependencies: ["data-plane", "recommendation-artifacts"]
  },
  {
    id: "trade-journal",
    name: "Manual Trade Journal",
    plane: "Portfolio",
    status: "planned",
    sourceType: "static_scaffold",
    sourceLabel: "Read-only placeholder in Phase 8",
    detail: "Manual journal capture is intentionally not enabled in this read-only UI phase.",
    specRefs: ["0002", "0005"],
    dependencies: ["portfolio-engine"]
  }
];

export function applyRuntimeProbes(
  modules: ModuleStatusRecord[],
  health: RuntimeProbe,
  readiness: RuntimeProbe
): ModuleStatusRecord[] {
  return modules.map((module) => {
    if (module.id === "api") {
      if (health.state === "available" && health.status === "ok") {
        return {
          ...module,
          status: "passing",
          sourceLabel: health.sourceLabel,
          detail: health.detail
        };
      }
      return {
        ...module,
        status: "failing",
        sourceLabel: health.sourceLabel,
        detail: health.detail
      };
    }

    if (module.id === "postgres") {
      if (readiness.state === "available" && readiness.status === "ready") {
        return {
          ...module,
          status: "passing",
          sourceLabel: readiness.sourceLabel,
          detail: readiness.detail
        };
      }
      return {
        ...module,
        status: "degraded",
        sourceLabel: readiness.sourceLabel,
        detail: readiness.detail
      };
    }

    return module;
  });
}

export function summarizeModules(modules: ModuleStatusRecord[]) {
  return modules.reduce(
    (summary, module) => ({
      ...summary,
      [module.status]: summary[module.status] + 1
    }),
    { passing: 0, degraded: 0, failing: 0, planned: 0 } satisfies Record<ModuleStatus, number>
  );
}
