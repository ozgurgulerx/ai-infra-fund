"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  adjacentStations,
  valueChain,
  type ValueChainStation,
  type ValueChainSubtheme,
} from "../lib/value-chain";
import {
  watchlist,
  type WatchlistEntry,
} from "../lib/watchlist-mirror";
import { SectionPanel } from "./section-panel";
import { StatusChip } from "./workstation";

type PriorityKey = WatchlistEntry["priority"];
type FilterKey = "all" | "accumulate" | "review" | "risk" | "unrated";

export type ValueChainCandidateRating = {
  ticker?: string;
  company?: string | null;
  current_label?: string;
  latest_change?: string;
  risk_flags?: string[];
  invalidation?: string | null;
  evidence_ids?: string[];
  source_links?: Array<{ url?: string; label?: string; evidence_ids?: string[] }>;
};

type CandidateRow = {
  entry: WatchlistEntry;
  rating?: ValueChainCandidateRating;
  stance: string;
  evidenceCount: number;
  sourceLinkCount: number;
  hasRisk: boolean;
  matchingThemes: string[];
};

type Lens = {
  id: string;
  label: string;
  caption: string;
  stations: ValueChainStation[];
};

const AI_GRID_STATION_IDS = new Set(["power", "grid_dc_build"]);

const priorityRank: Record<PriorityKey, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const stanceRank: Record<string, number> = {
  accumulate: 0,
  watch: 1,
  review: 2,
  hold: 3,
  trim: 4,
  "exit-candidate": 5,
  avoid: 6,
  unrated: 7,
};

const filters: Array<{ key: FilterKey; label: string }> = [
  { key: "all", label: "All" },
  { key: "accumulate", label: "Accumulate candidates" },
  { key: "review", label: "Watch / review" },
  { key: "risk", label: "Risk flagged" },
  { key: "unrated", label: "Unrated" },
];

