"use client";

import { useEffect, useState } from "react";
import {
  fetchLatestAdvisoryRun,
  fetchLatestSignalSnapshots,
  fetchPortfolioSummary,
  type PortfolioSummary,
} from "../lib/api";
import type {
  LatestAdvisoryRun,
  LatestSignalSnapshots,
} from "../lib/status-model";

type SignalRow = {
  forward_indicator_score?: string | number | null;
  sentiment_score?: string | number | null;
};

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatMoney(value: string | null | undefined): string {
  if (!value) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
}

function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return "—";
  const diffMs = Date.now() - t;
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export function HeroKpiStrip() {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [snapshots, setSnapshots] = useState<LatestSignalSnapshots | null>(
    null,
  );
  const [advisoryRun, setAdvisoryRun] = useState<LatestAdvisoryRun | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const [p, s, r] = await Promise.all([
        fetchPortfolioSummary(),
        fetchLatestSignalSnapshots(),
        fetchLatestAdvisoryRun(),
      ]);
      if (cancelled) return;
      setPortfolio(p);
      setSnapshots(s);
      setAdvisoryRun(r);
    }
    void load();
    const id = window.setInterval(load, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const portfolioTotal = portfolio
    ? formatMoney(portfolio.total_market_value)
    : "—";
  const dayDelta = portfolio ? formatPct(portfolio.day_delta_pct) : "—";
  const dayDeltaTone =
    portfolio?.day_delta_pct === null || portfolio?.day_delta_pct === undefined
      ? "hero-delta-neutral"
      : (portfolio?.day_delta_pct ?? 0) >= 0
        ? "hero-delta-up"
        : "hero-delta-down";

  const snapshotsPayload = (snapshots?.payload ?? {}) as {
    snapshots?: SignalRow[];
  };
  const rows = snapshotsPayload.snapshots ?? [];
  const positive = rows.filter(
    (r) =>
      (toNumber(r.forward_indicator_score) ??
        toNumber(r.sentiment_score) ??
        0) > 0,
  ).length;
  const sentimentLabel =
    rows.length === 0 ? "—" : `${positive}/${rows.length} positive`;

  const runPayload = (advisoryRun?.payload ?? {}) as {
    completed_at?: string | null;
    run_status?: string;
  };
  const runLabel = runPayload.completed_at
    ? relativeTime(runPayload.completed_at)
    : "no runs yet";
  const runStatus = runPayload.run_status ?? "—";

  return (
    <div className="hero-kpi-strip" role="status" aria-live="polite">
      <div className="hero-kpi">
        <span className="hero-kpi-label">Portfolio</span>
        <span className="hero-kpi-value">{portfolioTotal}</span>
      </div>
      <div className="hero-kpi">
        <span className="hero-kpi-label">Δ today</span>
        <span className={`hero-kpi-value ${dayDeltaTone}`}>{dayDelta}</span>
      </div>
      <div className="hero-kpi">
        <span className="hero-kpi-label">Sentiment</span>
        <span className="hero-kpi-value">{sentimentLabel}</span>
      </div>
      <div className="hero-kpi">
        <span className="hero-kpi-label">Last advisory run</span>
        <span className="hero-kpi-value">
          {runLabel}
          {runStatus !== "—" ? (
            <span className="hero-kpi-sub"> · {runStatus}</span>
          ) : null}
        </span>
      </div>
    </div>
  );
}
