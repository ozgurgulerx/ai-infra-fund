export type PortfolioHolding = {
  symbol: string;
  role: string;
  bucket: string;
  currentWeight: string;
  targetWeight: string;
  drift: string;
  note: string;
};

export type JournalEntry = {
  ticker: string;
  action: string;
  status: string;
  targetPrice: string;
  limitPrice: string;
  linkedRecommendation: string;
  evidenceIds: string;
};

export const portfolioRows = [
  ["MSFT", "AI platform and cloud capex", "Core", "23.19%"],
  ["NVDA", "AI accelerator leader", "Core", "9.67%"],
  ["SMCI", "AI server hardware", "Active risk", "5.21%"],
  ["ARM", "CPU/IP layer", "Satellite", "7.89%"],
  ["Cash", "Dry powder and risk buffer", "Reserve", "51.38%"]
] as const;

export const portfolioHoldings: PortfolioHolding[] = [
  {
    symbol: "MSFT",
    role: "AI platform and cloud capex",
    bucket: "Core",
    currentWeight: "23.19%",
    targetWeight: "22.50%",
    drift: "+0.69%",
    note: "Within target band"
  },
  {
    symbol: "NVDA",
    role: "AI accelerator leader",
    bucket: "Core",
    currentWeight: "9.67%",
    targetWeight: "12.00%",
    drift: "-2.33%",
    note: "Advisory accumulate candidate"
  },
  {
    symbol: "SMCI",
    role: "AI server hardware",
    bucket: "Active risk",
    currentWeight: "5.21%",
    targetWeight: "4.00%",
    drift: "+1.21%",
    note: "Risk and evidence review required"
  },
  {
    symbol: "ARM",
    role: "CPU/IP layer",
    bucket: "Satellite",
    currentWeight: "7.89%",
    targetWeight: "8.00%",
    drift: "-0.11%",
    note: "Hold"
  },
  {
    symbol: "Cash",
    role: "Dry powder and risk buffer",
    bucket: "Reserve",
    currentWeight: "51.38%",
    targetWeight: "50.00%",
    drift: "+1.38%",
    note: "Available for manual planning"
  }
];

export const journalEntries: JournalEntry[] = [
  {
    ticker: "NVDA",
    action: "Intended add",
    status: "Planned",
    targetPrice: "875.00",
    limitPrice: "868.50",
    linkedRecommendation: "recommendation-demo-nvda",
    evidenceIds: "evidence-demo-ai-infra-nvda"
  },
  {
    ticker: "SMCI",
    action: "Risk trim review",
    status: "Draft",
    targetPrice: "920.00",
    limitPrice: "914.00",
    linkedRecommendation: "not linked",
    evidenceIds: "not linked"
  }
];

export const tickerSignals = [
  { label: "sentiment_score", value: "0.68", source: "source-weighted evidence events" },
  { label: "technical_score", value: "0.61", source: "deterministic technical snapshot" },
  { label: "fundamental_score", value: "0.74", source: "deterministic fundamentals snapshot" },
  { label: "portfolio_risk_score", value: "0.32", source: "portfolio constraint model" }
];

export const systemRunRows = [
  ["Latest advisory run", "run-local-advisory-20260514", "advisory_only"],
  ["Model run ledger", "model-run-demo-local-review", "schema valid"],
  ["Evaluation", "evaluation-demo-ai-infra", "shadow-ready"],
  ["Target weights", "target-weights-demo-ai-infra", "deterministic"]
] as const;
