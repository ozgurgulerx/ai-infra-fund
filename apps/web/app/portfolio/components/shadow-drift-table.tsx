"use client";

import { useEffect, useState } from "react";

import { EmptyStateRow } from "../../../components/empty-state";
import {
  fetchShadowDrift,
  type ShadowDriftPayload,
} from "../../../lib/shadow-portfolio";

const REFRESH_INTERVAL_MS = 30000;

const initialPayload: ShadowDriftPayload = {
  as_of: new Date().toISOString(),
  rows: [],
  advisory_label: "advisory_only",
  status: "loading",
};

export function ShadowDriftTable() {
  const [payload, setPayload] = useState<ShadowDriftPayload>(initialPayload);

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      const next = await fetchShadowDrift();
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

  if (payload.rows.length === 0) {
    return (
      <EmptyStateRow>
        Shadow simulation — advisory only. No target weights available for the
        current as-of timestamp.
      </EmptyStateRow>
    );
  }

  return (
    <div
      className="data-table"
      role="table"
      aria-label="Shadow portfolio drift"
    >
      <div className="data-row data-header" role="row">
        <span>Symbol</span>
        <span>Current weight</span>
        <span>Advisory target</span>
        <span>Drift</span>
      </div>
      {payload.rows.map((row) => (
        <div className="data-row" role="row" key={row.ticker}>
          <span>{row.ticker}</span>
          <span>{row.current_weight}</span>
          <span>{row.target_weight}</span>
          <span>{row.drift}</span>
        </div>
      ))}
    </div>
  );
}
