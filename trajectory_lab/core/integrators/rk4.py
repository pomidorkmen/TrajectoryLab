"""Classical fixed-step fourth-order Runge--Kutta integrator."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
from scipy.optimize import brentq

from trajectory_lab.core.integrators.base import IntegrationResult, Rhs, make_time_grid


class RK4Integrator:
    """Deterministic explicit RK4 over a fixed output grid."""

    name = "RK4"

    @staticmethod
    def _step(
        rhs: Rhs,
        time_s: float,
        state: npt.NDArray[np.float64],
        step_s: float,
    ) -> npt.NDArray[np.float64]:
        """Advance one RK4 step; the RHS is re-evaluated at all four stages."""
        k1 = rhs(time_s, state)
        k2 = rhs(time_s + 0.5 * step_s, state + 0.5 * step_s * k1)
        k3 = rhs(time_s + 0.5 * step_s, state + 0.5 * step_s * k2)
        k4 = rhs(time_s + step_s, state + step_s * k3)
        return state + (step_s / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    def integrate(
        self,
        rhs: Rhs,
        initial_state: npt.NDArray[np.float64],
        duration_s: float,
        step_s: float,
        *,
        terminal_event_index: int | None = None,
        terminal_event_value: float = 0.0,
    ) -> IntegrationResult:
        """Integrate to the maximum time or a descending scalar event.

        Event localization uses Brent's method on a fractional RK4 step between
        output samples. The state at the event is calculated by the same RK4
        method, so the event is not rounded to the next output-grid point.
        """
        time = make_time_grid(duration_s, step_s)
        states = np.empty((time.size, initial_state.size), dtype=float)
        states[0] = initial_state

        if terminal_event_index is not None:
            if not 0 <= terminal_event_index < initial_state.size:
                raise ValueError("terminal_event_index is outside the state vector")
            initial_event_value = float(initial_state[terminal_event_index] - terminal_event_value)
            initial_derivative = float(rhs(0.0, initial_state)[terminal_event_index])
            if initial_event_value == 0.0 and initial_derivative < 0.0:
                return IntegrationResult(
                    time_s=np.asarray([0.0], dtype=float),
                    state=np.asarray([initial_state], dtype=float),
                    event_time_s=0.0,
                    event_state=np.asarray(initial_state, dtype=float).copy(),
                )

        for index in range(time.size - 1):
            t0 = float(time[index])
            h = float(time[index + 1] - time[index])
            y0 = states[index]
            next_state = self._step(rhs, t0, y0, h)

            if terminal_event_index is not None:
                left_value = float(y0[terminal_event_index] - terminal_event_value)
                right_value = float(next_state[terminal_event_index] - terminal_event_value)
                # The ground event is a downward crossing: above before, at/below after.
                if left_value > 0.0 and right_value <= 0.0:
                    event_offset = brentq(
                        lambda offset: float(
                            self._step(rhs, t0, y0, float(offset))[terminal_event_index]
                            - terminal_event_value
                        ),
                        0.0,
                        h,
                        xtol=1e-13,
                        rtol=4.0 * np.finfo(float).eps,
                    )
                    event_state = self._step(rhs, t0, y0, float(event_offset))
                    event_time = t0 + float(event_offset)
                    output_times = np.concatenate((time[: index + 1], [event_time]))
                    output_states = np.vstack((states[: index + 1], event_state))
                    return IntegrationResult(
                        time_s=output_times,
                        state=output_states,
                        event_time_s=event_time,
                        event_state=event_state,
                    )

            states[index + 1] = next_state

        return IntegrationResult(time_s=time, state=states)