export function ValueChainCandidateMatrix({
  ratings,
  status,
}: {
  ratings: ValueChainCandidateRating[];
  status: string;
}) {
  const [activeLensId, setActiveLensId] = useState("ai_grid");
  const [filterKey, setFilterKey] = useState<FilterKey>("all");

  const lenses = useMemo(buildLenses, []);
  const activeLens = lenses.find((lens) => lens.id === activeLensId) ?? lenses[0];
  const ratingsByTicker = useMemo(() => {
    return new Map(
      ratings
        .filter((rating) => rating.ticker)
        .map((rating) => [String(rating.ticker).toUpperCase(), rating]),
    );
  }, [ratings]);

  const activeRows = useMemo(() => {
    return uniqueCandidates(activeLens.stations, ratingsByTicker);
  }, [activeLens, ratingsByTicker]);
  const visibleRows = activeRows.filter((row) => matchesFilter(row, filterKey));
  const activeTags = new Set(
    activeLens.stations.flatMap((station) =>
      station.subthemes.map((subtheme) => subtheme.tag),
    ),
  );

  const accumulateCount = activeRows.filter(
    (row) => row.stance === "accumulate",
  ).length;
  const riskCount = activeRows.filter((row) => row.hasRisk).length;
  const evidenceCount = activeRows.reduce(
    (count, row) => count + row.evidenceCount,
    0,
  );

  return (
    <div className="value-chain-candidate-layout">
      <SectionPanel
        eyebrow="Candidate lens"
        title="AI Grid"
        aside={<StatusChip label={status} tone={status === "available" ? "fresh" : "stale"} />}
      >
        <p className="panel-note">
          Candidate matrix for configured AI infrastructure subsegments. Rows
          merge watchlist taxonomy with live advisory ratings, risk notes, and
          evidence refs.
        </p>

        <div className="value-chain-lens-bar" aria-label="Value-chain lenses">
          {lenses.map((lens) => {
            const isActive = lens.id === activeLens.id;
            const candidateCount = uniqueCandidates(
              lens.stations,
              ratingsByTicker,
            ).length;
            return (
              <button
                aria-pressed={isActive}
                className={`value-chain-lens${
                  isActive ? " value-chain-lens-active" : ""
                }`}
                key={lens.id}
                onClick={() => setActiveLensId(lens.id)}
                type="button"
              >
                <strong>{lens.label}</strong>
                <span>{candidateCount} candidates</span>
              </button>
            );
          })}
        </div>
      </SectionPanel>

      <section className="value-chain-candidate-main">
        <div className="value-chain-candidate-header">
          <div>
            <p className="eyebrow">Candidate matrix</p>
            <h2>{activeLens.label}</h2>
            <p>{activeLens.caption}</p>
          </div>
          <div className="value-chain-filter-bar" aria-label="Candidate filters">
            {filters.map((filter) => (
              <button
                aria-pressed={filter.key === filterKey}
                className={`value-chain-filter${
                  filter.key === filterKey ? " value-chain-filter-active" : ""
                }`}
                key={filter.key}
                onClick={() => setFilterKey(filter.key)}
                type="button"
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>

        <dl className="value-chain-summary-grid">
          <div>
            <dt>Candidates</dt>
            <dd>{visibleRows.length}</dd>
          </div>
          <div>
            <dt>Accumulate candidates</dt>
            <dd>{accumulateCount}</dd>
          </div>
          <div>
            <dt>Risk flagged</dt>
            <dd>{riskCount}</dd>
          </div>
          <div>
            <dt>Evidence refs</dt>
            <dd>{evidenceCount}</dd>
          </div>
        </dl>

        <div className="value-chain-candidate-table" role="table">
          <div
            className="value-chain-candidate-row value-chain-candidate-row-header"
            role="row"
          >
            <span>Candidate</span>
            <span>Priority</span>
            <span>Current advisory stance</span>
            <span>Latest change</span>
            <span>Risk / invalidation</span>
            <span>Evidence refs</span>
            <span>Ticker workbench</span>
          </div>

          {activeLens.stations.map((station) => (
            <StationCandidateGroup
              activeTags={activeTags}
              filterKey={filterKey}
              key={station.id}
              ratingsByTicker={ratingsByTicker}
              station={station}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function StationCandidateGroup({
  activeTags,
  filterKey,
  ratingsByTicker,
  station,
}: {
  activeTags: ReadonlySet<string>;
  filterKey: FilterKey;
  ratingsByTicker: ReadonlyMap<string, ValueChainCandidateRating>;
  station: ValueChainStation;
}) {
  return (
    <section className="value-chain-station-group">
      <div className="value-chain-station-heading">
        <strong>
          {station.index}. {station.label}
        </strong>
        <span>{station.caption}</span>
      </div>
      {station.subthemes.map((subtheme) => (
        <SubthemeCandidateGroup
          activeTags={activeTags}
          filterKey={filterKey}
          key={subtheme.tag}
          ratingsByTicker={ratingsByTicker}
          subtheme={subtheme}
        />
      ))}
    </section>
  );
}

function SubthemeCandidateGroup({
  activeTags,
  filterKey,
  ratingsByTicker,
  subtheme,
}: {
  activeTags: ReadonlySet<string>;
  filterKey: FilterKey;
  ratingsByTicker: ReadonlyMap<string, ValueChainCandidateRating>;
  subtheme: ValueChainSubtheme;
}) {
  const rows = watchlist
    .filter((entry) => entry.themes.includes(subtheme.tag))
    .map((entry) => candidateRow(entry, ratingsByTicker, activeTags))
    .filter((row) => matchesFilter(row, filterKey))
    .sort(compareCandidates);

  return (
    <div className="value-chain-subtheme-group">
      <div className="value-chain-subtheme-heading">
        <div>
          <strong>{subtheme.label}</strong>
          <span>{subtheme.short}</span>
        </div>
        <code>{subtheme.tag}</code>
      </div>
      {rows.length > 0 ? (
        rows.map((row) => (
          <CandidateMatrixRow
            key={`${subtheme.tag}-${row.entry.ticker}`}
            row={row}
          />
        ))
      ) : (
        <div className="value-chain-empty-row">
          No candidates match this filter.
        </div>
      )}
    </div>
  );
}

function CandidateMatrixRow({ row }: { row: CandidateRow }) {
  const rating = row.rating;
  const latestChange =
    rating?.latest_change || "No published advisory change yet.";
  const riskText =
    row.hasRisk
      ? [
          ...(rating?.risk_flags ?? []),
          rating?.invalidation ? `Invalidation: ${rating.invalidation}` : "",
        ]
          .filter(Boolean)
          .join(" | ")
      : "No current risk flag published.";

  return (
    <div className="value-chain-candidate-row" role="row">
      <span className="value-chain-candidate-asset">
        <Link className="ticker-link" href={`/ticker/${row.entry.ticker}`}>
          {row.entry.ticker}
        </Link>
        <small>{row.entry.companyName}</small>
        <em>{row.matchingThemes.join(" / ")}</em>
      </span>
      <span>
        <span className={`value-chain-priority priority-${row.entry.priority}`}>
          {row.entry.priority}
        </span>
      </span>
      <span>
        <StatusChip label={row.stance} tone={toneForStance(row.stance)} />
      </span>
      <span className="value-chain-candidate-note">{latestChange}</span>
      <span className="value-chain-candidate-note">{riskText}</span>
      <span className="value-chain-evidence-count">
        {row.evidenceCount} evidence refs
        <small>{row.sourceLinkCount} source links</small>
      </span>
      <span>
        <Link className="secondary-action" href={`/ticker/${row.entry.ticker}`}>
          Ticker workbench
        </Link>
      </span>
    </div>
  );
}

function buildLenses(): Lens[] {
  const gridStations = valueChain.filter((station) =>
    AI_GRID_STATION_IDS.has(station.id),
  );
  const stationLenses = [...valueChain, ...adjacentStations].map((station) => ({
    id: station.id,
    label: station.label,
    caption: station.caption,
    stations: [station],
  }));
  return [
    {
      id: "ai_grid",
      label: "AI Grid",
      caption:
        "Power generation, grid equipment, datacenter power, and cooling candidates tied to AI buildout constraints.",
      stations: gridStations,
    },
    ...stationLenses,
  ];
}

function uniqueCandidates(
  stations: ValueChainStation[],
  ratingsByTicker: ReadonlyMap<string, ValueChainCandidateRating>,
): CandidateRow[] {
  const tags = new Set(
    stations.flatMap((station) => station.subthemes.map((subtheme) => subtheme.tag)),
  );
  return watchlist
    .filter((entry) => entry.themes.some((tag) => tags.has(tag)))
    .map((entry) => candidateRow(entry, ratingsByTicker, tags))
    .sort(compareCandidates);
}

function candidateRow(
  entry: WatchlistEntry,
  ratingsByTicker: ReadonlyMap<string, ValueChainCandidateRating>,
  activeTags: ReadonlySet<string>,
): CandidateRow {
  const rating = ratingsByTicker.get(entry.ticker);
  const stance = normalizeStance(rating?.current_label);
  const evidenceCount = rating?.evidence_ids?.length ?? 0;
  const sourceLinkCount = rating?.source_links?.length ?? 0;
  const hasRisk =
    Boolean(rating?.invalidation) || Boolean(rating?.risk_flags?.length);
  const matchingThemes = entry.themes.filter((tag) => activeTags.has(tag));
  return {
    entry,
    rating,
    stance,
    evidenceCount,
    sourceLinkCount,
    hasRisk,
    matchingThemes,
  };
}

function compareCandidates(left: CandidateRow, right: CandidateRow): number {
  const priorityDelta =
    priorityRank[left.entry.priority] - priorityRank[right.entry.priority];
  if (priorityDelta !== 0) {
    return priorityDelta;
  }
  const stanceDelta =
    (stanceRank[left.stance] ?? stanceRank.unrated) -
    (stanceRank[right.stance] ?? stanceRank.unrated);
  if (stanceDelta !== 0) {
    return stanceDelta;
  }
  return left.entry.ticker.localeCompare(right.entry.ticker);
}

function matchesFilter(row: CandidateRow, filterKey: FilterKey): boolean {
  if (filterKey === "accumulate") {
    return row.stance === "accumulate";
  }
  if (filterKey === "review") {
    return ["watch", "review", "hold"].includes(row.stance);
  }
  if (filterKey === "risk") {
    return row.hasRisk;
  }
  if (filterKey === "unrated") {
    return row.stance === "unrated";
  }
  return true;
}

function normalizeStance(value: string | undefined): string {
  const normalized = String(value ?? "").trim().toLowerCase();
  return normalized || "unrated";
}

function toneForStance(
  stance: string,
): "neutral" | "positive" | "cautious" | "negative" | "review" | "fresh" {
  if (stance === "accumulate") {
    return "fresh";
  }
  if (stance === "watch" || stance === "review") {
    return "review";
  }
  if (stance === "trim" || stance === "exit-candidate" || stance === "avoid") {
    return "negative";
  }
  if (stance === "hold") {
    return "neutral";
  }
  return "cautious";
}
