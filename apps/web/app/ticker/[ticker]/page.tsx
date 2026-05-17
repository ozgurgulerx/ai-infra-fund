import { AppShell } from "../../../components/app-shell";
import {
  AdvisoryPill,
  EvidencePills,
  RiskFlags,
} from "../../../components/daily-cockpit/evidence-pills";
import {
  readTickerWorkbenchPayload,
  type RelatedTicker,
  type ThemeGroup,
  type TickerWorkbenchPayload,
  type WorkbenchItem,
} from "../../../lib/advisory/ticker-workbench";

export const dynamic = "force-dynamic";

type TickerPageProps = {
  params: Promise<{ ticker: string }>;
};

const TAB_LINKS = [
  ["summary", "Summary"],
  ["themes", "Themes"],
  ["news-events", "News / Events"],
  ["notes", "Notes"],
  ["related-tickers", "Related Tickers"],
  ["risks", "Risks"],
  ["evidence", "Evidence"],
] as const;

function valueText(value: unknown, fallback = "Unavailable"): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function itemText(
  item: WorkbenchItem | undefined,
  keys: string[],
  fallback: string,
): string {
  if (!item) {
    return fallback;
  }
  for (const key of keys) {
    const value = item[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return fallback;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.length > 0);
}

function formatTimestamp(value: unknown): string {
  if (typeof value !== "string" || !value) {
    return "No timestamp";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date);
}

function evidenceIds(items: WorkbenchItem[]): string[] {
  return Array.from(
    new Set(items.flatMap((item) => stringList(item.evidence_ids))),
  ).slice(0, 8);
}

function primaryCompany(payload: TickerWorkbenchPayload, symbol: string): string {
  const assessment = payload.equity_impact_assessments?.[0];
  return itemText(assessment, ["company"], symbol);
}

function primaryThesis(payload: TickerWorkbenchPayload, symbol: string): string {
  const advisory = payload.trading_advisories?.[0];
  const assessment = payload.equity_impact_assessments?.[0];
  return (
    itemText(advisory, ["advisory_summary"], "") ||
    itemText(assessment, ["assessment"], `${symbol} has no API-backed thesis yet.`)
  );
}

function firstTheme(payload: TickerWorkbenchPayload): ThemeGroup | undefined {
  return payload.theme_groups?.[0];
}

function relatedLabel(item: RelatedTicker): string {
  return `${item.ticker} · ${item.relationship_type}`;
}

function displayThemeGroups(theme_groups: ThemeGroup[]) {
  if (theme_groups.length === 0) {
    return (
      <div className="wave2-empty-state">
        No theme-grouped ticker intelligence has been published yet.
      </div>
    );
  }
  return theme_groups.map((theme) => (
    <section className="section-panel" key={theme.theme_id}>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Themes</p>
          <h2>{theme.theme_label}</h2>
        </div>
        <AdvisoryPill label={theme.advisory_stance?.action ?? "unrated"} />
      </div>
      <div className="wave2-metric-grid">
        <div>
          <span>Internal rating</span>
          <strong>{theme.advisory_stance?.action ?? "unrated"}</strong>
        </div>
        <div>
          <span>Freshness</span>
          <strong>{theme.advisory_stance?.freshness ?? "unknown"}</strong>
        </div>
        <div>
          <span>Confidence</span>
          <strong>{theme.advisory_stance?.confidence ?? "review"}</strong>
        </div>
      </div>
      <div className="wave2-list">
        <div>
          <strong>Why now</strong>
          <span>{theme.why_now}</span>
        </div>
        <div>
          <strong>What changed</strong>
          <span>{theme.what_changed}</span>
        </div>
        <div>
          <strong>readiness / suppression</strong>
          <span>
            {theme.advisory_stance?.freshness === "suppressed"
              ? "suppression active until stale or blocked inputs are cleared"
              : "readiness depends on current evidence, checks, and manual review"}
          </span>
        </div>
      </div>
      <EvidencePills ids={theme.evidence_ids} />
    </section>
  ));
}

export default async function TickerPage({ params }: TickerPageProps) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();
  const payload = await readTickerWorkbenchPayload(symbol);
  const theme_groups = payload.theme_groups ?? [];
  const primaryGroup = firstTheme(payload);
  const company = primaryCompany(payload, symbol);
  const degradedTickerWorkbench = payload.status === "degraded";
  const valuation = payload.valuation_contexts?.[0];
  const plan = payload.trade_plans?.[0];
  const allEvidenceIds = primaryGroup?.evidence_ids ?? evidenceIds([
    ...(payload.source_signals ?? []),
    ...(payload.market_events ?? []),
    ...(payload.equity_impact_assessments ?? []),
    ...(payload.trading_advisories ?? []),
  ]);
  const hasValidatedEvidence =
    payload.status === "available" && theme_groups.length > 0 && allEvidenceIds.length > 0;

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow={symbol}
        title="Ticker Analyst Workbench"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        {payload.is_fixture_fallback ? (
          <div className="readonly-label">Fixture/demo data</div>
        ) : null}
        <nav className="wave2-chip-row" aria-label="Ticker workbench tabs">
          {TAB_LINKS.map(([id, label]) => (
            <a className="wave2-chip" href={`#${id}`} key={id}>
              {label}
            </a>
          ))}
        </nav>
        {!hasValidatedEvidence ? (
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Degraded / empty state</p>
                <h2>No validated evidence for {symbol}</h2>
              </div>
              <AdvisoryPill label="review" />
            </div>
            <p className="panel-note">
              {payload.detail ??
                "The live read model has no validated evidence-linked ticker theme groups yet."}
            </p>
          </section>
        ) : null}
        <div className="wave2-grid wave2-grid-2">
          <section className="section-panel" id="summary">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Summary</p>
                <h2>{company}</h2>
              </div>
              <AdvisoryPill
                label={primaryGroup?.advisory_stance?.action ?? "unrated"}
              />
            </div>
            <p className="wave2-lede">{primaryThesis(payload, symbol)}</p>
            <div className="wave2-chip-row">
              {theme_groups.slice(0, 6).map((theme) => (
                <span className="wave2-chip" key={theme.theme_id}>
                  {theme.theme_label}
                </span>
              ))}
            </div>
            <RiskFlags flags={primaryGroup?.risk_flags ?? []} />
            <div className="wave2-invalidation">
              <strong>Invalidation</strong>
              <span>
                {valueText(
                  primaryGroup?.invalidation,
                  "No invalidation condition has been linked to this ticker.",
                )}
              </span>
            </div>
            <EvidencePills ids={allEvidenceIds} />
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Internal rating</p>
                <h2>Theme-aware advisory state</h2>
              </div>
              <span className="readonly-label">{payload.status ?? "unknown"}</span>
            </div>
            <div className="wave2-metric-grid">
              <div>
                <span>Action</span>
                <strong>{primaryGroup?.advisory_stance?.action ?? "unrated"}</strong>
              </div>
              <div>
                <span>Tone</span>
                <strong>{primaryGroup?.advisory_stance?.tone ?? "neutral"}</strong>
              </div>
              <div>
                <span>Updated</span>
                <strong>{formatTimestamp(primaryGroup?.latest_available_at)}</strong>
              </div>
            </div>
            <p className="wave2-muted">
              Ratings are internal advisory labels derived from persisted
              evidence, advisory, and readiness records. They are advisory
              review labels only.
            </p>
            {degradedTickerWorkbench ? (
              <p className="wave2-muted">Backend fallback is active.</p>
            ) : null}
          </section>
        </div>

        <div className="wave2-grid wave2-grid-2" id="themes">
          {displayThemeGroups(theme_groups)}
        </div>

        <div className="wave2-grid wave2-grid-3">
          <section className="section-panel" id="news-events">
            <div className="section-heading">
              <div>
                <p className="eyebrow">News by theme</p>
                <h2>News / Events</h2>
              </div>
            </div>
            <div className="wave2-list">
              {(primaryGroup?.market_events ?? payload.market_events ?? [])
                .slice(0, 5)
                .map((event, index) => (
                  <div key={String(event.event_id ?? index)}>
                    <strong>{itemText(event, ["catalyst", "event_type"], "Market event")}</strong>
                    <span>
                      {itemText(event, ["ai_relevance"], "No relevance note")} ·{" "}
                      {formatTimestamp(event.available_at)}
                    </span>
                  </div>
                ))}
            </div>
          </section>

          <section className="section-panel" id="notes">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Analyst notes</p>
                <h2>Notes</h2>
              </div>
            </div>
            <div className="wave2-list">
              {(primaryGroup?.llm_notes ?? payload.llm_analyst_notes ?? [])
                .slice(0, 4)
                .map((note, index) => (
                  <div key={String(note.note_id ?? index)}>
                    <strong>{itemText(note, ["allowed_role", "scope"], "review note")}</strong>
                    <span>{itemText(note, ["note"], "No note text")}</span>
                  </div>
                ))}
              {(primaryGroup?.trade_plan_notes ?? []).slice(0, 3).map((note, index) => (
                <div key={String(note.trade_plan_id ?? index)}>
                  <strong>Trade plan readiness</strong>
                  <span>{itemText(note, ["readiness"], "review")}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="section-panel" id="related-tickers">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Related tickers</p>
                <h2>Related Tickers</h2>
              </div>
            </div>
            <div className="wave2-list">
              {(primaryGroup?.related_tickers ?? []).slice(0, 8).map((related) => (
                <div key={`${related.ticker}-${related.relationship_type}`}>
                  <strong>{relatedLabel(related)}</strong>
                  <span>{related.reason}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="wave2-grid wave2-grid-3">
          <section className="section-panel" id="risks">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Risks</p>
                <h2>Risk watch</h2>
              </div>
            </div>
            <RiskFlags flags={primaryGroup?.risk_flags ?? []} />
            <div className="wave2-list">
              {(primaryGroup?.next_watch_items ?? []).slice(0, 5).map((item) => (
                <div key={item}>
                  <strong>Watch item</strong>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Valuation</p>
                <h2>Price target scenarios</h2>
              </div>
            </div>
            <div className="wave2-metric-grid">
              <div>
                <span>State</span>
                <strong>{itemText(valuation, ["valuation_state"], "unrated")}</strong>
              </div>
              <div>
                <span>Forward P/E</span>
                <strong>{valueText(valuation?.forward_pe, "n/a")}</strong>
              </div>
              <div>
                <span>EV/Sales</span>
                <strong>{valueText(valuation?.ev_sales, "n/a")}</strong>
              </div>
            </div>
            <p className="wave2-muted">
              Price targets are scenarios for manual planning and review.
            </p>
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Planning</p>
                <h2>Entry / add / invalidation levels</h2>
              </div>
            </div>
            <div className="wave2-list">
              <div>
                <strong>readiness</strong>
                <span>{itemText(plan, ["readiness"], "No trade plan readiness record")}</span>
              </div>
              <div>
                <strong>Manual journal only</strong>
                <span>{plan?.manual_journal_only ? "yes" : "not recorded"}</span>
              </div>
              <div>
                <strong>Bull case / Bear case</strong>
                <span>
                  Use the linked evidence trail and valuation scenarios before
                  entering a manual trade plan.
                </span>
              </div>
            </div>
          </section>
        </div>

        <section className="section-panel" id="evidence">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Evidence</p>
              <h2>Evidence trail</h2>
            </div>
            <span className="readonly-label">Advisory-only</span>
          </div>
          <EvidencePills ids={allEvidenceIds} />
          <p className="wave2-muted">
            LLM analyst critique can explain and review cited evidence, but
            deterministic modules own scores, risk, constraints, and target
            weights.
          </p>
        </section>
      </AppShell>
    </div>
  );
}
