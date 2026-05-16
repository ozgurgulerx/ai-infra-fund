export type AdvisoryAction = "watch" | "accumulate" | "hold" | "trim" | "avoid";

export type EvidenceRef = {
  evidenceId: string;
  source: string;
  title: string;
  availableAt: string;
};

export type MarketEventView = {
  eventId: string;
  eventType: string;
  catalyst: string;
  aiRelevance: string;
  segment: string;
  tickers: string[];
  direction: "positive" | "negative" | "mixed" | "neutral";
  sentimentDirection: "positive" | "negative" | "mixed" | "neutral";
  materiality: "high" | "medium_high" | "medium" | "low";
  reviewPriority: "urgent" | "high" | "medium" | "watch";
  occurredAt: string;
  availableAt: string;
  evidenceIds: string[];
  modelRunIds: string[];
  riskFlags: string[];
};

export type SegmentImpactView = {
  segmentId: string;
  segmentName: string;
  status: "accelerating" | "constrained" | "mixed" | "deteriorating" | "watch";
  momentum: "rising" | "stable" | "falling";
  latestCatalyst: string;
  firstOrderBeneficiaries: string[];
  secondOrderBeneficiaries: string[];
  negativelyExposedTickers: string[];
  riskFlags: string[];
  relatedEventIds: string[];
  evidenceIds: string[];
};

export type EquityAssessmentView = {
  ticker: string;
  company: string;
  currentThesis: string;
  segmentExposure: string[];
  recentEventIds: string[];
  bullCase: string;
  baseCase: string;
  bearCase: string;
  riskFlags: string[];
  invalidationCondition: string;
  advisoryImplication: AdvisoryAction;
  confidence: string;
  evidenceIds: string[];
  modelRunIds: string[];
};

export type RiskRegimeView = {
  regimeId: string;
  riskType: string;
  status: "elevated" | "watch" | "constructive" | "mixed";
  summary: string;
  reliefCondition: string;
  evidenceIds: string[];
};

export type TradePlanView = {
  tradePlanId: string;
  ticker: string;
  thesis: string;
  catalyst: string;
  segment: string;
  advisoryAction: AdvisoryAction;
  entryLevel: string;
  addLevel: string;
  stopInvalidation: string;
  targetOne: string;
  targetTwo: string;
  timeHorizon: string;
  positionSizingNote: string;
  portfolioImpact: string;
  riskFlags: string[];
  evidenceIds: string[];
  llmCritique: string;
};

export type PriceTargetScenarioView = {
  ticker: string;
  bear: string;
  base: string;
  bull: string;
  horizon: string;
  evidenceIds: string[];
  riskFlags: string[];
  invalidationCondition: string;
};

export type EntryExitLevelView = {
  ticker: string;
  entryZone: string;
  addZone: string;
  trimZone: string;
  basis: string;
  evidenceIds: string[];
  riskFlags: string[];
};

export type LlmAnalystNoteView = {
  noteId: string;
  role: string;
  tickerOrSegment: string;
  summary: string;
  confidence: string;
  evidenceIds: string[];
  modelRunId: string;
};

export type SuggestedActionView = {
  actionId: string;
  ticker: string;
  advisoryLabel: AdvisoryAction;
  analystAction: string;
  linkedEventIds: string[];
  linkedTradePlanId: string;
  evidenceIds: string[];
  riskFlags: string[];
  invalidationCondition: string;
};

export type JournalReviewView = {
  journalId: string;
  ticker: string;
  status: string;
  entryExit: string;
  realizedUnrealizedPnl: string;
  exitReason: string;
  mistakeClassification: string;
  postTradeLlmReview: string;
  segment: string;
  catalystType: string;
  evidenceIds: string[];
};

export type PortfolioExposureView = {
  ticker: string;
  company: string;
  segment: string;
  weight: string;
  advisoryAction: AdvisoryAction;
  riskFlags: string[];
  linkedTradePlanId: string;
};

