import { AppShell } from "../../../components/app-shell";
import { AdvisoryPill, RiskFlags } from "../../../components/daily-cockpit/evidence-pills";
import {
  AdvisoryTable,
  EmptyState,
  EvidenceDrawer,
  MetricTile,
  SectionCard,
  StatusChip,
} from "../../../components/workstation";
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

function sourceLinks(items: WorkbenchItem[]) {
  const seen = new Set<string>();
  const links: Array<{ url?: string; label?: string; evidence_ids?: string[] }> = [];
  for (const link of items.flatMap((item) => item.source_links ?? [])) {
    if (!link.url || seen.has(link.url)) {
      continue;
    }
    seen.add(link.url);
    links.push(link);
  }
  return links;
}

function evidenceRefs(items: WorkbenchItem[]) {
  return items.flatMap((item) => item.evidence_refs ?? []);
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
    return <EmptyState title="No theme-grouped ticker intelligence has been published yet." />;
  }
  return theme_groups.map((theme) => (
    <SectionCard
      badge={<AdvisoryPill label={theme.advisory_stance?.action ?? "unrated"} />}
      eyebrow="Themes"
      key={theme.theme_id}
      title={theme.theme_label}
    >
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
    </SectionCard>
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
  const allEvidenceIds = Array.from(
    new Set([
      ...theme_groups.flatMap((theme) => theme.evidence_ids),
      ...evidenceIds([
        ...(payload.source_signals ?? []),
        ...(payload.market_events ?? []),
        ...(payload.equity_impact_assessments ?? []),
        ...(payload.trading_advisories ?? []),
      ]),
    ]),
  ).slice(0, 8);
  const allWorkbenchItems = [
    ...(payload.source_signals ?? []),
    ...(payload.market_events ?? []),
    ...(payload.equity_impact_assessments ?? []),
    ...(payload.trading_advisories ?? []),
    ...theme_groups.flatMap((theme) => [
      ...(theme.source_signals ?? []),
      ...(theme.market_events ?? []),
      ...(theme.impact_assessments ?? []),
      ...(theme.llm_notes ?? []),
    ]),
  ];
  const allSourceLinks = sourceLinks(allWorkbenchItems);
  const allEvidenceRefs = evidenceRefs(allWorkbenchItems);
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
          <SectionCard
            badge={<AdvisoryPill label="review" />}
            eyebrow="Degraded / empty state"
            title={`No validated evidence for ${symbol}`}
          >
            <p className="panel-note">
              {payload.detail ??
                "The live read model has no validated evidence-linked ticker theme groups yet."}
            </p>
          </SectionCard>
        ) : null}
        <div className="workstation-grid workstation-grid-2">
          <SectionCard
            badge={
              <AdvisoryPill
                label={primaryGroup?.advisory_stance?.action ?? "unrated"}
              />
            }
            eyebrow="Summary"
            id="summary"
            title={company}
          >
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
          </SectionCard>

          <SectionCard
            badge={<StatusChip label={payload.status ?? "unknown"} tone="neutral" />}
            eyebrow="Internal rating"
            title="Theme-aware advisory state"
          >
            <div className="summary-strip summary-strip-3">
              <MetricTile
                label="Action"
                value={primaryGroup?.advisory_stance?.action ?? "unrated"}
              />
              <MetricTile
                label="Tone"
                value={primaryGroup?.advisory_stance?.tone ?? "neutral"}
                tone="review"
              />
              <MetricTile
                label="Updated"
                value={formatTimestamp(primaryGroup?.latest_available_at)}
              />
            </div>
            <p className="wave2-muted">
              Ratings are internal advisory labels derived from persisted
              evidence, advisory, and readiness records. They are advisory
              review labels only.
            </p>
            {degradedTickerWorkbench ? (
              <p className="wave2-muted">Backend fallback is active.</p>
            ) : null}
          </SectionCard>
        </div>

        <div className="workstation-grid workstation-grid-2" id="themes">
          {displayThemeGroups(theme_groups)}
        </div>

        <div className="workstation-grid workstation-grid-3">
          <SectionCard eyebrow="News by theme" id="news-events" title="News / Events">
            <AdvisoryTable
              columns={["Event", "Relevance", "Source", "Freshness"]}
              rows={(primaryGroup?.market_events ?? payload.market_events ?? [])
                .slice(0, 5)
                .map((event, index) => ({
                  id: String(event.event_id ?? index),
                  cells: [
                    itemText(event, ["catalyst", "event_type"], "Market event"),
                    itemText(event, ["ai_relevance"], "No relevance note"),
                    sourceLinks([event]).length > 0 ? (
                      <a
                        className="source-inline-link"
                        href={sourceLinks([event])[0].url}
                        key="source"
                        rel="noreferrer"
                        target="_blank"
                      >
                        {sourceLinks([event])[0].label || "review source"}
                      </a>
                    ) : (
                      "source link unavailable"
                    ),
                    formatTimestamp(event.available_at),
                  ],
                }))}
            />
          </SectionCard>

          <SectionCard eyebrow="Analyst notes" id="notes" title="Notes">
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
          </SectionCard>

          <SectionCard eyebrow="Related tickers" id="related-tickers" title="Related Tickers">
            <div className="wave2-list">
              {(primaryGroup?.related_tickers ?? []).slice(0, 8).map((related) => (
                <div key={`${related.ticker}-${related.relationship_type}`}>
                  <strong>{relatedLabel(related)}</strong>
                  <span>{related.reason}</span>
                </div>
              ))}
            </div>
          </SectionCard>
        </div>

        <div className="workstation-grid workstation-grid-3">
          <SectionCard eyebrow="Risks" id="risks" title="Risk watch">
            <RiskFlags flags={primaryGroup?.risk_flags ?? []} />
            <div className="wave2-list">
              {(primaryGroup?.next_watch_items ?? []).slice(0, 5).map((item) => (
                <div key={item}>
                  <strong>Watch item</strong>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard eyebrow="Valuation" title="Price target scenarios">
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
          </SectionCard>

          <SectionCard eyebrow="Planning" title="Entry / add / invalidation levels">
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
          </SectionCard>
        </div>

        <SectionCard
          badge={<StatusChip label="Advisory-only" tone="neutral" />}
          eyebrow="Evidence"
          id="evidence"
          title="Evidence trail"
        >
          <EvidenceDrawer
            ids={allEvidenceIds}
            links={allSourceLinks}
            refs={allEvidenceRefs}
          />
          <p className="wave2-muted">
            LLM analyst critique can explain and review cited evidence, but
            deterministic modules own scores, risk, constraints, and target
            weights.
          </p>
        </SectionCard>
      </AppShell>
    </div>
  );
}
