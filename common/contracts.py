"""Contracts 1 and 2 (Document 2, section 4.3). Contract 0 is graph/schema.yaml.

Contract 1 - InvestigationSpec: what the investigator wants the engine to do (filled from the graph).
Contract 2 - VariableResult: what the engine returns for one variable.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class InvestigationSpec:
    question: str
    concepts: list[str]
    variables: list[str]
    region: str
    period: list[str]                       # ["YYYY-MM", "YYYY-MM"]
    methods: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=lambda: [
        "trend_maps", "opposite_map", "clusters", "regional_series", "explanation"])
    # extra detail read from the graph so the UI can show the plan
    variable_details: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.question.strip():
            raise ValueError("question is empty")
        if not self.variables:
            raise ValueError("no variables in the plan")
        if len(self.period) != 2 or self.period[0] > self.period[1]:
            raise ValueError(f"bad period {self.period}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InvestigationSpec":
        return cls(**d)


@dataclass
class RegionalTrend:
    slope_per_decade: float | None
    ci95: list[float | None]
    p: float | None
    significant: bool
    tau: float | None = None
    n_months: int | None = None
    years_needed: float | None = None


@dataclass
class CellCounts:
    n: int
    n_tested: int
    sig_up: int
    sig_down: int
    pct_sig_area: float          # cos-latitude weighted, % of tested land area
    pct_sig_up_area: float
    pct_sig_down_area: float


@dataclass
class VariableResult:
    variable: str
    display_name: str
    unit: str                    # unit of the slope, per decade
    region: str
    period: list[str]
    regional: RegionalTrend
    cells: CellCounts
    method: str
    datasets: list[str]
    run_id: str
    warnings: list[str] = field(default_factory=list)
    synthetic: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VariableResult":
        d = dict(d)
        d["regional"] = RegionalTrend(**d["regional"])
        d["cells"] = CellCounts(**d["cells"])
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
