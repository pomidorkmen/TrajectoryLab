"""Example extension model: constant Cd for reference comparisons."""

from __future__ import annotations

from trajectory_lab.core.drag.base import BaseDragModel
from trajectory_lab.core.state import FlowState


class ConstantCdExample(BaseDragModel):
    """A deliberately simple user-model example."""

    def __init__(self, coefficient: float = 0.47) -> None:
        self.coefficient = coefficient

    def cd(self, state: FlowState) -> float:
        del state
        return self.coefficient

    def describe(self) -> dict[str, object]:
        return {
            "id": "example.constant_cd",
            "name": "Example constant Cd",
            "version": "1.0.0",
            "author": "TrajectoryLab example",
            "source": "Demonstration only",
            "validity": {"reynolds_min": 0.0, "reynolds_max": 1e6},
        }
