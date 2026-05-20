import { AppShell } from "../../components/app-shell";
import {
  ValueChainCandidateMatrix,
  type ValueChainCandidateRating,
} from "../../components/value-chain-candidate-matrix";

export const dynamic = "force-dynamic";

type ApiEnvelope<TData> = {
  data?: TData;
  error?: { code?: string; message?: string };
};

type WatchlistRatingsPayload = {
  status?: string;
  advisory_label?: string;
  items?: ValueChainCandidateRating[];
};

const INTERNAL_TOKEN_HEADER = "X-Internal-Token";

export default async function ThemesPage() {
  const ratingsPayload = await readLatestWatchlistRatings();

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Value-Chain Candidate Matrix"
        title="AI Infrastructure Candidate Matrix"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <ValueChainCandidateMatrix
          ratings={ratingsPayload.items ?? []}
          status={ratingsPayload.status ?? "degraded"}
        />
      </AppShell>
    </div>
  );
}

async function readLatestWatchlistRatings(): Promise<WatchlistRatingsPayload> {
  try {
    const response = await fetch(
      `${internalApiBaseUrl()}/internal/watchlist/ratings/latest`,
      {
        cache: "no-store",
        headers: internalHeaders(),
        method: "GET",
      },
    );
    const payload = (await response.json()) as ApiEnvelope<WatchlistRatingsPayload>;
    if (!response.ok || !payload.data) {
      return emptyRatingsPayload();
    }
    return payload.data;
  } catch {
    return emptyRatingsPayload();
  }
}

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

function emptyRatingsPayload(): WatchlistRatingsPayload {
  return {
    status: "degraded",
    advisory_label: "advisory_only",
    items: [],
  };
}
