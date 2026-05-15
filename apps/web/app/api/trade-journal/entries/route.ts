import { NextResponse } from "next/server";

const BACKEND_TRADE_JOURNAL_ENTRIES_ENDPOINT = "/internal/trade-journal/entries";
const INTERNAL_TOKEN_HEADER = "X-Internal-Token";

function apiBaseUrl(): string {
  return (
    process.env.AI_INFRA_FUND_INTERNAL_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  ).replace(/\/$/, "");
}

function internalHeaders(method: "GET" | "POST"): HeadersInit {
  const headers: Record<string, string> = {};
  const token = process.env.AI_INFRA_FUND_INTERNAL_TOKEN?.trim();
  if (token) {
    headers[INTERNAL_TOKEN_HEADER] = token;
  }
  if (method === "POST") {
    headers["Content-Type"] = "application/json";
  }
  return headers;
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
    headers: internalHeaders(method),
    method
  });
  const body = await response.json();
  return NextResponse.json(body, { status: response.status });
}
