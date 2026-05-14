export type ValueChainStationId =
  | "compute"
  | "memory_packaging"
  | "foundry_equipment"
  | "power"
  | "grid_dc_build"
  | "networking"
  | "hyperscalers"
  | "frontier_adjacent"
  | "geopolitical_adjacent";

export type ValueChainStation = {
  id: ValueChainStationId;
  index: string;
  label: string;
  caption: string;
  subthemes: ValueChainSubtheme[];
};

export type ValueChainSubtheme = {
  tag: string;
  label: string;
  short: string;
};

export const valueChain: ValueChainStation[] = [
  {
    id: "compute",
    index: "01",
    label: "Compute",
    caption: "Accelerators and custom silicon — the heart of the cluster.",
    subthemes: [
      {
        tag: "ai_accelerators",
        label: "AI Accelerators",
        short: "GPUs / accelerators",
      },
      {
        tag: "accelerated_compute",
        label: "Accelerated Compute",
        short: "compute fabric",
      },
      {
        tag: "custom_silicon",
        label: "Custom Silicon",
        short: "ASICs / TPUs / Trainium",
      },
      {
        tag: "tensor_processing",
        label: "Tensor Processing",
        short: "TPU lineage",
      },
    ],
  },
  {
    id: "memory_packaging",
    index: "02",
    label: "Memory & Packaging",
    caption:
      "HBM stacks and advanced packaging — the binding constraint on GPU throughput.",
    subthemes: [
      {
        tag: "hbm_memory",
        label: "HBM Memory",
        short: "high-bandwidth stacks",
      },
      {
        tag: "advanced_packaging",
        label: "Advanced Packaging",
        short: "CoWoS / chiplets",
      },
      {
        tag: "compute_supply_chain",
        label: "Compute Supply Chain",
        short: "wafer-to-rack flow",
      },
    ],
  },
  {
    id: "foundry_equipment",
    index: "03",
    label: "Foundry & Equipment",
    caption: "Wafer production and the lithography that gates it.",
    subthemes: [
      {
        tag: "foundry_capacity",
        label: "Foundry Capacity",
        short: "leading-edge wafers",
      },
      { tag: "lithography", label: "Lithography", short: "EUV / High-NA" },
      {
        tag: "semiconductor_equipment",
        label: "Semi Equipment",
        short: "front-end tools",
      },
    ],
  },
  {
    id: "power",
    index: "04",
    label: "Power",
    caption:
      "Generation — nuclear, gas turbines, shale. The decade's hard ceiling.",
    subthemes: [
      { tag: "nuclear_power", label: "Nuclear", short: "baseload reactors" },
      {
        tag: "gas_turbines",
        label: "Gas Turbines",
        short: "GE Vernova / Siemens",
      },
      {
        tag: "marcellus_gas",
        label: "Marcellus Gas",
        short: "Appalachian shale",
      },
      {
        tag: "natural_gas_supply",
        label: "Natural Gas Supply",
        short: "feedstock",
      },
      {
        tag: "hyperscaler_ppa",
        label: "Hyperscaler PPAs",
        short: "direct power contracts",
      },
      {
        tag: "independent_power_producer",
        label: "Independent Power",
        short: "IPPs",
      },
    ],
  },
  {
    id: "grid_dc_build",
    index: "05",
    label: "Grid & DC Build",
    caption: "Transmission, distribution, electrical equipment, and cooling.",
    subthemes: [
      {
        tag: "transmission_buildout",
        label: "Transmission Buildout",
        short: "high-voltage build",
      },
      {
        tag: "grid_equipment",
        label: "Grid Equipment",
        short: "transformers / switchgear",
      },
      {
        tag: "electrical_distribution",
        label: "Electrical Distribution",
        short: "datacenter electrical",
      },
      {
        tag: "data_center_power",
        label: "Datacenter Power",
        short: "rack-level power",
      },
      {
        tag: "data_center_cooling",
        label: "Datacenter Cooling",
        short: "liquid / immersion",
      },
      { tag: "hvac", label: "HVAC", short: "thermal management" },
      { tag: "cooling", label: "Cooling", short: "rack thermal loop" },
    ],
  },
  {
    id: "networking",
    index: "06",
    label: "Networking",
    caption: "Datacenter fabrics — Infiniband, optics, switching.",
    subthemes: [
      {
        tag: "ai_networking",
        label: "AI Networking",
        short: "Infiniband / Ethernet",
      },
      {
        tag: "data_center_fabrics",
        label: "Datacenter Fabrics",
        short: "switching backbone",
      },
    ],
  },
  {
    id: "hyperscalers",
    index: "07",
    label: "Hyperscalers",
    caption: "Capex demand-side: who is spending the trillions.",
    subthemes: [
      {
        tag: "hyperscaler_capex",
        label: "Hyperscaler Capex",
        short: "Big Tech buildout",
      },
      { tag: "ai_cloud", label: "AI Cloud", short: "platform layer" },
      {
        tag: "enterprise_ai",
        label: "Enterprise AI",
        short: "model platforms",
      },
      {
        tag: "ai_data_centers",
        label: "AI Datacenters",
        short: "campus-scale",
      },
      {
        tag: "model_training",
        label: "Model Training",
        short: "frontier runs",
      },
      {
        tag: "model_platforms",
        label: "Model Platforms",
        short: "API / inference",
      },
      {
        tag: "trainium_infrastructure",
        label: "Trainium Infra",
        short: "AWS silicon",
      },
      { tag: "ai_research", label: "AI Research", short: "DeepMind / FAIR" },
      { tag: "autonomous_ai", label: "Autonomous AI", short: "robotics / FSD" },
    ],
  },
];

export const adjacentStations: ValueChainStation[] = [
  {
    id: "frontier_adjacent",
    index: "α",
    label: "Frontier Compute",
    caption: "Beyond classical silicon — held at arm's length.",
    subthemes: [
      {
        tag: "quantum_compute",
        label: "Quantum",
        short: "trapped-ion / superconducting",
      },
      {
        tag: "frontier_compute",
        label: "Frontier Compute",
        short: "experimental",
      },
    ],
  },
  {
    id: "geopolitical_adjacent",
    index: "β",
    label: "Geopolitical",
    caption: "China AI competition and export-control surface.",
    subthemes: [
      {
        tag: "china_ai_cloud",
        label: "China AI Cloud",
        short: "domestic platforms",
      },
      {
        tag: "geopolitical_ai_competition",
        label: "AI Competition",
        short: "national posture",
      },
      { tag: "export_controls", label: "Export Controls", short: "BIS regime" },
      { tag: "china_ai", label: "China AI", short: "PRC ecosystem" },
    ],
  },
];
