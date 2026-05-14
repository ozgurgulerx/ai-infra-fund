import { STATUS_TONE_MAP, type ModuleStatusRecord } from "../lib/status-model";

type ComponentLane = {
  title: string;
  summary: string;
  moduleIds: string[];
};

const COMPONENT_LANES: ComponentLane[] = [
  {
    title: "Data Spine",
    summary: "Durable records, snapshots, embeddings, and runtime state.",
    moduleIds: ["postgres", "data-plane"]
  },
  {
    title: "Evidence & Research",
    summary: "Evidence ingestion, model routing, and analyst-facing traceability.",
    moduleIds: ["worker", "evidence-plane", "model-router"]
  },
  {
    title: "Signal Factory",
    summary: "Deterministic scores, signal bundles, and validation inputs.",
    moduleIds: ["signal-plane"]
  },
  {
    title: "Portfolio & Advisory",
    summary: "Deterministic target weights and advisory-only recommendation artifacts.",
    moduleIds: ["portfolio-engine", "recommendation-artifacts", "trade-journal"]
  },
  {
    title: "Governance & Ops",
    summary: "Evaluation, API boundary, and control-room visibility.",
    moduleIds: ["evaluation-harness", "api", "ui"]
  }
];

type HedgeFundComponentMapProps = {
  modules: ModuleStatusRecord[];
  sourceSummary: string;
};

export function HedgeFundComponentMap({ modules, sourceSummary }: HedgeFundComponentMapProps) {
  const modulesById = new Map(modules.map((module) => [module.id, module]));
  const knownModuleIds = new Set(COMPONENT_LANES.flatMap((lane) => lane.moduleIds));
  const additionalModules = modules.filter((module) => !knownModuleIds.has(module.id));
  const lanes = additionalModules.length
    ? [
        ...COMPONENT_LANES,
        {
          title: "Additional Live Modules",
          summary: "Modules reported by the live status feed outside the baseline map.",
          moduleIds: additionalModules.map((module) => module.id)
        }
      ]
    : COMPONENT_LANES;

  return (
    <section className="component-map" aria-label="Hedge Fund Component Map" data-testid="hedge-fund-component-map">
      <div className="component-map-header">
        <div>
          <p className="eyebrow">Architecture Picture</p>
          <h3>Hedge Fund Component Map</h3>
        </div>
        <span className="readonly-label">{sourceSummary}</span>
      </div>

      <div className="component-map-flow" aria-label="Advisory-only component flow">
        <span>Market data</span>
        <span>Evidence</span>
        <span>Signals</span>
        <span>Target weights</span>
        <span>Advisory recommendation</span>
        <span>Evaluation</span>
      </div>

      <div className="component-map-lanes">
        {lanes.map((lane) => (
          <div className="component-map-lane" key={lane.title}>
            <div className="component-map-lane-header">
              <strong>{lane.title}</strong>
              <span>{lane.summary}</span>
            </div>
            <div className="component-map-node-list">
              {lane.moduleIds.map((moduleId) => {
                const module = modulesById.get(moduleId);
                if (!module) {
                  return null;
                }

                const tone = STATUS_TONE_MAP[module.status];

                return (
                  <article className={`component-map-node ${tone.cssClass}`} key={module.id}>
                    <div className="component-map-node-header">
                      <span>
                        <strong>{module.name}</strong>
                        <small>{module.plane}</small>
                      </span>
                      <span className="status-pill">{tone.label}</span>
                    </div>
                    <p>{module.detail}</p>
                    <span className="component-map-source">{module.sourceLabel}</span>
                  </article>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
