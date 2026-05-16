import { evidenceById } from "../../lib/situational-awareness/mock-workstation-data";

export function EvidencePills({ ids }: { ids: string[] }) {
  return (
    <div className="wave2-evidence-list">
      {ids.map((id) => {
        const evidence = evidenceById(id);
        return (
          <span className="wave2-evidence-pill" key={id} title={evidence?.title ?? id}>
            {id}
          </span>
        );
      })}
    </div>
  );
}

export function RiskFlags({ flags }: { flags: string[] }) {
  return (
    <div className="wave2-chip-row">
      {flags.map((flag) => (
        <span className="wave2-risk-chip" key={flag}>
          {flag.replaceAll("_", " ")}
        </span>
      ))}
    </div>
  );
}

export function AdvisoryPill({ label }: { label: string }) {
  return <span className="wave2-advisory-pill">{label.replaceAll("_", " ")}</span>;
}
