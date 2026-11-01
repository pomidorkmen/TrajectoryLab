"""Example empirical power-law model for controlled software testing only."""

from __future__ import annotations

from trajectory_lab.core.drag.base import BaseDragModel
from trajectory_lab.core.state import FlowState


class ReynoldsPowerExample(BaseDragModel):
    """Return Cd=a*Re**b with explicitly user-supplied parameters."""

    def __init__(self, a: float = 1.0, b: float = -0.2) -> None:
        self.a = a
        self.b = b

    def cd(self, state: FlowState) -> float:
        if state.reynolds <= 0:
            raise ValueError("ReynoldsPowerExample requires Re > 0")
        return self.a * state.reynolds**self.b

    def describe(self) -> dict[str, object]:
        return {
            "id": "example.reynolds_power",
            "name": "Example Reynolds power law",
            "version": "1.0.0",
            "author": "TrajectoryLab example",
            "source": "User-defined demonstration formula",
            "formula": f"Cd = {self.a:.12g} * Re^{self.b:.12g}",
            "a": self.a,
            "b": self.b,
            "validity": {"reynolds_min": 0.1, "reynolds_max": 1000.0},
        }
