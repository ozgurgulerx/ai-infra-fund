/**
 * Transparency primitives — visual affordances for Google PAIR + Microsoft HAX.
 *
 *   ConfidenceBar  → PAIR G2:  make clear HOW WELL the system can do what it does.
 *   ProvenancePill → HAX G11:  make clear WHY the system did what it did.
 *   AdvisoryStamp  → HAX G1:   make clear WHAT the system can do (advisory only).
 *
 * Use these wherever a model-derived value, recommendation, or claim is shown.
 * They are deliberately small so they can be inlined inside table cells,
 * metric details, and section headings without disrupting the grid.
 */

type ConfidenceTone = "neutral" | "positive" | "warn" | "negative";

type ConfidenceBarProps = {
  /** value in [0, 1] */
  value: number;
  /** number of segments rendered; 5 reads as a 5-bar glyph */
  segments?: number;
  tone?: ConfidenceTone;
  /** screen-reader label; defaults to a percentage */
  label?: string;
};

export function ConfidenceBar({
  value,
  segments = 5,
  tone = "neutral",
  label,
}: ConfidenceBarProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const lit = Math.round(clamped * segments);
  const a11y = label ?? `confidence ${Math.round(clamped * 100)} percent`;
  return (
    <span
      className="confidence-bar"
      data-tone={tone}
      role="img"
      aria-label={a11y}
      title={a11y}
    >
      {Array.from({ length: segments }, (_, i) => (
        <i key={i} className={i < lit ? "on" : undefined} aria-hidden="true" />
      ))}
    </span>
  );
}

type ProvenancePillProps = {
  /** source slug rendered as the visible label, e.g. "SEC", "yf", "FRED" */
  source: string;
  /** optional evidence-id or ref pointer (e.g. "E-2026-0517-0042"); used in title only */
  ref?: string;
  /** optional count appended after a middle dot — "SEC·3" */
  count?: number;
};

export function ProvenancePill({ source, ref, count }: ProvenancePillProps) {
  const title = ref ? `${source} · ${ref}` : source;
  return (
    <span className="provenance-pill" title={title}>
      {count != null ? `${source}·${count}` : source}
    </span>
  );
}

type AdvisoryStampProps = {
  /** label shown after the dot; defaults to "Advisory only" */
  label?: string;
};

/**
 * Persistent "advisory only" indicator. Use once in the global chrome so
 * users never lose sight of the system's bounded capability (HAX G1).
 */
export function AdvisoryStamp({ label = "Advisory only" }: AdvisoryStampProps) {
  return (
    <span className="advisory-badge" aria-label={label}>
      {label}
    </span>
  );
}
