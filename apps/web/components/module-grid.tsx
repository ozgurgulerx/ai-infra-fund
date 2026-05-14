import { STATUS_TONE_MAP, type ModuleStatusRecord } from "../lib/status-model";

type ModuleGridProps = {
  modules: ModuleStatusRecord[];
};

export function ModuleGrid({ modules }: ModuleGridProps) {
  return (
    <div className="module-grid" data-testid="module-grid">
      {modules.map((module) => {
        const tone = STATUS_TONE_MAP[module.status];

        return (
          <details className={`module-node ${tone.cssClass}`} key={module.id}>
            <summary>
              <span>
                <span className="module-name">{module.name}</span>
                <span className="module-plane">{module.plane}</span>
              </span>
              <span className="status-pill">{tone.label}</span>
            </summary>
            <div className="module-detail">
              <p>{module.detail}</p>
              <dl>
                <div>
                  <dt>Source</dt>
                  <dd>{module.sourceLabel}</dd>
                </div>
                <div>
                  <dt>Spec</dt>
                  <dd>{module.specRefs.join(", ")}</dd>
                </div>
                <div>
                  <dt>Depends on</dt>
                  <dd>{module.dependencies.length ? module.dependencies.join(", ") : "None"}</dd>
                </div>
              </dl>
            </div>
          </details>
        );
      })}
    </div>
  );
}
