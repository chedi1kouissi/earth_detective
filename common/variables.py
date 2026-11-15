"""Reference description of the datasets and variables we use (Document 2, section 5.2).

This table is written by humans. It is used for two things:
1. the download / preprocessing pipeline (phase 1) needs it before any graph exists;
2. validate_graph compares the recipes written by the curator agent against it
   ("this table is what we use to check its work").
The investigation itself reads recipes from the graph, not from here.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetSpec:
    key: str                 # short key used in folder names: merra2, imerg, gldas, modis_ndvi
    short_name: str          # CMR short name
    version: str             # CMR version
    cmr_concept_id: str      # checked against CMR on 2026-11-14
    provider: str
    native_res: str
    file_format: str


@dataclass(frozen=True)
class VariableSpec:
    id: str                  # our short id, used everywhere in code: t2m, precip, ...
    display_name: str
    dataset: str             # DatasetSpec.key
    name_in_file: str
    group: str | None
    unit_native: str
    unit_target: str
    conversion: str          # human-readable conversion rule
    kind: str                # state | flux | index
    definition_for_students: str
    cf_standard_name: str | None = None
    concepts: tuple[str, ...] = field(default_factory=tuple)


DATASETS: dict[str, DatasetSpec] = {
    "merra2": DatasetSpec("merra2", "M2TMNXSLV", "5.12.4", "C1276812859-GES_DISC", "GES_DISC",
                          "0.5 x 0.625 deg", "netCDF4"),
    "imerg": DatasetSpec("imerg", "GPM_3IMERGM", "07", "C2723754851-GES_DISC", "GES_DISC",
                         "0.1 deg", "HDF5"),
    "gldas": DatasetSpec("gldas", "GLDAS_NOAH025_M", "2.1", "C1342986036-GES_DISC", "GES_DISC",
                         "0.25 deg", "netCDF4"),
    "modis_ndvi": DatasetSpec("modis_ndvi", "MOD13C2", "061", "C2565788914-LPCLOUD", "LPCLOUD",
                              "0.05 deg", "HDF4"),
}

VARIABLES: dict[str, VariableSpec] = {
    "t2m": VariableSpec(
        "t2m", "Air temperature at 2 m", "merra2", "T2M", None, "K", "degC",
        "value - 273.15", "state",
        "How warm the air is about 2 metres above the ground, like a thermometer in a garden.",
        "air_temperature", ("surface heating", "evaporative demand")),
    "precip": VariableSpec(
        "precip", "Precipitation", "imerg", "precipitation", "Grid", "mm/hr", "mm/month",
        "value * 24 * days_in_month", "flux",
        "How much water falls from the sky as rain or snow in a month.",
        "precipitation_flux", ("water availability", "water cycle", "drought")),
    "soil_moisture": VariableSpec(
        "soil_moisture", "Soil moisture (0-10 cm)", "gldas", "SoilMoi0_10cm_inst", None,
        "kg m-2", "kg m-2", "none (1 kg/m2 = 1 mm of water)", "state",
        "How much water is held in the top 10 cm of soil, where many plant roots drink.",
        "mass_content_of_water_in_soil_layer", ("drought", "water availability",
                                                "vegetation health")),
    "et": VariableSpec(
        "et", "Evapotranspiration", "gldas", "Evap_tavg", None, "kg m-2 s-1", "mm/day",
        "value * 86400", "flux",
        "Water going from the ground and plants into the air (evaporation + plants 'sweating').",
        "water_evapotranspiration_flux", ("water cycle", "evaporative demand",
                                          "water availability")),
    "ndvi": VariableSpec(
        "ndvi", "Vegetation greenness (NDVI)", "modis_ndvi", "CMG 0.05 Deg Monthly NDVI", None,
        "1 (stored as integer, scale 0.0001)", "NDVI units", "value * 0.0001", "index",
        "A number from -1 to 1 that says how green and alive the plants are, seen from space.",
        "normalized_difference_vegetation_index", ("vegetation health", "drought")),
}

VARIABLE_ORDER = ["t2m", "precip", "soil_moisture", "et", "ndvi"]

CONCEPTS: dict[str, tuple[str, ...]] = {
    # concept -> synonyms (lower case). Used by the seed backup and to check the curator.
    # A synonym belongs to ONE concept only (validate_graph rejects duplicates).
    "surface heating": ("hotter", "warmer", "warming", "heat", "temperature", "hot"),
    "water availability": ("water", "wetter", "drier", "dry", "water scarcity", "scarcer",
                           "rainfall"),
    "drought": ("droughts", "drying", "water stress", "aridity", "arid", "dry spell"),
    "vegetation health": ("green", "greenness", "plants", "vegetation", "crops", "greening",
                          "browning"),
    "evaporative demand": ("evaporation", "thirsty air", "evapotranspiration"),
    "water cycle": ("hydrological cycle", "rain", "precipitation"),
}

SUBREGIONS: dict[str, tuple[str, tuple[float, float, float, float]]] = {
    # id -> (name, (west, south, east, north)). Boxes, not borders: good enough at 1 degree.
    "iberia": ("Iberian Peninsula", (-10.0, 36.0, 3.0, 44.0)),
    "maghreb": ("Maghreb", (-10.0, 28.0, 12.0, 37.0)),
    "tunisia": ("Tunisia", (7.0, 30.0, 12.0, 38.0)),
    "nile_delta": ("Nile Delta and Lower Egypt", (28.0, 27.0, 34.0, 32.0)),
    "levant": ("Levant", (34.0, 29.0, 40.0, 37.0)),
    "sahara_margin": ("Sahara margin", (-10.0, 25.0, 30.0, 30.0)),
    "italy_balkans": ("Italy and the Balkans", (7.0, 37.0, 28.0, 47.0)),
    "anatolia": ("Anatolia", (26.0, 36.0, 40.0, 42.0)),
}
