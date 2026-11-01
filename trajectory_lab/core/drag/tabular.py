"""Tabulated Cd(Re) model with explicit log-log interpolation and range policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np
from scipy.interpolate import PchipInterpolator

from trajectory_lab.core.drag.base import BaseDragModel
from trajectory_lab.core.state import FlowState

Interpolation = Literal["linear", "log-log", "cubic-log-log"]
Extrapolation = Literal["clamp", "extrapolate", "error"]


@dataclass(frozen=True, slots=True)
class TabularDragModel(BaseDragModel):
    """Cd(Re) table with linear or logarithmic axes interpolation.

    Default interpolation is log-log: interpolate log(Cd) linearly against
    log(Re), which is suitable for data spanning multiple decades and exactly
    preserves power laws between tabulated nodes.
    """

    cd_upper_limit = 1.0e12  # User tables may contain physically valid creeping-flow Cd > 100.

    points: Sequence[tuple[float, float]]
    interpolation: Interpolation = "log-log"
    extrapolation: Extrapolation = "error"
    model_name: str = "User tabular sphere model"
    model_version: str = "1.1.0"

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("A tabular model requires at least two (Re, Cd) points")
        re_values = np.asarray([point[0] for point in self.points], dtype=float)
        cd_values = np.asarray([point[1] for point in self.points], dtype=float)
        if not np.all(np.isfinite(re_values)) or not np.all(np.isfinite(cd_values)):
            raise ValueError("Tabular model points must be finite")
        if np.any(re_values <= 0) or np.any(cd_values <= 0) or np.any(cd_values >= 1.0e12):
            raise ValueError("Re and Cd table values must be positive; Cd must be below 1e12")
        if np.any(np.diff(re_values) <= 0):
            raise ValueError("Re table values must be strictly increasing")
        if self.interpolation not in ("linear", "log-log", "cubic-log-log"):
            raise ValueError("Interpolation must be 'linear', 'log-log' or 'cubic-log-log'")
        if self.extrapolation not in ("clamp", "extrapolate", "error"):
            raise ValueError("Extrapolation must be 'clamp', 'extrapolate' or 'error'")

    @property
    def _arrays(self) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.asarray([point[0] for point in self.points], dtype=float),
            np.asarray([point[1] for point in self.points], dtype=float),
        )

    def cd(self, state: FlowState) -> float:
        re_values, cd_values = self._arrays
        re = state.reynolds
        if re <= 0:
            raise ValueError("Tabular drag model requires Re > 0")
        outside = re < re_values[0] or re > re_values[-1]
        if outside and self.extrapolation == "error":
            raise ValueError(
                f"Re={re:g} outside table range [{re_values[0]:g}, {re_values[-1]:g}]"
            )
        if outside and self.extrapolation == "clamp":
            return float(cd_values[0] if re < re_values[0] else cd_values[-1])

        if self.interpolation == "linear":
            if outside:
                if re < re_values[0]:
                    slope = (cd_values[1] - cd_values[0]) / (re_values[1] - re_values[0])
                    return float(cd_values[0] + slope * (re - re_values[0]))
                slope = (cd_values[-1] - cd_values[-2]) / (re_values[-1] - re_values[-2])
                return float(cd_values[-1] + slope * (re - re_values[-1]))
            return float(np.interp(re, re_values, cd_values))

        log_re = np.log(re_values)
        log_cd = np.log(cd_values)
        target = math_log(re)
        if self.interpolation == "cubic-log-log":
            interpolator = PchipInterpolator(log_re, log_cd, extrapolate=True)
            return float(np.exp(interpolator(target)))
        return float(np.exp(np.interp(target, log_re, log_cd))) if not outside else self._log_extrapolate(
            target, log_re, log_cd
        )

    @staticmethod
    def _log_extrapolate(target: float, log_re: np.ndarray, log_cd: np.ndarray) -> float:
        if target < log_re[0]:
            slope = (log_cd[1] - log_cd[0]) / (log_re[1] - log_re[0])
            result = log_cd[0] + slope * (target - log_re[0])
        else:
            slope = (log_cd[-1] - log_cd[-2]) / (log_re[-1] - log_re[-2])
            result = log_cd[-1] + slope * (target - log_re[-1])
        return float(np.exp(result))

    def describe(self) -> dict[str, object]:
        re_values, _ = self._arrays
        return {
            "id": "drag.user_tabular",
            "name": self.model_name,
            "version": self.model_version,
            "author": "User-supplied data",
            "source": "User table",
            "interpolation": self.interpolation,
            "interpolation_axes": "Re, Cd" if self.interpolation == "linear" else "log(Re), log(Cd)",
            "extrapolation": self.extrapolation,
            "validity": {
                "reynolds_min": float(re_values[0]),
                "reynolds_min_inclusive": True,
                "reynolds_max": float(re_values[-1]),
                "reynolds_max_inclusive": True,
            },
            "geometry": "as documented by the user",
        }

    def validity_range(self) -> tuple[float, float]:
        re_values, _ = self._arrays
        return (float(re_values[0]), float(re_values[-1]))

    def fingerprint_payload(self) -> dict[str, object]:
        payload = self.describe()
        payload["points"] = [
            {"reynolds": float(reynolds), "cd": float(cd_value)}
            for reynolds, cd_value in self.points
        ]
        return payload


def math_log(value: float) -> float:
    """Tiny local helper keeping the scalar input conversion explicit."""
    return float(np.log(value))
