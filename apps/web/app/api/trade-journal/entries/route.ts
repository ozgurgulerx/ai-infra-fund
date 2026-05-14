import { NextResponse } from "next/server";

const BACKEND_TRADE_JOURNAL_ENTRIES_ENDPOINT = "/internal/trade-journal/entries";

function apiBaseUrl(): string {
  return (
    process.env.AI_INFRA_FUND_INTERNAL_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  ).replace(/\/$/, "");
}

export async function GET() {
  return forwardTradeJournalRequest("GET");
}

export async function POST(request: Request) {
  const payload = await request.json();
  return forwardTradeJournalRequest("POST", payload);
}

async function forwardTradeJournalRequest(method: "GET" | "POST", payload?: unknown) {
  const response = await fetch(`${apiBaseUrl()}${BACKEND_TRADE_JOURNAL_ENTRIES_ENDPOINT}`, {
    body: method === "POST" ? JSON.stringify(payload) : undefined,
    cache: "no-store",
    headers: method === "POST" ? { "Content-Type": "application/json" } : undefined,
    method
  });
  const body = await response.json();
  return NextResponse.json(body, { status: response.status });
}
