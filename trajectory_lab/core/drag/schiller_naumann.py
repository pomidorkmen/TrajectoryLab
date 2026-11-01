"""Schiller--Naumann sphere drag correlation."""

from __future__ import annotations

from trajectory_lab.core.drag.base import BaseDragModel
from trajectory_lab.core.state import FlowState


class SchillerNaumannSphere(BaseDragModel):
    # The 24/Re asymptote legitimately exceeds 100 at sufficiently small Re.
    cd_upper_limit = 1.0e12

    """Cd=24/Re*(1+0.15*Re**0.687), supported here for 0 < Re < 800."""

    def cd(self, state: FlowState) -> float:
        re = state.reynolds
        if re <= 0:
            raise ValueError("Schiller-Naumann correlation is undefined at Re=0")
        return 24.0 / re * (1.0 + 0.15 * re**0.687)

    def describe(self) -> dict[str, object]:
        return {
            "id": "drag.schiller_naumann_sphere",
            "name": "Schiller-Naumann sphere",
            "version": "1.1.0",
            "author": "Schiller & Naumann (1933)",
            "source": "Schiller & Naumann (1933), smooth spherical particles",
            "formula": "Cd = 24/Re * (1 + 0.15*Re^0.687)",
            "validity": {
                "reynolds_min": 0.0,
                "reynolds_min_inclusive": False,
                "reynolds_max": 800.0,
                "reynolds_max_inclusive": False,
            },
            "geometry": "rigid sphere",
        }

    def validity_range(self) -> tuple[float, float]:
        return (0.0, 800.0)
