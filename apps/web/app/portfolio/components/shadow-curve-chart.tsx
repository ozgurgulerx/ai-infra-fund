"use client";

import { useEffect, useMemo, useState } from "react";

import {
  fetchShadowSimulation,
  type ShadowSimulationPayload,
} from "../../../lib/shadow-portfolio";

const REFRESH_INTERVAL_MS = 30000;
const HORIZON_DAYS = 30;
const CHART_WIDTH = 480;
const CHART_HEIGHT = 160;
const CHART_PADDING = 12;

const initialPayload: ShadowSimulationPayload = {
  as_of: new Date().toISOString(),
  curve: [],
  metrics: {},
  advisory_label: "advisory_only",
  status: "loading",
};

export function ShadowCurveChart() {
  const [payload, setPayload] =
    useState<ShadowSimulationPayload>(initialPayload);

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      const next = await fetchShadowSimulation(HORIZON_DAYS);
      if (!cancelled) {
        setPayload(next);
      }
    }

    void refresh();
    const interval = window.setInterval(refresh, REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const polylinePoints = useMemo(() => buildPolylinePoints(payload), [payload]);

  if (payload.curve.length === 0) {
    return (
      <div className="data-empty-state" role="status">
        Counterfactual simulation curve will appear once price history with an
        as-of-or-earlier availability stamp is recorded. Advisory only.
      </div>
    );
  }

  return (
    <div
      className="shadow-curve-chart"
      aria-label="Shadow portfolio value curve"
    >
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        width="100%"
        height="160"
        role="img"
        aria-label="Counterfactual shadow value over time, advisory only."
      >
        <polyline
          points={polylinePoints}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
        />
      </svg>
      <dl className="shadow-curve-metrics">
        {Object.entries(payload.metrics).map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function buildPolylinePoints(payload: ShadowSimulationPayload): string {
  const values = payload.curve.map((point) => Number(point.shadow_value));
  if (values.length === 0) {
    return "";
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const innerWidth = CHART_WIDTH - CHART_PADDING * 2;
  const innerHeight = CHART_HEIGHT - CHART_PADDING * 2;
  return values
    .map((value, index) => {
      const xRatio = values.length === 1 ? 0.5 : index / (values.length - 1);
      const x = CHART_PADDING + xRatio * innerWidth;
      const y = CHART_PADDING + (1 - (value - min) / span) * innerHeight;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}
