from __future__ import annotations

import numpy as np
import pytest

from trajectory_lab.core.integrators.dop853 import DOP853Integrator
from trajectory_lab.core.integrators.rk4 import RK4Integrator


def rhs(_time: float, state: np.ndarray) -> np.ndarray:
    return np.asarray([state[1], -2.0 * state[0]])


def test_rk4_harmonic_oscillator_accuracy() -> None:
    result = RK4Integrator().integrate(rhs, np.asarray([1.0, 0.0]), 1.0, 0.001)
    assert result.state[-1, 0] == pytest.approx(np.cos(np.sqrt(2.0)), abs=2e-11)


def test_dop853_harmonic_oscillator_accuracy() -> None:
    result = DOP853Integrator().integrate(
        rhs, np.asarray([1.0, 0.0]), 1.0, 0.1, rtol=1e-11, atol=1e-13
    )
    assert result.state[-1, 0] == pytest.approx(np.cos(np.sqrt(2.0)), abs=1e-10)


def test_dop853_accepts_componentwise_atol_vector() -> None:
    tolerances = np.asarray([1e-12, 2e-12])
    result = DOP853Integrator().integrate(
        rhs, np.asarray([1.0, 0.0]), 1.0, 0.1, rtol=1e-10, atol=tolerances
    )
    assert result.state[-1, 0] == pytest.approx(np.cos(np.sqrt(2.0)), abs=1e-9)


def test_dop853_rejects_wrong_atol_vector_shape() -> None:
    with pytest.raises(ValueError, match="atol vector"):
        DOP853Integrator().integrate(
            rhs, np.asarray([1.0, 0.0]), 1.0, 0.1, atol=np.asarray([1e-12, 1e-12, 1e-12])
        )


def test_time_grid_includes_exact_end_time() -> None:
    result = RK4Integrator().integrate(rhs, np.asarray([1.0, 0.0]), 1.0, 0.3)
    assert result.time_s[-1] == 1.0


def test_rk4_localizes_descending_ground_event_between_output_samples() -> None:
    from math import cos, radians, sin

    speed = 10.0
    angle = radians(45.0)
    expected_time = 2.0 * speed * sin(angle) / 9.80665
    initial = np.asarray([0.0, 0.0, 0.0, speed * cos(angle), speed * sin(angle), 0.0])

    def ballistic_rhs(_time: float, state: np.ndarray) -> np.ndarray:
        return np.asarray([state[3], state[4], state[5], 0.0, -9.80665, 0.0])

    result = RK4Integrator().integrate(
        ballistic_rhs, initial, 3.0, 0.37,
        terminal_event_index=1, terminal_event_value=0.0,
    )
    assert result.event_time_s == pytest.approx(expected_time, abs=1e-9)
    assert result.time_s[-1] == pytest.approx(expected_time, abs=1e-9)
    assert result.state[-1, 1] == pytest.approx(0.0, abs=1e-11)


def test_rk4_ground_event_at_initial_time_when_already_descending() -> None:
    initial = np.asarray([0.0, 0.0, 0.0, 0.0, -1.0, 0.0])
    result = RK4Integrator().integrate(
        lambda _t, _y: np.asarray([0.0, -9.80665, 0.0, 0.0, 0.0, 0.0]),
        initial, 1.0, 0.1,
        terminal_event_index=1, terminal_event_value=0.0,
    )
    assert result.event_time_s == 0.0
    assert result.time_s.tolist() == [0.0]


def test_step_larger_than_duration_is_clamped_to_final_time() -> None:
    result = RK4Integrator().integrate(rhs, np.asarray([1.0, 0.0]), 0.2, 1.0)
    assert result.time_s.tolist() == [0.0, 0.2]
    assert result.state[-1, 0] == pytest.approx(np.cos(np.sqrt(2.0) * 0.2), abs=2e-5)
