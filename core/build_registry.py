from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuildStep:
    module_name: str
    label: str


BUILD_STEPS: tuple[BuildStep, ...] = (
    BuildStep("main", "data sources"),
    BuildStep("BuildingTypology", "TABULA building typology"),
    BuildStep("EnergySystem", "TABULA energy systems"),
    BuildStep("CalculationBuildingSet", "TABULA calculation building set"),
    BuildStep("IWU_NWG", "IWU NWG"),
    BuildStep("Altbauatlas", "Altbauatlas"),
    BuildStep("Epd", "EPD"),
    BuildStep("Crrem", "CRREM"),
)
