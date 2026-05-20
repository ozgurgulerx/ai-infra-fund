import type { CSSProperties, ReactNode } from "react";

type Tone =
  | "neutral"
  | "positive"
  | "cautious"
  | "negative"
  | "mixed"
  | "review"
  | "fresh"
  | "stale";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  subtitle?: string;
  children?: ReactNode;
};

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  children,
}: PageHeaderProps) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {children ? <div className="page-header-actions">{children}</div> : null}
    </header>
  );
}

type MetricTileProps = {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: Tone;
};

export function MetricTile({
  label,
  value,
  detail,
  tone = "neutral",
}: MetricTileProps) {
  return (
    <div className={`metric-tile metric-tile-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

export function StatusChip({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: Tone;
}) {
  return <span className={`status-chip status-chip-${tone}`}>{label}</span>;
}

export function RiskBadge({ label }: { label: string }) {
  return <span className="risk-badge">{label.replaceAll("_", " ")}</span>;
}

export function LlmReviewBadge({
  status,
}: {
  status: "fallback" | "review_required" | "rejected" | "available" | string;
}) {
  const tone =
    status === "available"
      ? "fresh"
      : status === "rejected"
        ? "negative"
        : status === "fallback"
          ? "cautious"
          : "review";
  return <StatusChip label={`LLM ${status.replaceAll("_", " ")}`} tone={tone} />;
}

type AdvisoryTableProps = {
  columns: string[];
  rows: Array<{ id: string; cells: ReactNode[] }>;
  emptyLabel?: string;
  density?: "normal" | "compact";
};

export function AdvisoryTable({
  columns,
  rows,
  emptyLabel = "No records available.",
  density = "normal",
}: AdvisoryTableProps) {
  const gridStyle: CSSProperties = {
    gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))`,
  };

  if (rows.length === 0) {
    return <EmptyState title={emptyLabel} />;
  }

  return (
    <div className={`advisory-table advisory-table-${density}`}>
      <div className="advisory-table-row advisory-table-header" style={gridStyle}>
        {columns.map((column) => (
          <span key={column}>{column}</span>
        ))}
      </div>
      {rows.map((row) => (
        <div className="advisory-table-row" key={row.id} style={gridStyle}>
          {row.cells.map((cell, index) => (
            <span key={`${row.id}-${columns[index] ?? index}`}>{cell}</span>
          ))}
        </div>
      ))}
    </div>
  );
}

type EvidenceDrawerProps = {
  ids: string[];
  refs?: Array<{
    evidence_id?: string;
    title?: string | null;
    summary?: string | null;
    source_links?: Array<{ url?: string; label?: string; evidence_ids?: string[] }>;
  }>;
  links?: Array<{ url?: string; label?: string; evidence_ids?: string[] }>;
  title?: string;
  caption?: string;
};

export function EvidenceDrawer({
  ids,
  refs = [],
  links = [],
  title = "Evidence and audit trail",
  caption = "Evidence IDs are available for audit review and hidden from the main analyst viewport by default.",
}: EvidenceDrawerProps) {
  const uniqueIds = Array.from(new Set(ids.filter(Boolean)));
  const linkedRefs = refs.filter((ref) => ref.evidence_id);
  const sourceLinks = dedupeLinks([
    ...links,
    ...linkedRefs.flatMap((ref) => ref.source_links ?? []),
  ]);

  return (
    <details className="evidence-drawer">
      <summary>
        <span>{title}</span>
        <strong>{uniqueIds.length} refs</strong>
      </summary>
      <p>{caption}</p>
      {sourceLinks.length > 0 ? (
        <div className="source-link-list">
          {sourceLinks.map((link) => (
            <a
              className="source-link"
              href={link.url}
              key={link.url}
              rel="noreferrer"
              target="_blank"
            >
              <span>{link.label || "Review source"}</span>
              <small>{link.url}</small>
            </a>
          ))}
        </div>
      ) : null}
      {linkedRefs.length > 0 ? (
        <div className="evidence-ref-list">
          {linkedRefs.map((ref) => (
            <article className="evidence-ref" key={ref.evidence_id}>
              <code>{ref.evidence_id}</code>
              {ref.title ? <strong>{ref.title}</strong> : null}
              {ref.summary ? <span>{ref.summary}</span> : null}
            </article>
          ))}
        </div>
      ) : uniqueIds.length > 0 ? (
        <div className="evidence-drawer-grid">
          {uniqueIds.map((id) => (
            <code key={id}>{id}</code>
          ))}
        </div>
      ) : (
        <EmptyState title="No evidence IDs linked yet." />
      )}
    </details>
  );
}

function dedupeLinks(
  links: Array<{ url?: string; label?: string; evidence_ids?: string[] }>,
) {
  const seen = new Set<string>();
  const result: Array<{ url?: string; label?: string; evidence_ids?: string[] }> = [];
  for (const link of links) {
    if (!link.url || seen.has(link.url)) {
      continue;
    }
    seen.add(link.url);
    result.push(link);
  }
  return result;
}

type SectionCardProps = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  badge?: ReactNode;
  children: ReactNode;
  id?: string;
};

export function SectionCard({
  eyebrow,
  title,
  subtitle,
  badge,
  children,
  id,
}: SectionCardProps) {
  return (
    <section className="section-card" id={id}>
      <div className="section-card-heading">
        <div>
          {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {badge ? <div className="section-card-badge">{badge}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail?: string;
}) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}
