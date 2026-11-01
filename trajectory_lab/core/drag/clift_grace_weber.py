"""Continuous piecewise Clift--Grace--Weber smooth-sphere drag curve."""

from __future__ import annotations

import math

from trajectory_lab.core.drag.base import BaseDragModel
from trajectory_lab.core.state import FlowState


class CliftGraceWeberCompositeSphere(BaseDragModel):
    """Full low/subcritical Clift--Grace--Weber sphere curve to Re=3e5.

    The earlier implementation switched directly from the low-Re correction
    curve to a Clift--Gauvin formula at Re=260. Those expressions differ by
    about 0.043 in Cd at the hand-off. This implementation instead uses the
    published piecewise Clift/Grace/Weber standard curve throughout the
    supported interval, with narrow C1 smoothstep joins around source-table
    breakpoints to remove numerical jumps caused by rounded coefficients.
    """

    MAX_REYNOLDS = 3.0e5
    cd_upper_limit = 1.0e12  # Low-Re Cd can exceed 100 without being nonphysical.
    JOIN_HALF_WIDTH_FRACTION = 0.005
    _BOUNDARIES = (0.01, 20.0, 260.0, 1500.0, 12_000.0, 44_000.0)

    @staticmethod
    def _branch(reynolds: float, branch: int) -> float:
        re = reynolds
        log_re = math.log10(re)
        if branch == 0:
            return 24.0 / re + 3.0 / 16.0
        if branch == 1:
            return 24.0 / re * (1.0 + 0.1315 * re ** (0.82 - 0.05 * log_re))
        if branch == 2:
            return 24.0 / re * (1.0 + 0.1935 * re**0.6305)
        if branch == 3:
            return 10.0 ** (1.6435 - 1.1242 * log_re + 0.1558 * log_re**2)
        if branch == 4:
            return 10.0 ** (
                -2.4571 + 2.5558 * log_re - 0.9295 * log_re**2 + 0.1049 * log_re**3
            )
        if branch == 5:
            return 10.0 ** (-1.9181 + 0.6370 * log_re - 0.0636 * log_re**2)
        if branch == 6:
            return 10.0 ** (-4.3390 + 1.5809 * log_re - 0.1546 * log_re**2)
        raise ValueError(f"Unknown Clift-GW branch index: {branch}")

    def cd(self, state: FlowState) -> float:
        re = state.reynolds
        if re <= 0:
            raise ValueError("Clift--Grace--Weber correlation is undefined at Re=0")
        if re > self.MAX_REYNOLDS:
            raise ValueError(
                f"Clift--Grace--Weber correlation is limited to Re <= {self.MAX_REYNOLDS:g}"
            )

        # Сначала проверяем узкие зоны стыков и плавно смешиваем соседние формулы.
        for index, boundary in enumerate(self._BOUNDARIES):
            lower = boundary * (1.0 - self.JOIN_HALF_WIDTH_FRACTION)
            upper = boundary * (1.0 + self.JOIN_HALF_WIDTH_FRACTION)
            if lower < re < upper:
                left_value = self._branch(re, index)
                right_value = self._branch(re, index + 1)
                fraction = (math.log(re) - math.log(lower)) / (math.log(upper) - math.log(lower))
                weight = fraction * fraction * (3.0 - 2.0 * fraction)
                return (1.0 - weight) * left_value + weight * right_value

        branch_index = 0
        for boundary in self._BOUNDARIES:
            if re > boundary:
                branch_index += 1
            else:
                break
        return self._branch(re, branch_index)

    def describe(self) -> dict[str, object]:
        return {
            "id": "drag.clift_grace_weber_sphere",
            "name": "Clift--Grace--Weber standard sphere curve",
            "version": "1.1.0",
            "author": "Clift, Grace & Weber",
            "source": "Clift, Grace & Weber (1978), Table 5.2; see project docs/physics.md",
            "formula": "Published piecewise smooth-sphere Cd(Re) curve, Re <= 3e5",
            "validity": {
                "reynolds_min": 0.0,
                "reynolds_min_inclusive": False,
                "reynolds_max": self.MAX_REYNOLDS,
                "reynolds_max_inclusive": True,
            },
            "geometry": "smooth rigid sphere",
            "join_policy": (
                "C1 smoothstep blend over +/-0.5% in Re around rounded source-table breakpoints"
            ),
            "branches": list(self._BOUNDARIES),
        }

    def validity_range(self) -> tuple[float, float]:
        return (0.0, self.MAX_REYNOLDS)
