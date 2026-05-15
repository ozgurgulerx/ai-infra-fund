"use client";

import { useMemo, useState } from "react";

import { AppShell } from "../../components/app-shell";
import { SectionPanel } from "../../components/section-panel";
import {
  adjacentStations,
  valueChain,
  type ValueChainStation,
} from "../../lib/value-chain";
import {
  tickersByStation,
  watchlist,
  type WatchlistEntry,
} from "../../lib/watchlist-mirror";

type PriorityKey = WatchlistEntry["priority"];

const priorityRank: Record<PriorityKey, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export default function ThemesPage() {
  const [activeId, setActiveId] = useState<string>(nameKey(valueChain[0]));

  const activeStation = useMemo<ValueChainStation>(() => {
    const all = [...valueChain, ...adjacentStations];
    return all.find((s) => nameKey(s) === activeId) ?? valueChain[0];
  }, [activeId]);

  const stationKey = nameKey(activeStation);

  const stationTickers = useMemo(() => {
    const tags = new Set(activeStation.subthemes.map((s) => s.tag));
    return tickersByStation(tags).sort(
      (a, b) => priorityRank[a.priority] - priorityRank[b.priority],
    );
  }, [activeStation]);

  const subthemeCounts = useMemo(() => {
    const tags = new Set(activeStation.subthemes.map((s) => s.tag));
    const counts = new Map<string, WatchlistEntry[]>();
    for (const tag of tags) {
      counts.set(
        tag,
        watchlist.filter((entry) => entry.themes.includes(tag)),
      );
    }
    return counts;
  }, [activeStation]);

  const criticalCount = stationTickers.filter(
    (t) => t.priority === "critical",
  ).length;

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Value-chain Atlas"
        title="AI Infrastructure Value Chain"
      >
        <div className="workbench-grid">
          <SectionPanel
            eyebrow="Read-only"
            title="Compute supply chain spine"
            aside={<span className="advisory-inline">Advisory-only</span>}
          >
            <p className="panel-note">
              Compute does not exist without memory, foundries, lithography,
              gigawatts of power, transmission, switchgear, and cooling. Each
              station below routes the current that ends in a training run. Pick
              a station to inspect its subthemes and the equities that ride
              them.
            </p>

            <div
              className="value-chain-spine"
              role="tablist"
              aria-label="Primary value-chain stations"
            >
              {valueChain.map((station) => {
                const tags = new Set(station.subthemes.map((s) => s.tag));
                const equityCount = tickersByStation(tags).length;
                const isActive = nameKey(station) === stationKey;
                return (
                  <button
                    key={station.label}
                    type="button"
                    role="tab"
                    aria-selected={isActive}
                    onClick={() => setActiveId(nameKey(station))}
                    className={`value-chain-station${
                      isActive ? " value-chain-station--active" : ""
                    }`}
                  >
                    <strong>
                      {station.index}. {station.label}
                    </strong>
                    <span style={{ color: "var(--muted)", fontSize: 12 }}>
                      {equityCount} equities · {station.caption}
                    </span>
                  </button>
                );
              })}
            </div>

            <div
              className="value-chain-spine"
              style={{ marginTop: 12 }}
              role="tablist"
              aria-label="Adjacent value-chain stations"
            >
              {adjacentStations.map((station) => {
                const isActive = nameKey(station) === stationKey;
                return (
                  <button
                    key={station.label}
                    type="button"
                    role="tab"
                    aria-selected={isActive}
                    onClick={() => setActiveId(nameKey(station))}
                    className={`value-chain-station${
                      isActive ? " value-chain-station--active" : ""
                    }`}
                  >
                    <strong>Adjacent · {station.label}</strong>
                    <span style={{ color: "var(--muted)", fontSize: 12 }}>
                      {station.caption}
                    </span>
                  </button>
                );
              })}
            </div>
          </SectionPanel>

          <SectionPanel
            eyebrow={`Station ${activeStation.index}`}
            title={activeStation.label}
            aside={<span className="advisory-inline">Advisory-only</span>}
          >
            <p className="panel-note">{activeStation.caption}</p>

            <dl className="metric-grid">
              <div className="metric-card">
                <dt>Subthemes</dt>
                <dd>{activeStation.subthemes.length}</dd>
              </div>
              <div className="metric-card">
                <dt>Equities</dt>
                <dd>{stationTickers.length}</dd>
              </div>
              <div className="metric-card">
                <dt>Critical</dt>
                <dd>{criticalCount}</dd>
              </div>
            </dl>

            <h3 style={{ marginTop: 16, marginBottom: 8 }}>Subthemes</h3>
            <div className="value-chain-subthemes">
              {activeStation.subthemes.map((sub) => {
                const entries = subthemeCounts.get(sub.tag) ?? [];
                return (
                  <div className="value-chain-subtheme" key={sub.tag}>
                    <strong>{sub.label}</strong>
                    <span>{sub.short}</span>
                    <span style={{ color: "var(--muted)", fontSize: 11 }}>
                      tag: {sub.tag}
                    </span>
                    <span style={{ marginTop: 6 }}>
                      {entries.length === 0
                        ? "— no equities mapped"
                        : entries.map((e) => e.ticker).join(" · ")}
                    </span>
                  </div>
                );
              })}
            </div>
          </SectionPanel>

          <SectionPanel
            eyebrow="Tickers"
            title="Equities at this station"
            aside={<span className="advisory-inline">Advisory-only</span>}
          >
            <div
              className="data-table data-table-four"
              role="table"
              aria-label="Equities at the active station"
            >
              <div role="row" className="data-row data-header">
                <span>Symbol</span>
                <span>Company</span>
                <span>Priority</span>
                <span>Themes</span>
              </div>
              {stationTickers.map((entry) => (
                <div role="row" className="data-row" key={entry.ticker}>
                  <span>{entry.ticker}</span>
                  <span>{entry.companyName}</span>
                  <span>{entry.priority}</span>
                  <span>
                    {entry.themes
                      .filter((t) =>
                        activeStation.subthemes.some((s) => s.tag === t),
                      )
                      .join(" / ")}
                  </span>
                </div>
              ))}
              {stationTickers.length === 0 ? (
                <div role="row" className="data-empty-state">
                  No equities mapped to this station yet.
                </div>
              ) : null}
            </div>
            <p className="panel-note">
              Source: config/ai_equity_watchlist.yaml · taxonomy:
              lib/value-chain.ts. Read-only — no order, broker, or execution
              control.
            </p>
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}

function nameKey(station: ValueChainStation): string {
  return `${station.id}-${station.label.toLowerCase().replace(/[^a-z]/g, "-")}`;
}
