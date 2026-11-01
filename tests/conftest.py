"""Shared test fixtures."""

from __future__ import annotations

import pytest

from trajectory_lab.core.atmosphere import ConstantAtmosphere
from trajectory_lab.core.simulation import SimulationConfig


@pytest.fixture
def gravity_only_config() -> SimulationConfig:
    return SimulationConfig(
        mass_kg=0.5,
        diameter_m=0.1,
        initial_position_m=(0.0, 3.0, 0.0),
        initial_velocity_m_s=(1.0, 1.0, 0.0),
        duration_s=0.2,
        step_s=0.01,
        gravity_m_s2=(0.0, -9.80665, 0.0),
        wind_velocity_m_s=(0.0, 0.0, 0.0),
        atmosphere=ConstantAtmosphere(),
        drag_model=None,
        seed=1729,
    )
