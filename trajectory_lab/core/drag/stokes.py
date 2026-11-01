"""Stokes drag correlation for creeping flow around a rigid sphere."""

from __future__ import annotations

from trajectory_lab.core.drag.base import BaseDragModel
from trajectory_lab.core.state import FlowState


class StokesSphere(BaseDragModel):
    """Stokes law, Cd=24/Re; valid in the creeping-flow limit Re < 1."""

    # Cd=24/Re is unbounded as Re tends to zero; use only a finite overflow guard.
    cd_upper_limit = 1.0e12

    def cd(self, state: FlowState) -> float:
        if state.reynolds <= 0:
            raise ValueError("Stokes correlation is undefined at Re=0")
        return 24.0 / state.reynolds

    def describe(self) -> dict[str, object]:
        return {
            "id": "drag.stokes_sphere",
            "name": "Stokes sphere",
            "version": "1.1.0",
            "author": "George G. Stokes (1851)",
            "source": "Classical creeping-flow solution",
            "formula": "Cd = 24/Re",
            "validity": {
                "reynolds_min": 0.0,
                "reynolds_min_inclusive": False,
                "reynolds_max": 1.0,
                "reynolds_max_inclusive": False,
            },
            "geometry": "rigid sphere",
            "cd_validation_limit": "model-specific finite guard; exact Stokes Cd may exceed 100",
        }

    def validity_range(self) -> tuple[float, float]:
        return (0.0, 1.0)
