import { NextResponse } from "next/server";

type BackendRouteContext = {
  params: Promise<{ path: string[] }>;
};

const INTERNAL_TOKEN_HEADER = "X-Internal-Token";

function internalApiBaseUrl(): string {
  return (
    process.env.AI_INFRA_FUND_INTERNAL_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  ).replace(/\/$/, "");
}

function internalHeaders(): HeadersInit | undefined {
  const token = process.env.AI_INFRA_FUND_INTERNAL_TOKEN?.trim();
  return token ? { [INTERNAL_TOKEN_HEADER]: token } : undefined;
}

export async function GET(request: Request, context: BackendRouteContext) {
  return forwardReadOnlyBackendRequest(request, context);
}

async function forwardReadOnlyBackendRequest(request: Request, context: BackendRouteContext) {
  const { path } = await context.params;
  const sourceUrl = new URL(request.url);
  const backendPath = `/${path.map(encodeURIComponent).join("/")}`;
  const backendUrl = `${internalApiBaseUrl()}${backendPath}${sourceUrl.search}`;

  const response = await fetch(backendUrl, {
    cache: "no-store",
    headers: internalHeaders(),
    method: "GET"
  });
  const body = await response.text();

  return new NextResponse(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json"
    }
  });
}
