"""Shared time-grid and integration result utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import numpy.typing as npt

Rhs = Callable[[float, npt.NDArray[np.float64]], npt.NDArray[np.float64]]


@dataclass(frozen=True, slots=True)
class IntegrationResult:
    time_s: npt.NDArray[np.float64]
    state: npt.NDArray[np.float64]
    event_time_s: float | None = None
    event_state: npt.NDArray[np.float64] | None = None


def make_time_grid(duration_s: float, step_s: float) -> npt.NDArray[np.float64]:
    """Build a fixed output grid and include the exact final time."""
    if duration_s <= 0 or step_s <= 0:
        raise ValueError("Duration and step must be positive")
    count = int(np.floor(duration_s / step_s))
    values = step_s * np.arange(count + 1, dtype=float)
    if values[-1] < duration_s - max(1e-14, duration_s * 1e-14):
        values = np.append(values, duration_s)
    else:
        values[-1] = duration_s
    return values
