import { STATUS_TONE_MAP, type ModuleStatus } from "../lib/status-model";

type StatusTileProps = {
  title: string;
  status: ModuleStatus;
  source: string;
  detail: string;
  metric?: string;
};

export function StatusTile({ title, status, source, detail, metric }: StatusTileProps) {
  const tone = STATUS_TONE_MAP[status];

  return (
    <article className={`status-tile ${tone.cssClass}`}>
      <div className="status-tile-header">
        <h3>
          <span className="status-beacon" aria-hidden="true" />
          {title}
        </h3>
        <span className="status-pill">{tone.label}</span>
      </div>
      {metric ? <p className="status-metric">{metric}</p> : null}
      <p className="status-detail">{detail}</p>
      <p className="status-source">{source}</p>
    </article>
  );
}
