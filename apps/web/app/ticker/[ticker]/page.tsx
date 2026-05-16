import { AppShell } from "../../../components/app-shell";
import {
  AdvisoryPill,
  EvidencePills,
  RiskFlags,
} from "../../../components/daily-cockpit/evidence-pills";
import {
  assessmentForTicker,
  levelsForTicker,
  marketEventsForTicker,
  mockWorkstationData,
  portfolioExposureForTicker,
  priceScenarioForTicker,
  tradePlansForTicker,
} from "../../../lib/situational-awareness/mock-workstation-data";

type TickerPageProps = {
  params: Promise<{ ticker: string }>;
};

export default async function TickerPage({ params }: TickerPageProps) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();
  const assessment = assessmentForTicker(symbol) ?? mockWorkstationData.equityAssessments[0];
  const events = marketEventsForTicker(symbol);
  const scenario = priceScenarioForTicker(symbol);
  const levels = levelsForTicker(symbol);
  const plans = tradePlansForTicker(symbol);
  const exposure = portfolioExposureForTicker(symbol);
  const relatedTickers = Array.from(
    new Set(
      mockWorkstationData.segmentImpacts
        .filter((segment) =>
          [...segment.firstOrderBeneficiaries, ...segment.secondOrderBeneficiaries].includes(symbol),
        )
        .flatMap((segment) => [
          ...segment.firstOrderBeneficiaries,
          ...segment.secondOrderBeneficiaries,
        ])
        .filter((item) => item !== symbol),
    ),
  ).slice(0, 8);

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow={symbol}
        title="Ticker Analyst Workbench"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <div className="wave2-grid wave2-grid-2">
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Current thesis</p>
                <h2>{assessment.company}</h2>
              </div>
              <AdvisoryPill label={assessment.advisoryImplication} />
            </div>
            <p className="wave2-lede">{assessment.currentThesis}</p>
            <div className="wave2-chip-row">
              {assessment.segmentExposure.map((segment) => (
                <span className="wave2-chip" key={segment}>
                  {segment}
                </span>
              ))}
            </div>
            <RiskFlags flags={assessment.riskFlags} />
            <div className="wave2-invalidation">
              <strong>Invalidation</strong>
              <span>{assessment.invalidationCondition}</span>
            </div>
            <EvidencePills ids={assessment.evidenceIds} />
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Portfolio exposure</p>
                <h2>Position and related tickers</h2>
              </div>
            </div>
            <div className="wave2-metric-grid">
              <div>
                <span>Current weight</span>
                <strong>{exposure?.weight ?? "not held"}</strong>
              </div>
              <div>
                <span>Primary segment</span>
                <strong>{exposure?.segment ?? assessment.segmentExposure[0]}</strong>
              </div>
              <div>
                <span>Related tickers</span>
                <strong>{relatedTickers.join(", ") || "None"}</strong>
              </div>
            </div>
          </section>
        </div>

        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Recent MarketEvents</p>
              <h2>Evidence-backed catalyst trail</h2>
            </div>
          </div>
          <div className="wave2-card-grid">
            {events.map((event) => (
              <article className="wave2-card" key={event.eventId}>
                <div className="wave2-card-kicker">
                  <span>{event.eventType.replaceAll("_", " ")}</span>
                  <strong>{event.direction}</strong>
                </div>
                <h3>{event.catalyst}</h3>
                <p>{event.aiRelevance}</p>
                <EvidencePills ids={event.evidenceIds} />
              </article>
            ))}
          </div>
        </section>

        <div className="wave2-grid wave2-grid-2">
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Bull case / bear case</p>
                <h2>Thesis range</h2>
              </div>
            </div>
            <div className="wave2-case-grid">
              <span>Bull case</span>
              <p>{assessment.bullCase}</p>
              <span>Base case</span>
              <p>{assessment.baseCase}</p>
              <span>Bear case</span>
              <p>{assessment.bearCase}</p>
            </div>
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Price target scenarios</p>
                <h2>Scenarios, not predictions</h2>
              </div>
            </div>
            {scenario ? (
              <div className="wave2-scenario-row">
                <div><span>Bear</span><strong>{scenario.bear}</strong></div>
                <div><span>Base</span><strong>{scenario.base}</strong></div>
                <div><span>Bull</span><strong>{scenario.bull}</strong></div>
                <p>{scenario.invalidationCondition}</p>
                <EvidencePills ids={scenario.evidenceIds} />
              </div>
            ) : (
              <p className="panel-note">No static scenario is available for {symbol}.</p>
            )}
          </section>
        </div>

        <div className="wave2-grid wave2-grid-2">
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Entry / add / invalidation levels</p>
                <h2>Planning notes only</h2>
              </div>
            </div>
            {levels ? (
              <div className="wave2-metric-grid">
                <div><span>Entry zone</span><strong>{levels.entryZone}</strong></div>
                <div><span>Add zone</span><strong>{levels.addZone}</strong></div>
                <div><span>Trim zone</span><strong>{levels.trimZone}</strong></div>
              </div>
            ) : (
              <p className="panel-note">No planning levels are available for {symbol}.</p>
            )}
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">LLM analyst critique</p>
                <h2>Review notes and trade history summary</h2>
              </div>
            </div>
            <div className="wave2-stack">
              {plans.map((plan) => (
                <article className="wave2-list-card" key={plan.tradePlanId}>
                  <strong>{plan.tradePlanId}</strong>
                  <p>{plan.llmCritique}</p>
                  <span>{plan.portfolioImpact}</span>
                  <EvidencePills ids={plan.evidenceIds} />
                </article>
              ))}
              <p className="panel-note">
                Trade history summary if available: local journal entries remain manual and advisory-only.
              </p>
            </div>
          </section>
        </div>
      </AppShell>
    </div>
  );
}
