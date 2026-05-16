from __future__ import annotations

from enum import Enum

from .common import normalize_tuple, require_non_empty_tuple, require_text


class Segment(str, Enum):
    AI_MODEL_PROGRESS = "ai_model_progress"
    HYPERSCALER_CAPEX = "hyperscaler_capex"
    AI_HARDWARE_ACCELERATORS = "ai_hardware_accelerators"
    MEMORY_HBM = "memory_hbm"
    ADVANCED_PACKAGING_COWOS = "advanced_packaging_cowos"
    FOUNDRY_SEMICONDUCTOR_EQUIPMENT = "foundry_semiconductor_equipment"
    NETWORKING_INTERCONNECT = "networking_interconnect"
    DATACENTER_PROVIDERS = "datacenter_providers"
    POWER_GRID = "power_grid"
    COOLING_ELECTRICAL_INFRASTRUCTURE = "cooling_electrical_infrastructure"
    SOVEREIGN_AI_EXPORT_CONTROLS = "sovereign_ai_export_controls"
    SOFTWARE_MONETIZATION = "software_monetization"


CORE_AI_INFRASTRUCTURE_SEGMENTS: tuple[Segment, ...] = tuple(Segment)

SEGMENT_THEME_ALIASES: dict[str, Segment] = {
    "ai_model_progress": Segment.AI_MODEL_PROGRESS,
    "model_capability": Segment.AI_MODEL_PROGRESS,
    "frontier_models": Segment.AI_MODEL_PROGRESS,
    "hyperscaler_capex": Segment.HYPERSCALER_CAPEX,
    "cloud_capex": Segment.HYPERSCALER_CAPEX,
    "capex": Segment.HYPERSCALER_CAPEX,
    "ai_hardware": Segment.AI_HARDWARE_ACCELERATORS,
    "ai_hardware_accelerators": Segment.AI_HARDWARE_ACCELERATORS,
    "accelerators": Segment.AI_HARDWARE_ACCELERATORS,
    "gpu": Segment.AI_HARDWARE_ACCELERATORS,
    "gpus": Segment.AI_HARDWARE_ACCELERATORS,
    "memory_hbm": Segment.MEMORY_HBM,
    "hbm": Segment.MEMORY_HBM,
    "dram": Segment.MEMORY_HBM,
    "advanced_packaging": Segment.ADVANCED_PACKAGING_COWOS,
    "advanced_packaging_cowos": Segment.ADVANCED_PACKAGING_COWOS,
    "cowos": Segment.ADVANCED_PACKAGING_COWOS,
    "foundry": Segment.FOUNDRY_SEMICONDUCTOR_EQUIPMENT,
    "foundries": Segment.FOUNDRY_SEMICONDUCTOR_EQUIPMENT,
    "semiconductor_equipment": Segment.FOUNDRY_SEMICONDUCTOR_EQUIPMENT,
    "networking": Segment.NETWORKING_INTERCONNECT,
    "interconnect": Segment.NETWORKING_INTERCONNECT,
    "networking_interconnect": Segment.NETWORKING_INTERCONNECT,
    "data_centers": Segment.DATACENTER_PROVIDERS,
    "datacenter": Segment.DATACENTER_PROVIDERS,
    "datacenter_providers": Segment.DATACENTER_PROVIDERS,
    "power": Segment.POWER_GRID,
    "power_grid": Segment.POWER_GRID,
    "grid": Segment.POWER_GRID,
    "cooling": Segment.COOLING_ELECTRICAL_INFRASTRUCTURE,
    "electrical_infrastructure": Segment.COOLING_ELECTRICAL_INFRASTRUCTURE,
    "cooling_electrical_infrastructure": Segment.COOLING_ELECTRICAL_INFRASTRUCTURE,
    "sovereign_ai": Segment.SOVEREIGN_AI_EXPORT_CONTROLS,
    "export_controls": Segment.SOVEREIGN_AI_EXPORT_CONTROLS,
    "national_security": Segment.SOVEREIGN_AI_EXPORT_CONTROLS,
    "software_monetization": Segment.SOFTWARE_MONETIZATION,
    "ai_revenue": Segment.SOFTWARE_MONETIZATION,
}


def normalize_segment(value: Segment | str) -> Segment:
    if isinstance(value, Segment):
        return value
    key = _segment_key(value)
    if key in SEGMENT_THEME_ALIASES:
        return SEGMENT_THEME_ALIASES[key]
    try:
        return Segment(key)
    except ValueError as exc:
        raise ValueError(f"segment must be one of {[segment.value for segment in Segment]}") from exc


def segments_from_themes(themes: object) -> tuple[Segment, ...]:
    segments: list[Segment] = []
    for theme in normalize_tuple(themes, "themes"):
        key = _segment_key(theme)
        segment = SEGMENT_THEME_ALIASES.get(key)
        if segment is None:
            continue
        if segment not in segments:
            segments.append(segment)
    return require_non_empty_tuple(tuple(segments), "segments")


def _segment_key(value: object) -> str:
    return require_text(str(value), "segment").strip().lower().replace("-", "_").replace(" ", "_")
