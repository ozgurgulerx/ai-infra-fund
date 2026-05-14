export type WatchlistEntry = {
  ticker: string;
  companyName: string;
  themes: string[];
  sectorTags: string[];
  priority: "critical" | "high" | "medium" | "low";
  sourceUrls: string[];
};

export const watchlist: WatchlistEntry[] = [
  {
    ticker: "NVDA",
    companyName: "NVIDIA",
    themes: ["ai_accelerators", "accelerated_compute", "data_center_capex"],
    sectorTags: ["semiconductors", "ai_infrastructure"],
    priority: "critical",
    sourceUrls: [
      "https://www.nvidia.com/en-us/data-center/",
      "https://investor.nvidia.com/",
    ],
  },
  {
    ticker: "MSFT",
    companyName: "Microsoft",
    themes: [
      "ai_cloud",
      "hyperscaler_capex",
      "enterprise_ai",
      "model_platforms",
    ],
    sectorTags: ["cloud_platforms", "software"],
    priority: "critical",
    sourceUrls: [
      "https://azure.microsoft.com/en-us/products/ai-services",
      "https://www.microsoft.com/en-us/investor",
    ],
  },
  {
    ticker: "GOOGL",
    companyName: "Alphabet",
    themes: [
      "ai_cloud",
      "hyperscaler_capex",
      "ai_research",
      "tensor_processing",
    ],
    sectorTags: ["cloud_platforms", "internet_platforms"],
    priority: "high",
    sourceUrls: ["https://cloud.google.com/ai", "https://abc.xyz/investor/"],
  },
  {
    ticker: "AMZN",
    companyName: "Amazon",
    themes: [
      "hyperscaler_capex",
      "ai_cloud",
      "custom_silicon",
      "trainium_infrastructure",
      "data_center_power",
    ],
    sectorTags: ["cloud_platforms", "internet_platforms", "ai_infrastructure"],
    priority: "critical",
    sourceUrls: [
      "https://ir.aboutamazon.com/overview/",
      "https://aws.amazon.com/machine-learning/trainium/",
    ],
  },
  {
    ticker: "META",
    companyName: "Meta Platforms",
    themes: [
      "hyperscaler_capex",
      "custom_silicon",
      "model_training",
      "ai_data_centers",
    ],
    sectorTags: ["internet_platforms", "ai_infrastructure", "social_platforms"],
    priority: "critical",
    sourceUrls: [
      "https://investor.atmeta.com/home/default.aspx",
      "https://about.fb.com/news/2024/04/introducing-our-next-generation-infrastructure-for-ai/",
    ],
  },
  {
    ticker: "TSLA",
    companyName: "Tesla",
    themes: [
      "hyperscaler_capex",
      "autonomous_ai",
      "model_training",
      "data_center_power",
    ],
    sectorTags: ["automotive", "ai_infrastructure", "robotics"],
    priority: "high",
    sourceUrls: ["https://ir.tesla.com/"],
  },
  {
    ticker: "AMD",
    companyName: "Advanced Micro Devices",
    themes: ["ai_accelerators", "compute_supply_chain"],
    sectorTags: ["semiconductors", "ai_infrastructure"],
    priority: "high",
    sourceUrls: [
      "https://www.amd.com/en/solutions/data-center/ai.html",
      "https://ir.amd.com/",
    ],
  },
  {
    ticker: "TSM",
    companyName: "Taiwan Semiconductor Manufacturing",
    themes: ["advanced_packaging", "compute_supply_chain", "foundry_capacity"],
    sectorTags: ["semiconductors", "manufacturing"],
    priority: "high",
    sourceUrls: [
      "https://www.tsmc.com/english",
      "https://investor.tsmc.com/english",
    ],
  },
  {
    ticker: "SMICY",
    companyName: "Semiconductor Manufacturing International Corporation",
    themes: [
      "foundry_capacity",
      "compute_supply_chain",
      "geopolitical_ai_competition",
      "export_controls",
    ],
    sectorTags: ["semiconductors", "foundry", "china_ai"],
    priority: "medium",
    sourceUrls: ["https://www.smics.com/en/site/investor"],
  },
  {
    ticker: "INTC",
    companyName: "Intel",
    themes: [
      "advanced_packaging",
      "compute_supply_chain",
      "foundry_capacity",
      "ai_accelerators",
    ],
    sectorTags: ["semiconductors", "manufacturing", "foundry"],
    priority: "high",
    sourceUrls: ["https://www.intc.com/"],
  },
  {
    ticker: "BIDU",
    companyName: "Baidu",
    themes: [
      "china_ai_cloud",
      "model_platforms",
      "geopolitical_ai_competition",
    ],
    sectorTags: ["internet_platforms", "cloud_platforms", "china_ai"],
    priority: "medium",
    sourceUrls: [
      "https://ir.baidu.com/",
      "https://cloud.baidu.com/en/index.html",
    ],
  },
  {
    ticker: "ASML",
    companyName: "ASML Holding",
    themes: ["lithography", "compute_supply_chain", "semiconductor_equipment"],
    sectorTags: ["semiconductor_equipment", "manufacturing"],
    priority: "high",
    sourceUrls: ["https://www.asml.com/en/investors"],
  },
  {
    ticker: "AVGO",
    companyName: "Broadcom",
    themes: ["ai_networking", "custom_silicon", "infrastructure_software"],
    sectorTags: ["semiconductors", "networking", "software"],
    priority: "high",
    sourceUrls: ["https://investors.broadcom.com/"],
  },
  {
    ticker: "ANET",
    companyName: "Arista Networks",
    themes: ["ai_networking", "data_center_fabrics"],
    sectorTags: ["networking", "ai_infrastructure"],
    priority: "medium",
    sourceUrls: ["https://investors.arista.com/"],
  },
  {
    ticker: "VRT",
    companyName: "Vertiv",
    themes: ["data_center_power", "cooling", "ai_data_centers"],
    sectorTags: ["electrical_equipment", "data_center_infrastructure"],
    priority: "medium",
    sourceUrls: ["https://investors.vertiv.com/"],
  },
  {
    ticker: "IONQ",
    companyName: "IonQ",
    themes: ["quantum_compute", "frontier_compute"],
    sectorTags: ["quantum_technology", "deep_tech"],
    priority: "low",
    sourceUrls: ["https://investors.ionq.com/"],
  },
  {
    ticker: "MU",
    companyName: "Micron Technology",
    themes: ["hbm_memory", "compute_supply_chain", "ai_accelerators"],
    sectorTags: ["semiconductors", "memory", "ai_infrastructure"],
    priority: "high",
    sourceUrls: [
      "https://investors.micron.com/",
      "https://www.micron.com/products/memory/hbm",
    ],
  },
  {
    ticker: "CEG",
    companyName: "Constellation Energy",
    themes: ["nuclear_power", "data_center_power", "hyperscaler_ppa"],
    sectorTags: ["utilities", "independent_power", "ai_infrastructure"],
    priority: "high",
    sourceUrls: ["https://investors.constellationenergy.com/"],
  },
  {
    ticker: "VST",
    companyName: "Vistra",
    themes: [
      "nuclear_power",
      "data_center_power",
      "independent_power_producer",
    ],
    sectorTags: ["utilities", "independent_power", "ai_infrastructure"],
    priority: "high",
    sourceUrls: ["https://investor.vistracorp.com/"],
  },
  {
    ticker: "TLN",
    companyName: "Talen Energy",
    themes: ["nuclear_power", "data_center_power", "hyperscaler_ppa"],
    sectorTags: ["utilities", "independent_power", "ai_infrastructure"],
    priority: "medium",
    sourceUrls: ["https://www.talenenergy.com/investors/"],
  },
  {
    ticker: "GEV",
    companyName: "GE Vernova",
    themes: ["gas_turbines", "grid_equipment", "data_center_power"],
    sectorTags: [
      "electrical_equipment",
      "power_generation",
      "ai_infrastructure",
    ],
    priority: "high",
    sourceUrls: ["https://www.gevernova.com/investors"],
  },
  {
    ticker: "ETN",
    companyName: "Eaton",
    themes: ["data_center_power", "electrical_distribution", "grid_equipment"],
    sectorTags: ["electrical_equipment", "industrials", "ai_infrastructure"],
    priority: "high",
    sourceUrls: [
      "https://www.eaton.com/us/en-us/company/investor-relations.html",
    ],
  },
  {
    ticker: "PWR",
    companyName: "Quanta Services",
    themes: ["transmission_buildout", "grid_equipment", "data_center_power"],
    sectorTags: [
      "construction_services",
      "utilities_infrastructure",
      "ai_infrastructure",
    ],
    priority: "medium",
    sourceUrls: ["https://investors.quantaservices.com/"],
  },
  {
    ticker: "EQT",
    companyName: "EQT Corporation",
    themes: ["marcellus_gas", "data_center_power", "natural_gas_supply"],
    sectorTags: ["energy", "natural_gas", "ai_infrastructure"],
    priority: "medium",
    sourceUrls: ["https://ir.eqt.com/"],
  },
  {
    ticker: "TT",
    companyName: "Trane Technologies",
    themes: ["data_center_cooling", "hvac", "ai_data_centers"],
    sectorTags: ["industrials", "thermal_management", "ai_infrastructure"],
    priority: "medium",
    sourceUrls: ["https://investors.tranetechnologies.com/"],
  },
];

export const tickersByStation = (
  stationSubthemeTags: ReadonlySet<string>,
): WatchlistEntry[] =>
  watchlist.filter((entry) =>
    entry.themes.some((tag) => stationSubthemeTags.has(tag)),
  );
