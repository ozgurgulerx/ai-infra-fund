"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
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
import styles from "./themes.module.css";

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

  return (
    <main className={styles.shell}>
      <div className={styles.grain} aria-hidden="true" />
      <div className={styles.frame}>
        <header className={styles.header}>
          <div className={styles.eyebrowRow}>
            <span className={styles.eyebrowMono}>FILE / 04.A</span>
            <span className={styles.eyebrowMono}>
              AI INFRA FUND · VALUE-CHAIN ATLAS
            </span>
            <span className={styles.eyebrowMono}>REV 2026.05</span>
          </div>
          <h1 className={styles.title}>
            The <em>trillion-dollar</em> value chain,
            <br />
            laid out station by station.
          </h1>
          <p className={styles.lede}>
            Compute does not exist without memory, foundries, lithography,
            gigawatts of power, transmission, switchgear, and cooling. Each
            station below routes the current that ends in a training run. Pick a
            station to inspect its subthemes and the equities that ride them.
          </p>
          <div className={styles.headerMeta}>
            <Link href="/" className={styles.backLink}>
              ← Control Room
            </Link>
            <span className={styles.metaDot} />
            <span className={styles.metaMono}>
              {watchlist.length} equities · {valueChain.length} primary stations
              · {adjacentStations.length} adjacent
            </span>
          </div>
        </header>

        <section className={styles.spineSection} aria-label="Value chain spine">
          <div className={styles.spineLabel}>
            <span className={styles.spineLabelMono}>FIG. 1</span>
            <span>Primary value-chain spine — read left to right</span>
          </div>
          <ol className={styles.spine}>
            {valueChain.map((station, index) => {
              const tags = new Set(station.subthemes.map((s) => s.tag));
              const equityCount = tickersByStation(tags).length;
              const isActive = nameKey(station) === stationKey;
              return (
                <li
                  key={station.label}
                  className={`${styles.station} ${isActive ? styles.stationActive : ""}`}
                  style={{ animationDelay: `${index * 70}ms` }}
                >
                  <button
                    type="button"
                    onClick={() => setActiveId(nameKey(station))}
                    className={styles.stationButton}
                    aria-pressed={isActive}
                  >
                    <span className={styles.stationIndex}>{station.index}</span>
                    <span className={styles.stationLabel}>{station.label}</span>
                    <span className={styles.stationCount}>
                      <span className={styles.countNum}>{equityCount}</span>
                      <span className={styles.countLabel}>equities</span>
                    </span>
                    <span className={styles.stationCaption}>
                      {station.caption}
                    </span>
                  </button>
                  {index < valueChain.length - 1 ? (
                    <span className={styles.wire} aria-hidden="true" />
                  ) : null}
                </li>
              );
            })}
          </ol>

          <div className={styles.adjacentRail}>
            <span className={styles.adjacentTitle}>Adjacent</span>
            {adjacentStations.map((station) => {
              const isActive = nameKey(station) === stationKey;
              return (
                <button
                  key={station.label}
                  type="button"
                  onClick={() => setActiveId(nameKey(station))}
                  className={`${styles.adjacentChip} ${
                    isActive ? styles.adjacentChipActive : ""
                  }`}
                  aria-pressed={isActive}
                >
                  <span className={styles.adjacentIndex}>{station.index}</span>
                  {station.label}
                </button>
              );
            })}
          </div>
        </section>

        <section
          className={styles.detail}
          aria-label="Station detail"
          aria-live="polite"
        >
          <header className={styles.detailHeader}>
            <div>
              <span className={styles.detailEyebrow}>
                Station {activeStation.index}
              </span>
              <h2 className={styles.detailTitle}>
                <em>{activeStation.label}</em>
              </h2>
              <p className={styles.detailCaption}>{activeStation.caption}</p>
            </div>
            <dl className={styles.detailStats}>
              <div>
                <dt>Subthemes</dt>
                <dd>{activeStation.subthemes.length}</dd>
              </div>
              <div>
                <dt>Equities</dt>
                <dd>{stationTickers.length}</dd>
              </div>
              <div>
                <dt>Critical</dt>
                <dd>
                  {
                    stationTickers.filter((t) => t.priority === "critical")
                      .length
                  }
                </dd>
              </div>
            </dl>
          </header>

          <div className={styles.detailGrid}>
            <section className={styles.subthemeColumn}>
              <h3 className={styles.columnHead}>Subthemes</h3>
              <ul className={styles.subthemeList}>
                {activeStation.subthemes.map((sub) => {
                  const entries = subthemeCounts.get(sub.tag) ?? [];
                  return (
                    <li className={styles.subthemeRow} key={sub.tag}>
                      <div className={styles.subthemeText}>
                        <span className={styles.subthemeLabel}>
                          {sub.label}
                        </span>
                        <span className={styles.subthemeShort}>
                          {sub.short}
                        </span>
                      </div>
                      <span className={styles.subthemeTag}>{sub.tag}</span>
                      <span className={styles.subthemeCount}>
                        {entries.length === 0 ? (
                          <span className={styles.subthemeCountEmpty}>—</span>
                        ) : (
                          entries.map((e) => e.ticker).join(" · ")
                        )}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </section>

            <section className={styles.tickerColumn}>
              <h3 className={styles.columnHead}>Equities at this station</h3>
              <ol className={styles.tickerList}>
                {stationTickers.map((entry, index) => (
                  <li
                    key={entry.ticker}
                    className={styles.tickerRow}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <span className={styles.tickerSymbol}>{entry.ticker}</span>
                    <span className={styles.tickerCompany}>
                      {entry.companyName}
                    </span>
                    <span
                      className={`${styles.tickerPriority} ${
                        styles[`priority_${entry.priority}`]
                      }`}
                    >
                      {entry.priority}
                    </span>
                    <span className={styles.tickerThemes}>
                      {entry.themes
                        .filter((t) =>
                          activeStation.subthemes.some((s) => s.tag === t),
                        )
                        .join(" / ")}
                    </span>
                  </li>
                ))}
                {stationTickers.length === 0 ? (
                  <li className={styles.tickerEmpty}>
                    No equities mapped to this station yet.
                  </li>
                ) : null}
              </ol>
            </section>
          </div>
        </section>

        <footer className={styles.footer}>
          <span className={styles.footerMono}>
            Source: config/ai_equity_watchlist.yaml · taxonomy:
            lib/value-chain.ts
          </span>
          <span className={styles.footerMono}>
            Read-only · no broker connection · no order surface
          </span>
        </footer>
      </div>
    </main>
  );
}

function nameKey(station: ValueChainStation): string {
  return `${station.id}-${station.label.toLowerCase().replace(/[^a-z]/g, "-")}`;
}
