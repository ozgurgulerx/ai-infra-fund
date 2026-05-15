"use client";

import { useEffect, useState } from "react";

import { EmptyStateRow } from "../../components/empty-state";
import {
  eventLabel,
  eventStatusTone,
  fetchRecentEvents,
  type ExperimentEvent,
} from "../../lib/events";

const REFRESH_INTERVAL_MS = 30000;
const EVENT_LIMIT = 25;

export function EventTimeline() {
  const [events, setEvents] = useState<ExperimentEvent[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      const payload = await fetchRecentEvents(EVENT_LIMIT);
      if (!cancelled) {
        setEvents(payload.events);
      }
    }

    void refresh();
    const interval = window.setInterval(refresh, REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  if (events.length === 0) {
    return (
      <EmptyStateRow>
        No advisory events recorded yet. The timeline streams advisory-pipeline
        milestones (signal computed, weights generated, recommendation issued,
        backtest started/completed, shadow comparison recorded).
      </EmptyStateRow>
    );
  }

  return (
    <ol className="event-timeline" aria-label="Advisory event timeline">
      {events.map((event) => {
        const tone = eventStatusTone(event.severity);
        return (
          <li
            key={event.event_id}
            className={`event-row ${tone.cssClass}`}
            title={`${tone.label} severity`}
          >
            <span className="event-kind">{eventLabel(event.kind)}</span>
            <span className="event-time" title={event.occurred_at}>
              {event.occurred_at}
            </span>
            {event.run_id ? (
              <span className="event-run">{event.run_id}</span>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
