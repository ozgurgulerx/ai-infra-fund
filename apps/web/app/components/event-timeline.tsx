"use client";

import { useEffect, useState } from "react";

import {
  eventLabel,
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
      <div className="data-empty-state" role="status">
        No advisory events recorded yet. The timeline streams advisory-pipeline
        milestones (signal computed, weights generated, recommendation issued,
        backtest started/completed, shadow comparison recorded).
      </div>
    );
  }

  return (
    <ol className="event-timeline" aria-label="Advisory event timeline">
      {events.map((event) => (
        <li
          key={event.event_id}
          className={`event-row event-${event.severity}`}
        >
          <span className="event-kind">{eventLabel(event.kind)}</span>
          <span className="event-time" title={event.occurred_at}>
            {event.occurred_at}
          </span>
          {event.run_id ? (
            <span className="event-run">{event.run_id}</span>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
