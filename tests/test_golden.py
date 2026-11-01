from __future__ import annotations

import json
from pathlib import Path

import pytest

from trajectory_lab.core.atmosphere import ConstantAtmosphere
from trajectory_lab.core.simulation import SimulationConfig, simulate

ROOT = Path(__file__).resolve().parents[1]


def test_rk4_golden_reference() -> None:
    golden = json.loads((ROOT / "tests" / "golden" / "rk4_reference.json").read_text())
    config = SimulationConfig(
        mass_kg=0.5,
        diameter_m=0.1,
        initial_position_m=(0.0, 3.0, 0.0),
        initial_velocity_m_s=(1.0, 1.0, 0.0),
        duration_s=golden["duration_s"],
        step_s=golden["step_s"],
        gravity_m_s2=(0.0, -9.80665, 0.0),
        wind_velocity_m_s=(0.0, 0.0, 0.0),
        atmosphere=ConstantAtmosphere(),
        drag_model=None,
        seed=1729,
    )
    result = simulate(config, method="rk4")
    expected = golden["expected"]
    tolerances = golden["tolerances"]
    for actual, target in zip(result.position_m[-1], expected["final_position_m"], strict=True):
        assert actual == pytest.approx(target, abs=tolerances["position_abs_m"])
    for actual, target in zip(result.velocity_m_s[-1], expected["final_velocity_m_s"], strict=True):
        assert actual == pytest.approx(target, abs=tolerances["velocity_abs_m_s"])
    assert result.kinetic_energy_j[-1] == pytest.approx(
        expected["final_kinetic_energy_j"], abs=tolerances["energy_abs_j"]
    )
    assert result.checksum_sha256 == expected["checksum_sha256"]