export const mockWorkstationData = {
  run: {
    briefId: "brief_20260516_ai_infra_trading_cockpit",
    runId: "run_20260516_wave2_static_workstation",
    asOf: "2026-05-16T08:00:00Z",
    freshness: "static mock fixture",
    advisoryLabel: "advisory_only",
    regime: "AI capex positive, power/HBM constrained, export-control risk elevated",
    executiveSummary:
      "AI infrastructure evidence still favors accelerator, CoWoS, HBM, and power-chain beneficiaries, but crowding and export-control risk keep several names in review-only mode.",
    suppressedAdvisories: [
      "META: capex monetization evidence is not strong enough for an exposure increase.",
      "VRT: valuation extension suppresses fresh add guidance until backlog quality refreshes.",
    ],
  },
  evidenceItems: [
    {
      evidenceId: "evid_20260516_cloud_capex_comp_sheet",
      source: "public earnings composite",
      title: "Hyperscaler AI capex comparison sheet",
      availableAt: "2026-05-16T07:00:00Z",
    },
    {
      evidenceId: "evid_20260515_hbm_supplier_checks",
      source: "public supplier checks",
      title: "HBM supplier allocation update",
      availableAt: "2026-05-15T17:30:00Z",
    },
    {
      evidenceId: "evid_20260515_tsm_cowos_capex_note",
      source: "company and supplier disclosures",
      title: "CoWoS capacity expansion note",
      availableAt: "2026-05-15T12:10:00Z",
    },
    {
      evidenceId: "evid_20260514_cloud_ppa_release",
      source: "public power procurement release",
      title: "AI campus power purchase agreement",
      availableAt: "2026-05-14T14:00:00Z",
    },
    {
      evidenceId: "evid_20260513_export_control_rule",
      source: "public policy notice",
      title: "Accelerator export-control update",
      availableAt: "2026-05-13T11:00:00Z",
    },
    {
      evidenceId: "evid_20260512_ai_infra_multiples_table",
      source: "internal deterministic valuation table",
      title: "AI infrastructure multiples and scenario table",
      availableAt: "2026-05-12T16:00:00Z",
    },
    {
      evidenceId: "evid_20260516_mock_price_marks",
      source: "mock deterministic price marks",
      title: "Static fixture price marks for planning screens",
      availableAt: "2026-05-16T08:00:00Z",
    },
    {
      evidenceId: "evid_20260516_manual_journal_entries",
      source: "local manual journal fixture",
      title: "Local journal entries and review notes",
      availableAt: "2026-05-16T08:00:00Z",
    },
  ] satisfies EvidenceRef[],
  marketEvents: [
    {
      eventId: "mevt_20260516_hyperscaler_capex_raise",
      eventType: "hyperscaler_capex",
      catalyst: "Cloud AI capex guidance remains above prior run-rate.",
      aiRelevance: "Pulls accelerator, networking, power, and datacenter demand forward.",
      segment: "Hyperscaler capex",
      tickers: ["NVDA", "AVGO", "ANET", "VRT", "MSFT", "GOOGL", "AMZN", "META"],
      direction: "positive",
      sentimentDirection: "positive",
      materiality: "high",
      reviewPriority: "urgent",
      occurredAt: "2026-05-16T06:30:00Z",
      availableAt: "2026-05-16T07:00:00Z",
      evidenceIds: ["evid_20260516_cloud_capex_comp_sheet"],
      modelRunIds: ["mrun_20260516_event_extract_001"],
      riskFlags: ["capex_duration", "depreciation_pressure"],
    },
    {
      eventId: "mevt_20260516_hbm_supply_bottleneck",
      eventType: "hbm_memory",
      catalyst: "HBM allocation remains tight against accelerator demand.",
      aiRelevance: "Supports memory pricing but can cap accelerator shipment timing.",
      segment: "HBM / memory",
      tickers: ["MU", "NVDA", "AMD", "TSM"],
      direction: "mixed",
      sentimentDirection: "mixed",
      materiality: "high",
      reviewPriority: "high",
      occurredAt: "2026-05-15T17:00:00Z",
      availableAt: "2026-05-15T17:30:00Z",
      evidenceIds: ["evid_20260515_hbm_supplier_checks"],
      modelRunIds: ["mrun_20260516_event_extract_002"],
      riskFlags: ["hbm_allocation", "customer_concentration"],
    },
    {
      eventId: "mevt_20260516_cowos_capacity_expansion",
      eventType: "advanced_packaging",
      catalyst: "Advanced packaging capacity plans continue expanding.",
      aiRelevance: "Benefits TSM and semicap suppliers while relieving accelerator shipment constraints.",
      segment: "Foundry / CoWoS / semicap",
      tickers: ["TSM", "ASML", "NVDA", "AMD"],
      direction: "positive",
      sentimentDirection: "positive",
      materiality: "medium_high",
      reviewPriority: "high",
      occurredAt: "2026-05-15T11:20:00Z",
      availableAt: "2026-05-15T12:10:00Z",
      evidenceIds: ["evid_20260515_tsm_cowos_capex_note"],
      modelRunIds: ["mrun_20260516_event_extract_003"],
      riskFlags: ["geopolitical", "cowos_ramp_timing"],
    },
    {
      eventId: "mevt_20260516_datacenter_power_purchase_agreement",
      eventType: "power_grid",
      catalyst: "AI campus power purchase agreements keep moving ahead.",
      aiRelevance: "Power availability remains a first-order limiter for datacenter deployment.",
      segment: "Power / grid / cooling",
      tickers: ["VRT", "ETN", "PWR", "CEG", "DLR", "EQIX"],
      direction: "positive",
      sentimentDirection: "positive",
      materiality: "medium_high",
      reviewPriority: "high",
      occurredAt: "2026-05-14T13:20:00Z",
      availableAt: "2026-05-14T14:00:00Z",
      evidenceIds: ["evid_20260514_cloud_ppa_release"],
      modelRunIds: ["mrun_20260516_event_extract_004"],
      riskFlags: ["grid_interconnection", "valuation_extension"],
    },
    {
      eventId: "mevt_20260516_export_control_update",
      eventType: "export_control",
      catalyst: "New accelerator export-control review raises shipment uncertainty.",
      aiRelevance: "Creates revenue timing and compliance risk for accelerator-heavy names.",
      segment: "Sovereign AI / export controls",
      tickers: ["NVDA", "AMD", "AVGO", "TSM"],
      direction: "negative",
      sentimentDirection: "negative",
      materiality: "medium_high",
      reviewPriority: "high",
      occurredAt: "2026-05-13T10:30:00Z",
      availableAt: "2026-05-13T11:00:00Z",
      evidenceIds: ["evid_20260513_export_control_rule"],
      modelRunIds: ["mrun_20260516_event_extract_005"],
      riskFlags: ["export_control", "geopolitical"],
    },
  ] satisfies MarketEventView[],
  segmentImpacts: [
    {
      segmentId: "hyperscaler_capex",
      segmentName: "Hyperscaler capex",
      status: "accelerating",
      momentum: "rising",
      latestCatalyst: "Cloud AI capex guidance remains above prior run-rate.",
      firstOrderBeneficiaries: ["NVDA", "AVGO", "ANET", "VRT"],
      secondOrderBeneficiaries: ["TSM", "ASML", "MU", "PWR"],
      negativelyExposedTickers: ["META"],
      riskFlags: ["capex_monetization_gap", "depreciation_pressure"],
      relatedEventIds: ["mevt_20260516_hyperscaler_capex_raise"],
      evidenceIds: ["evid_20260516_cloud_capex_comp_sheet"],
    },
    {
      segmentId: "accelerators",
      segmentName: "AI accelerators",
      status: "constrained",
      momentum: "rising",
      latestCatalyst: "HBM and export-control constraints keep accelerator supply quality under review.",
      firstOrderBeneficiaries: ["NVDA", "AMD"],
      secondOrderBeneficiaries: ["TSM", "MU", "AVGO"],
      negativelyExposedTickers: ["META", "GOOGL"],
      riskFlags: ["hbm_allocation", "export_control"],
      relatedEventIds: [
        "mevt_20260516_hbm_supply_bottleneck",
        "mevt_20260516_export_control_update",
      ],
      evidenceIds: ["evid_20260515_hbm_supplier_checks", "evid_20260513_export_control_rule"],
    },
    {
      segmentId: "hbm_memory",
      segmentName: "HBM / memory",
      status: "accelerating",
      momentum: "rising",
      latestCatalyst: "HBM allocation remains tight against accelerator demand.",
      firstOrderBeneficiaries: ["MU"],
      secondOrderBeneficiaries: ["NVDA", "AMD", "TSM"],
      negativelyExposedTickers: [],
      riskFlags: ["qualification", "memory_cycle"],
      relatedEventIds: ["mevt_20260516_hbm_supply_bottleneck"],
      evidenceIds: ["evid_20260515_hbm_supplier_checks"],
    },
    {
      segmentId: "foundry_cowos_semicap",
      segmentName: "Foundry / CoWoS / semicap",
      status: "accelerating",
      momentum: "rising",
      latestCatalyst: "Advanced packaging capacity plans continue expanding.",
      firstOrderBeneficiaries: ["TSM", "ASML"],
      secondOrderBeneficiaries: ["NVDA", "AMD", "MU"],
      negativelyExposedTickers: [],
      riskFlags: ["geopolitical", "cowos_ramp_timing"],
      relatedEventIds: ["mevt_20260516_cowos_capacity_expansion"],
      evidenceIds: ["evid_20260515_tsm_cowos_capex_note"],
    },
    {
      segmentId: "networking_interconnect",
      segmentName: "Networking / interconnect",
      status: "watch",
      momentum: "stable",
      latestCatalyst: "Capex evidence keeps Ethernet and custom silicon demand in review.",
      firstOrderBeneficiaries: ["ANET", "AVGO", "MRVL"],
      secondOrderBeneficiaries: ["NVDA", "AMD"],
      negativelyExposedTickers: [],
      riskFlags: ["customer_concentration"],
      relatedEventIds: ["mevt_20260516_hyperscaler_capex_raise"],
      evidenceIds: ["evid_20260516_cloud_capex_comp_sheet"],
    },
    {
      segmentId: "datacenter_providers",
      segmentName: "Datacenter providers",
      status: "mixed",
      momentum: "stable",
      latestCatalyst: "Demand is strong, but power access determines rentable capacity.",
      firstOrderBeneficiaries: ["DLR", "EQIX"],
      secondOrderBeneficiaries: ["VRT", "ETN", "PWR"],
      negativelyExposedTickers: [],
      riskFlags: ["power_availability", "leasing_spread"],
      relatedEventIds: ["mevt_20260516_datacenter_power_purchase_agreement"],
      evidenceIds: ["evid_20260514_cloud_ppa_release"],
    },
    {
      segmentId: "power_grid_cooling",
      segmentName: "Power / grid / nuclear / gas / cooling",
      status: "constrained",
      momentum: "rising",
      latestCatalyst: "Power purchase agreements keep grid and cooling constraints visible.",
      firstOrderBeneficiaries: ["VRT", "ETN", "PWR", "CEG"],
      secondOrderBeneficiaries: ["DLR", "EQIX", "MSFT"],
      negativelyExposedTickers: ["META", "GOOGL"],
      riskFlags: ["grid_interconnection", "valuation_extension"],
      relatedEventIds: ["mevt_20260516_datacenter_power_purchase_agreement"],
      evidenceIds: ["evid_20260514_cloud_ppa_release"],
    },
    {
      segmentId: "sovereign_ai_export_controls",
      segmentName: "Sovereign AI / export controls / security",
      status: "deteriorating",
      momentum: "rising",
      latestCatalyst: "Export-control review raises shipment uncertainty.",
      firstOrderBeneficiaries: [],
      secondOrderBeneficiaries: ["ASML", "TSM"],
      negativelyExposedTickers: ["NVDA", "AMD", "AVGO"],
      riskFlags: ["export_control", "geopolitical"],
      relatedEventIds: ["mevt_20260516_export_control_update"],
      evidenceIds: ["evid_20260513_export_control_rule"],
    },
    {
      segmentId: "ai_software_monetization",
      segmentName: "AI software monetization",
      status: "watch",
      momentum: "stable",
      latestCatalyst: "Cloud platforms need stronger AI revenue evidence to offset capex intensity.",
      firstOrderBeneficiaries: ["MSFT", "ORCL"],
      secondOrderBeneficiaries: ["GOOGL", "AMZN"],
      negativelyExposedTickers: ["META"],
      riskFlags: ["monetization_lag", "margin_pressure"],
      relatedEventIds: ["mevt_20260516_hyperscaler_capex_raise"],
      evidenceIds: ["evid_20260516_cloud_capex_comp_sheet"],
    },
  ] satisfies SegmentImpactView[],
  equityAssessments: [
    {
      ticker: "NVDA",
      company: "NVIDIA",
      currentThesis:
        "Accelerator demand remains structurally strong, but HBM allocation and export-control risk keep adds conditional.",
      segmentExposure: ["AI accelerators", "HBM / memory", "Sovereign AI / export controls"],
      recentEventIds: [
        "mevt_20260516_hyperscaler_capex_raise",
        "mevt_20260516_hbm_supply_bottleneck",
        "mevt_20260516_export_control_update",
      ],
      bullCase: "Hyperscaler capex and constrained supply sustain pricing power.",
      baseCase: "Demand remains strong while shipment timing stays tied to HBM availability.",
      bearCase: "Policy limits or HBM delays reduce recognized revenue timing.",
      riskFlags: ["hbm_allocation", "export_control", "valuation_crowding"],
      invalidationCondition:
        "Invalidate the accumulate setup if HBM constraints worsen while export-control risk removes material shipment routes.",
      advisoryImplication: "watch",
      confidence: "0.74",
      evidenceIds: [
        "evid_20260516_cloud_capex_comp_sheet",
        "evid_20260515_hbm_supplier_checks",
        "evid_20260513_export_control_rule",
      ],
      modelRunIds: ["mrun_20260516_advisory_review_001"],
    },
    {
      ticker: "TSM",
      company: "Taiwan Semiconductor Manufacturing Company",
      currentThesis:
        "CoWoS capacity expansion is a first-order AI infrastructure bottleneck and a durable strategic positive.",
      segmentExposure: ["Foundry / CoWoS / semicap", "AI accelerators"],
      recentEventIds: ["mevt_20260516_cowos_capacity_expansion"],
      bullCase: "Packaging capacity expansion captures AI accelerator value-chain scarcity.",
      baseCase: "Capacity ramps steadily while geopolitical risk stays manageable.",
      bearCase: "Ramp timing slips or customer concentration grows faster than capacity.",
      riskFlags: ["geopolitical", "customer_concentration"],
      invalidationCondition:
        "Invalidate if CoWoS ramp milestones slip while AI accelerator demand indicators cool.",
      advisoryImplication: "accumulate",
      confidence: "0.77",
      evidenceIds: ["evid_20260515_tsm_cowos_capex_note"],
      modelRunIds: ["mrun_20260516_advisory_review_002"],
    },
    {
      ticker: "MU",
      company: "Micron",
      currentThesis:
        "HBM tightness supports a watch-to-accumulate path, but customer qualification evidence must improve.",
      segmentExposure: ["HBM / memory"],
      recentEventIds: ["mevt_20260516_hbm_supply_bottleneck"],
      bullCase: "HBM mix shift raises margins and improves memory-cycle quality.",
      baseCase: "HBM demand offsets some commodity memory volatility.",
      bearCase: "Qualification delays or commodity weakness overwhelm AI mix uplift.",
      riskFlags: ["qualification", "memory_cycle"],
      invalidationCondition:
        "Invalidate if HBM share-gain evidence weakens or pricing turns down before qualification improves.",
      advisoryImplication: "watch",
      confidence: "0.67",
      evidenceIds: ["evid_20260515_hbm_supplier_checks"],
      modelRunIds: ["mrun_20260516_advisory_review_003"],
    },
    {
      ticker: "VRT",
      company: "Vertiv",
      currentThesis:
        "Power and cooling demand remains strong, but valuation extension makes fresh exposure less attractive.",
      segmentExposure: ["Power / grid / nuclear / gas / cooling", "Datacenter providers"],
      recentEventIds: ["mevt_20260516_datacenter_power_purchase_agreement"],
      bullCase: "Backlog quality and AI campus buildouts support durable growth.",
      baseCase: "Demand is strong but valuation absorbs near-term upside.",
      bearCase: "Backlog conversion or margin evidence weakens after rerating.",
      riskFlags: ["valuation_extension", "backlog_conversion"],
      invalidationCondition:
        "Invalidate hold/trim discipline if backlog deteriorates while valuation remains extended.",
      advisoryImplication: "trim",
      confidence: "0.69",
      evidenceIds: ["evid_20260514_cloud_ppa_release", "evid_20260512_ai_infra_multiples_table"],
      modelRunIds: ["mrun_20260516_advisory_review_004"],
    },
    {
      ticker: "MSFT",
      company: "Microsoft",
      currentThesis:
        "Platform quality remains high, but capex intensity requires stronger utilization and AI revenue confirmation.",
      segmentExposure: ["Hyperscaler capex", "AI software monetization"],
      recentEventIds: ["mevt_20260516_hyperscaler_capex_raise"],
      bullCase: "AI platform monetization absorbs capex and improves cloud differentiation.",
      baseCase: "Capex remains acceptable if utilization evidence keeps improving.",
      bearCase: "Depreciation and monetization lag compress multiple support.",
      riskFlags: ["capex_duration", "monetization_lag"],
      invalidationCondition:
        "Invalidate an overweight thesis if AI revenue evidence fails to offset sustained capex increases.",
      advisoryImplication: "hold",
      confidence: "0.71",
      evidenceIds: ["evid_20260516_cloud_capex_comp_sheet"],
      modelRunIds: ["mrun_20260516_advisory_review_005"],
    },
  ] satisfies EquityAssessmentView[],
  riskRegimes: [
    {
      regimeId: "risk_export_control_20260516",
      riskType: "Export controls",
      status: "elevated",
      summary: "Policy friction is the main negative counterweight for accelerator-heavy exposure.",
      reliefCondition: "Relief requires clearer license paths or evidence that demand can reroute without margin damage.",
      evidenceIds: ["evid_20260513_export_control_rule"],
    },
    {
      regimeId: "risk_power_grid_20260516",
      riskType: "Power and grid",
      status: "watch",
      summary: "Power access remains a hard limiter for AI campus timing.",
      reliefCondition: "Relief requires energized capacity, not only announcements.",
      evidenceIds: ["evid_20260514_cloud_ppa_release"],
    },
    {
      regimeId: "risk_rates_liquidity_20260516",
      riskType: "Rates and liquidity",
      status: "mixed",
      summary: "High-multiple AI infrastructure names remain sensitive to discount-rate moves.",
      reliefCondition: "Relief requires stable rates and breadth improvement beyond megacap AI.",
      evidenceIds: ["evid_20260512_ai_infra_multiples_table"],
    },
  ] satisfies RiskRegimeView[],
  suggestedActions: [
    {
      actionId: "sact_20260516_nvda_watch",
      ticker: "NVDA",
      advisoryLabel: "watch",
      analystAction: "Review accumulate only if HBM and policy blockers improve.",
      linkedEventIds: [
        "mevt_20260516_hyperscaler_capex_raise",
        "mevt_20260516_hbm_supply_bottleneck",
      ],
      linkedTradePlanId: "tpln_20260516_nvda_accumulate_pullback",
      evidenceIds: ["evid_20260516_cloud_capex_comp_sheet", "evid_20260515_hbm_supplier_checks"],
      riskFlags: ["hbm_allocation", "export_control"],
      invalidationCondition:
        "Shipment assumptions fall on HBM or policy constraints while capex evidence stops improving.",
    },
    {
      actionId: "sact_20260516_tsm_accumulate",
      ticker: "TSM",
      advisoryLabel: "accumulate",
      analystAction: "Review manual journal note if entry zone and geopolitical checks remain valid.",
      linkedEventIds: ["mevt_20260516_cowos_capacity_expansion"],
      linkedTradePlanId: "tpln_20260516_tsm_add_cowos",
      evidenceIds: ["evid_20260515_tsm_cowos_capex_note"],
      riskFlags: ["geopolitical", "customer_concentration"],
      invalidationCondition: "CoWoS ramp milestones slip or leading AI customer demand weakens materially.",
    },
    {
      actionId: "sact_20260516_vrt_trim",
      ticker: "VRT",
      advisoryLabel: "trim",
      analystAction: "Review local trim journal note after rerating and backlog check.",
      linkedEventIds: ["mevt_20260516_datacenter_power_purchase_agreement"],
      linkedTradePlanId: "tpln_20260516_vrt_trim_strength",
      evidenceIds: ["evid_20260514_cloud_ppa_release", "evid_20260512_ai_infra_multiples_table"],
      riskFlags: ["valuation_extension", "backlog_conversion"],
      invalidationCondition: "Power and cooling backlog evidence deteriorates while valuation remains extended.",
    },
  ] satisfies SuggestedActionView[],
  openTradePlans: [
    {
      tradePlanId: "tpln_20260516_nvda_accumulate_pullback",
      ticker: "NVDA",
      thesis: "AI accelerator demand remains strong but evidence gates are strict.",
      catalyst: "Hyperscaler capex and HBM supply review.",
      segment: "AI accelerators",
      advisoryAction: "watch",
      entryLevel: "Review zone 880-910",
      addLevel: "Second review zone 820-850",
      stopInvalidation: "Invalidate below HBM/policy evidence gate, not as an executable stop.",
      targetOne: "Scenario 980",
      targetTwo: "Scenario 1180",
      timeHorizon: "6 to 18 months",
      positionSizingNote: "Keep single-name concentration under deterministic cap.",
      portfolioImpact: "Would increase accelerator exposure only if risk gate passes.",
      riskFlags: ["hbm_allocation", "export_control", "valuation_crowding"],
      evidenceIds: ["evid_20260516_cloud_capex_comp_sheet", "evid_20260515_hbm_supplier_checks"],
      llmCritique: "Strong thesis, but do not upgrade until policy and HBM contradictions are reviewed.",
    },
    {
      tradePlanId: "tpln_20260516_tsm_add_cowos",
      ticker: "TSM",
      thesis: "CoWoS expansion improves AI infrastructure bottleneck exposure.",
      catalyst: "Packaging capacity expansion note.",
      segment: "Foundry / CoWoS / semicap",
      advisoryAction: "accumulate",
      entryLevel: "Review zone 164-170",
      addLevel: "Second review zone 152-158",
      stopInvalidation: "Invalidate if packaging milestones slip.",
      targetOne: "Scenario 185",
      targetTwo: "Scenario 220",
      timeHorizon: "9 to 24 months",
      positionSizingNote: "Add only if geopolitical risk check remains inside cap.",
      portfolioImpact: "Raises foundry/packaging exposure and reduces pure accelerator concentration.",
      riskFlags: ["geopolitical", "cowos_ramp_timing"],
      evidenceIds: ["evid_20260515_tsm_cowos_capex_note"],
      llmCritique: "Best second-order beneficiary setup, but customer concentration must be monitored.",
    },
    {
      tradePlanId: "tpln_20260516_vrt_trim_strength",
      ticker: "VRT",
      thesis: "Power/cooling demand is real, but valuation extension argues for discipline.",
      catalyst: "AI campus power agreement.",
      segment: "Power / grid / nuclear / gas / cooling",
      advisoryAction: "trim",
      entryLevel: "No fresh add zone in this run",
      addLevel: "Review only below rerating band",
      stopInvalidation: "Invalidate trim bias if backlog quality accelerates and valuation resets.",
      targetOne: "Scenario 108",
      targetTwo: "Scenario 132",
      timeHorizon: "6 to 18 months",
      positionSizingNote: "Reduce crowding only through local manual journal review.",
      portfolioImpact: "Lowers power/cooling valuation risk while keeping theme exposure.",
      riskFlags: ["valuation_extension", "backlog_conversion"],
      evidenceIds: ["evid_20260514_cloud_ppa_release", "evid_20260512_ai_infra_multiples_table"],
      llmCritique: "Demand remains strong; the issue is setup quality after rerating.",
    },
  ] satisfies TradePlanView[],
  portfolioSnapshot: [
    {
      ticker: "NVDA",
      company: "NVIDIA",
      segment: "AI accelerators",
      weight: "12.0%",
      advisoryAction: "watch",
      riskFlags: ["hbm_allocation", "export_control"],
      linkedTradePlanId: "tpln_20260516_nvda_accumulate_pullback",
    },
    {
      ticker: "TSM",
      company: "Taiwan Semiconductor Manufacturing Company",
      segment: "Foundry / CoWoS / semicap",
      weight: "7.7%",
      advisoryAction: "accumulate",
      riskFlags: ["geopolitical"],
      linkedTradePlanId: "tpln_20260516_tsm_add_cowos",
    },
    {
      ticker: "VRT",
      company: "Vertiv",
      segment: "Power / grid / cooling",
      weight: "6.8%",
      advisoryAction: "trim",
      riskFlags: ["valuation_extension"],
      linkedTradePlanId: "tpln_20260516_vrt_trim_strength",
    },
    {
      ticker: "MSFT",
      company: "Microsoft",
      segment: "Cloud platform",
      weight: "7.3%",
      advisoryAction: "hold",
      riskFlags: ["capex_duration"],
      linkedTradePlanId: "tpln_20260516_msft_hold_capex_monitor",
    },
  ] satisfies PortfolioExposureView[],
  priceTargetScenarios: [
    {
      ticker: "NVDA",
      bear: "760",
      base: "980",
      bull: "1180",
      horizon: "6 to 18 months",
      evidenceIds: ["evid_20260512_ai_infra_multiples_table", "evid_20260515_hbm_supplier_checks"],
      riskFlags: ["export_control", "hbm_allocation"],
      invalidationCondition: "Shipment assumptions fall on HBM or policy constraints.",
    },
    {
      ticker: "TSM",
      bear: "142",
      base: "185",
      bull: "220",
      horizon: "9 to 24 months",
      evidenceIds: ["evid_20260515_tsm_cowos_capex_note"],
      riskFlags: ["geopolitical", "cowos_ramp_timing"],
      invalidationCondition: "Advanced packaging expansion misses milestones.",
    },
    {
      ticker: "VRT",
      bear: "82",
      base: "108",
      bull: "132",
      horizon: "6 to 18 months",
      evidenceIds: ["evid_20260514_cloud_ppa_release", "evid_20260512_ai_infra_multiples_table"],
      riskFlags: ["valuation_extension", "cooling_margin"],
      invalidationCondition: "Backlog or margin evidence weakens after valuation rerating.",
    },
  ] satisfies PriceTargetScenarioView[],
  entryExitLevels: [
    {
      ticker: "NVDA",
      entryZone: "880-910",
      addZone: "820-850",
      trimZone: "1080-1120",
      basis: "mock deterministic levels",
      evidenceIds: ["evid_20260516_mock_price_marks"],
      riskFlags: ["hbm_allocation", "export_control"],
    },
    {
      ticker: "TSM",
      entryZone: "164-170",
      addZone: "152-158",
      trimZone: "198-205",
      basis: "mock deterministic levels",
      evidenceIds: ["evid_20260516_mock_price_marks"],
      riskFlags: ["geopolitical"],
    },
    {
      ticker: "VRT",
      entryZone: "91-96",
      addZone: "84-88",
      trimZone: "118-125",
      basis: "mock deterministic levels",
      evidenceIds: ["evid_20260516_mock_price_marks"],
      riskFlags: ["valuation_extension"],
    },
  ] satisfies EntryExitLevelView[],
  correlationExposures: [
    {
      cluster: "Accelerator and custom silicon",
      tickers: ["NVDA", "AMD", "AVGO", "MRVL"],
      weight: "27.9%",
      note: "Crowding elevated; HBM and export-control evidence gate all fresh exposure.",
    },
    {
      cluster: "Foundry, semicap, HBM",
      tickers: ["TSM", "ASML", "MU"],
      weight: "17.1%",
      note: "Second-order bottleneck exposure offsets pure accelerator concentration.",
    },
    {
      cluster: "Power, grid, cooling",
      tickers: ["VRT", "ETN", "PWR", "CEG"],
      weight: "19.6%",
      note: "Demand strong, but valuation and project timing risk require review.",
    },
  ],
  llmAnalystNotes: [
    {
      noteId: "llm_note_20260516_chief",
      role: "chief_analyst",
      tickerOrSegment: "AI infrastructure stack",
      summary:
        "The strongest setup remains bottleneck ownership, not generic AI exposure. Separate capacity beneficiaries from capex spenders.",
      confidence: "0.78",
      evidenceIds: ["evid_20260516_cloud_capex_comp_sheet", "evid_20260515_tsm_cowos_capex_note"],
      modelRunId: "mrun_20260516_brief_summarize_001",
    },
    {
      noteId: "llm_note_20260516_export",
      role: "risk_regime_reviewer",
      tickerOrSegment: "Sovereign AI / export controls",
      summary:
        "Export-control risk is thesis-relevant for accelerator revenue timing and must stay visible on every NVDA/AMD review.",
      confidence: "0.72",
      evidenceIds: ["evid_20260513_export_control_rule"],
      modelRunId: "mrun_20260516_risk_review_001",
    },
  ] satisfies LlmAnalystNoteView[],
  journalReviews: [
    {
      journalId: "jrn_20260516_vrt_review",
      ticker: "VRT",
      status: "completed local review",
      entryExit: "Trim note reviewed after valuation rerating",
      realizedUnrealizedPnl: "Mock realized/unrealized PnL: +4.2%",
      exitReason: "Valuation extension after demand confirmation",
      mistakeClassification: "none; discipline review",
      postTradeLlmReview:
        "The review followed the plan but should track backlog conversion before further trimming.",
      segment: "Power / grid / cooling",
      catalystType: "power capacity",
      evidenceIds: ["evid_20260514_cloud_ppa_release", "evid_20260516_manual_journal_entries"],
    },
    {
      journalId: "jrn_20260516_tsm_intended",
      ticker: "TSM",
      status: "intended local note",
      entryExit: "Planning note for entry zone review",
      realizedUnrealizedPnl: "Mock realized/unrealized PnL: not applicable",
      exitReason: "Open setup",
      mistakeClassification: "pending outcome",
      postTradeLlmReview:
        "Do not upgrade if the packaging ramp evidence becomes stale before the manual decision.",
      segment: "Foundry / CoWoS / semicap",
      catalystType: "capacity expansion",
      evidenceIds: ["evid_20260515_tsm_cowos_capex_note", "evid_20260516_manual_journal_entries"],
    },
  ] satisfies JournalReviewView[],
  pnlSummary: {
    label: "Mock deterministic PnL summary",
    total: "+6.8%",
    bySegment: [
      ["AI accelerators", "+3.1%"],
      ["Foundry / CoWoS / semicap", "+1.4%"],
      ["Power / grid / cooling", "+2.3%"],
    ],
    evidenceIds: ["evid_20260516_manual_journal_entries", "evid_20260516_mock_price_marks"],
  },
};

