"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  createTradeJournalEntry,
  fetchTradeJournalEntries,
  type TradeJournalEntry,
  type TradeJournalEntryInput
} from "../lib/api";

const initialInput: TradeJournalEntryInput = {
  ticker: "NVDA",
  side: "buy",
  quantity: "1",
  price: "900.00",
  fees: "0.00",
  trade_date: "2026-05-14",
  settlement_date: "2026-05-15",
  account_label: "local",
  status: "intended",
  notes: "Manual buy/sell journal entry for advisory review."
};

export function TradeEntryForm() {
  const [draft, setDraft] = useState<TradeJournalEntryInput>(initialInput);
  const [entries, setEntries] = useState<TradeJournalEntry[]>([]);
  const [message, setMessage] = useState("Journal-only record. Local journal only; No broker connection.");

  useEffect(() => {
    let cancelled = false;

    async function loadEntries() {
      const loadedEntries = await fetchTradeJournalEntries();
      if (!cancelled) {
        setEntries(loadedEntries);
      }
    }

    void loadEntries();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("Submitting journal-only record.");

    try {
      const created = await createTradeJournalEntry(draft);
      setEntries((currentEntries) => [created, ...currentEntries]);
      setMessage("Journal-only record added. Local journal only; No broker connection.");
    } catch (error) {
      const reason = error instanceof Error ? error.message : "request failed";
      setMessage(`Journal-only record was not added: ${reason}`);
    }
  }

  return (
    <div className="intent-workflow">
      <div className="audit-stack">
        <div>
          <strong>Manual buy/sell journal entry</strong>
          <span>Creates a local advisory journal record only. It does not connect to a broker.</span>
        </div>
        <div>
          <strong>Journal-only record</strong>
          <span>Captured for portfolio review, evidence traceability, and later reconciliation.</span>
        </div>
      </div>

      <form className="intent-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label className="field">
            <span>Ticker</span>
            <input
              name="ticker"
              value={draft.ticker}
              onChange={(event) => setDraft({ ...draft, ticker: event.target.value.toUpperCase() })}
            />
          </label>
          <label className="field">
            <span>Side</span>
            <select
              name="side"
              value={draft.side}
              onChange={(event) => setDraft({ ...draft, side: event.target.value as TradeJournalEntryInput["side"] })}
            >
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </label>
          <label className="field">
            <span>Quantity</span>
            <input
              inputMode="decimal"
              name="quantity"
              value={draft.quantity}
              onChange={(event) => setDraft({ ...draft, quantity: event.target.value })}
            />
          </label>
          <label className="field">
            <span>Price</span>
            <input
              inputMode="decimal"
              name="price"
              value={draft.price ?? ""}
              onChange={(event) => setDraft({ ...draft, price: event.target.value })}
            />
          </label>
          <label className="field">
            <span>Fees</span>
            <input
              inputMode="decimal"
              name="fees"
              value={draft.fees ?? ""}
              onChange={(event) => setDraft({ ...draft, fees: event.target.value })}
            />
          </label>
          <label className="field">
            <span>Trade date</span>
            <input
              name="trade_date"
              type="date"
              value={draft.trade_date}
              onChange={(event) => setDraft({ ...draft, trade_date: event.target.value })}
            />
          </label>
          <label className="field">
            <span>Settlement date</span>
            <input
              name="settlement_date"
              type="date"
              value={draft.settlement_date ?? ""}
              onChange={(event) => setDraft({ ...draft, settlement_date: event.target.value })}
            />
          </label>
          <label className="field">
            <span>Account label</span>
            <input
              name="account_label"
              value={draft.account_label}
              onChange={(event) => setDraft({ ...draft, account_label: event.target.value })}
            />
          </label>
          <label className="field">
            <span>Status</span>
            <select
              name="status"
              value={draft.status}
              onChange={(event) => setDraft({ ...draft, status: event.target.value as TradeJournalEntryInput["status"] })}
            >
              <option value="intended">Intended</option>
              <option value="paper">Paper</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
              <option value="ignored">Ignored</option>
            </select>
          </label>
          <label className="field field-full">
            <span>Notes</span>
            <textarea
              name="notes"
              value={draft.notes ?? ""}
              onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
            />
          </label>
        </div>
        <div className="action-bar">
          <button className="button-primary" type="submit">Add Trade To Local Journal</button>
          <span className="readonly-label">Local journal only</span>
          <span className="readonly-label">No broker connection</span>
        </div>
        <p className="panel-note">{message}</p>
      </form>

      <div className="intent-list" aria-label="Recent local trade journal records">
        {entries.map((entry) => (
          <div className="intent-row" key={entry.trade_id ?? `${entry.ticker}-${entry.trade_date}-${entry.side}`}>
            <strong>{entry.ticker} {entry.side}</strong>
            <span>
              {entry.quantity} @ {entry.price ?? "not reported"} / {entry.status} / source {entry.source ?? "manual_ui"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
