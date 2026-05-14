import { AppShell } from "../../../components/app-shell";
import { SectionPanel } from "../../../components/section-panel";
import { tickerSignals } from "../../../lib/portfolio-data";

type TickerPageProps = {
  params: Promise<{ ticker: string }>;
};

export default async function TickerPage({ params }: TickerPageProps) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();

  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Ticker" title="Ticker Workbench">
        <div className="workbench-grid">
          <SectionPanel eyebrow={symbol} title="Ticker Workbench" aside={<span className="advisory-inline">Advisory-only</span>}>
            <div className="status-list">
              {tickerSignals.map((signal) => (
                <div className="status-list-row" key={signal.label}>
                  <strong>{signal.label}</strong>
                  <span>{signal.value}</span>
                  <span>{signal.source}</span>
                </div>
              ))}
            </div>
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