export function evidenceById(evidenceId: string): EvidenceRef | undefined {
  return mockWorkstationData.evidenceItems.find(
    (item) => item.evidenceId === evidenceId,
  );
}

export function assessmentForTicker(ticker: string): EquityAssessmentView | undefined {
  return mockWorkstationData.equityAssessments.find(
    (assessment) => assessment.ticker === ticker.toUpperCase(),
  );
}

export function tradePlansForTicker(ticker: string): TradePlanView[] {
  return mockWorkstationData.openTradePlans.filter(
    (plan) => plan.ticker === ticker.toUpperCase(),
  );
}

export function priceScenarioForTicker(
  ticker: string,
): PriceTargetScenarioView | undefined {
  return mockWorkstationData.priceTargetScenarios.find(
    (scenario) => scenario.ticker === ticker.toUpperCase(),
  );
}

export function levelsForTicker(ticker: string): EntryExitLevelView | undefined {
  return mockWorkstationData.entryExitLevels.find(
    (levels) => levels.ticker === ticker.toUpperCase(),
  );
}

export function marketEventsForTicker(ticker: string): MarketEventView[] {
  return mockWorkstationData.marketEvents.filter((event) =>
    event.tickers.includes(ticker.toUpperCase()),
  );
}

export function portfolioExposureForTicker(
  ticker: string,
): PortfolioExposureView | undefined {
  return mockWorkstationData.portfolioSnapshot.find(
    (position) => position.ticker === ticker.toUpperCase(),
  );
}
