"""Constant-Cd quadratic-resistance model."""

from __future__ import annotations

from dataclasses import dataclass

from trajectory_lab.core.drag.base import BaseDragModel, validate_cd
from trajectory_lab.core.state import FlowState


@dataclass(frozen=True, slots=True)
class ConstantCdSphere(BaseDragModel):
    """Constant drag coefficient, intended as a controlled comparison model."""

    coefficient: float = 0.44

    def __post_init__(self) -> None:
        validate_cd(self.coefficient)

    def cd(self, state: FlowState) -> float:
        del state
        return self.coefficient

    def fingerprint_payload(self) -> dict[str, object]:
        return {"metadata": self.describe(), "coefficient": self.coefficient}

    def describe(self) -> dict[str, object]:
        return {
            "id": "drag.constant_cd_sphere",
            "name": "Constant Cd sphere",
            "version": "1.0.0",
            "author": "User parameter",
            "source": "User-defined constant coefficient",
            "formula": f"Cd = {self.coefficient:.12g}",
            "validity": {
                "reynolds_min": 0.0,
                "reynolds_min_inclusive": True,
                "reynolds_max": None,
                "note": "no intrinsic Reynolds-number limit",
            },
            "geometry": "sphere reference area",
        }
