import { evidenceById } from "../../lib/situational-awareness/mock-workstation-data";
import { RiskBadge, StatusChip } from "../workstation";

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
        <RiskBadge key={flag} label={flag} />
      ))}
    </div>
  );
}

export function AdvisoryPill({ label }: { label: string }) {
  return <StatusChip label={label.replaceAll("_", " ")} tone="positive" />;
}
