"""SciPy DOP853 adaptive integrator with dense-output event localization."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from trajectory_lab.core.integrators.base import IntegrationResult, Rhs, make_time_grid

Atol = float | Sequence[float] | npt.NDArray[np.float64]


class DOP853Integrator:
    """Adaptive DOP853; optional scalar-state event is rooted between samples."""

    name = "DOP853"

    def integrate(
        self,
        rhs: Rhs,
        initial_state: npt.NDArray[np.float64],
        duration_s: float,
        step_s: float,
        *,
        rtol: float = 1e-9,
        atol: Atol = 1e-12,
        terminal_event_index: int | None = None,
        terminal_event_value: float = 0.0,
    ) -> IntegrationResult:
        time = make_time_grid(duration_s, step_s)
        if isinstance(atol, (float, int)):
            atol_value: float | npt.NDArray[np.float64] = float(atol)
        else:
            atol_value = np.asarray(atol, dtype=float)
            if atol_value.shape != initial_state.shape:
                raise ValueError(
                    f"DOP853 atol vector must have shape {initial_state.shape}, got {atol_value.shape}"
                )
            if not np.all(np.isfinite(atol_value)) or np.any(atol_value <= 0):
                raise ValueError("Every DOP853 atol component must be finite and positive")

        if terminal_event_index is not None:
            if not 0 <= terminal_event_index < initial_state.size:
                raise ValueError("terminal_event_index is outside the state vector")
            initial_event_value = float(initial_state[terminal_event_index] - terminal_event_value)
            initial_derivative = float(rhs(0.0, initial_state)[terminal_event_index])
            if initial_event_value == 0.0 and initial_derivative < 0.0:
                initial_copy = np.asarray(initial_state, dtype=float).copy()
                return IntegrationResult(
                    time_s=np.asarray([0.0], dtype=float),
                    state=np.asarray([initial_copy], dtype=float),
                    event_time_s=0.0,
                    event_state=initial_copy,
                )

        events = None
        if terminal_event_index is not None:
            def terminal_event(_time: float, state: npt.NDArray[np.float64]) -> float:
                return float(state[terminal_event_index] - terminal_event_value)

            terminal_event.terminal = True  # type: ignore[attr-defined]
            terminal_event.direction = -1.0  # type: ignore[attr-defined]
            events = terminal_event

        solution = solve_ivp(
            rhs,
            (0.0, duration_s),
            initial_state,
            method="DOP853",
            t_eval=time,
            rtol=rtol,
            atol=atol_value,
            dense_output=True,
            events=events,
        )
        if not solution.success:
            raise RuntimeError(f"DOP853 integration failed: {solution.message}")

        if terminal_event_index is not None and solution.t_events and solution.t_events[0].size:
            event_time = float(solution.t_events[0][0])
            event_state = np.asarray(solution.y_events[0][0], dtype=float)
            output_times = solution.t.astype(float, copy=False)
            output_states = solution.y.T.astype(float, copy=False)
            if output_times.size and abs(float(output_times[-1]) - event_time) <= 1e-13:
                output_times = output_times[:-1]
                output_states = output_states[:-1]
            output_times = np.concatenate((output_times, [event_time]))
            output_states = np.vstack((output_states, event_state))
            return IntegrationResult(
                time_s=output_times,
                state=output_states,
                event_time_s=event_time,
                event_state=event_state,
            )

        return IntegrationResult(time_s=solution.t, state=solution.y.T.astype(float, copy=False))
