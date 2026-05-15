import { AppShell } from "../components/app-shell";
import { HeroKpiStrip } from "../components/hero-kpi-strip";
import { SentimentTile } from "../components/sentiment-tile";
import { NewsTile } from "../components/news-tile";
import { PortfolioTile } from "../components/portfolio-tile";
import { ActionsTile } from "../components/actions-tile";

export default function DailyBriefPage() {
  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Daily Brief"
        title="Market sentiment, news, portfolio, and suggested actions"
      >
        <HeroKpiStrip />
        <div className="daily-brief-grid">
          <SentimentTile />
          <NewsTile />
          <PortfolioTile />
          <ActionsTile />
        </div>
      </AppShell>
    </div>
  );
}
