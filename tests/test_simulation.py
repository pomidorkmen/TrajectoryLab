from __future__ import annotations

import math

import numpy as np
import pytest

from trajectory_lab.core.atmosphere import ConstantAtmosphere, ExponentialAtmosphere
from trajectory_lab.core.drag import ConstantCdSphere, StokesSphere
from trajectory_lab.core.simulation import (
    SimulationConfig,
    _trajectory_checksum,
    simulate,
    stokes_terminal_velocity,
)


def test_vacuum_reference_matches_analytic_position(gravity_only_config: SimulationConfig) -> None:
    result = simulate(gravity_only_config, method="rk4")
    t = 0.2
    expected_y = 3.0 + 1.0 * t - 0.5 * 9.80665 * t**2
    assert result.position_m[-1, 0] == pytest.approx(0.2, abs=1e-13)
    assert result.position_m[-1, 1] == pytest.approx(expected_y, abs=1e-12)


def test_mechanical_energy_conserved_without_drag(gravity_only_config: SimulationConfig) -> None:
    result = simulate(gravity_only_config)
    potential = gravity_only_config.mass_kg * 9.80665 * result.position_m[:, 1]
    total_energy = result.kinetic_energy_j + potential
    assert np.ptp(total_energy) < 1e-6


def test_vacuum_45_degree_range_matches_analytic_formula() -> None:
    speed = 10.0
    angle = math.radians(45.0)
    vertical_speed = speed * math.sin(angle)
    flight_time = 2.0 * vertical_speed / 9.80665
    config = SimulationConfig(
        mass_kg=1.0,
        diameter_m=0.1,
        initial_position_m=(0.0, 0.0, 0.0),
        initial_velocity_m_s=(speed * math.cos(angle), vertical_speed, 0.0),
        duration_s=flight_time,
        step_s=flight_time / 100.0,
        gravity_m_s2=(0.0, -9.80665, 0.0),
        wind_velocity_m_s=(0.0, 0.0, 0.0),
        atmosphere=ConstantAtmosphere(),
        drag_model=None,
    )
    result = simulate(config, method="rk4")
    expected_range = speed**2 * math.sin(2.0 * angle) / 9.80665
    assert result.range_m == pytest.approx(expected_range, abs=1e-10)


def test_dop853_finds_ground_impact_with_brent_root_between_samples() -> None:
    speed = 10.0
    angle = math.radians(45.0)
    vertical_speed = speed * math.sin(angle)
    expected_time = 2.0 * vertical_speed / 9.80665
    config = SimulationConfig(
        mass_kg=1.0,
        diameter_m=0.1,
        initial_position_m=(0.0, 0.0, 0.0),
        initial_velocity_m_s=(speed * math.cos(angle), vertical_speed, 0.0),
        duration_s=3.0,
        step_s=0.37,
        gravity_m_s2=(0.0, -9.80665, 0.0),
        wind_velocity_m_s=(0.0, 0.0, 0.0),
        atmosphere=ConstantAtmosphere(),
        drag_model=None,
    )
    result = simulate(config, method="dop853", atol=(1e-12,) * 6)
    assert result.impact_time_s == pytest.approx(expected_time, abs=1e-6)
    assert result.time_s[-1] == pytest.approx(expected_time, abs=1e-6)
    assert result.position_m[-1, 1] == pytest.approx(0.0, abs=1e-10)


def _variable_drag_config(step_s: float) -> SimulationConfig:
    return SimulationConfig(
        mass_kg=0.02,
        diameter_m=0.025,
        initial_position_m=(0.0, 20.0, 0.0),
        initial_velocity_m_s=(12.0, -2.0, 0.0),
        duration_s=0.4,
        step_s=step_s,
        gravity_m_s2=(0.0, -9.80665, 0.0),
        wind_velocity_m_s=(0.2, 0.0, 0.0),
        atmosphere=ExponentialAtmosphere(
            sea_level_density_kg_m3=1.225,
            scale_height_m=4000.0,
            temperature_k=288.15,
            temperature_lapse_rate_k_m=0.001,
        ),
        drag_model=ConstantCdSphere(0.43),
    )


def test_rk4_fourth_order_convergence_with_stagewise_atmosphere_and_drag() -> None:
    reference = simulate(_variable_drag_config(0.001), method="dop853", rtol=1e-13, atol=1e-14)
    coarse = simulate(_variable_drag_config(0.04), method="rk4")
    fine = simulate(_variable_drag_config(0.02), method="rk4")
    coarse_error = np.linalg.norm(np.concatenate((coarse.position_m[-1], coarse.velocity_m_s[-1])) - np.concatenate((reference.position_m[-1], reference.velocity_m_s[-1])))
    fine_error = np.linalg.norm(np.concatenate((fine.position_m[-1], fine.velocity_m_s[-1])) - np.concatenate((reference.position_m[-1], reference.velocity_m_s[-1])))
    assert coarse_error / fine_error == pytest.approx(16.0, rel=0.25)


def test_stokes_terminal_velocity_matches_effective_mass_formula() -> None:
    particle_density = 2500.0
    diameter = 10e-6
    radius = diameter / 2.0
    air_density = 1.2
    temperature = 288.15
    viscosity = 1.8e-5
    volume = math.pi * diameter**3 / 6.0
    particle_mass = particle_density * volume
    effective_mass = particle_mass - air_density * volume
    expected = effective_mass * 9.80665 / (6.0 * math.pi * viscosity * radius)
    assert stokes_terminal_velocity(particle_density, air_density, radius, viscosity) == pytest.approx(expected)

    config = SimulationConfig(
        mass_kg=particle_mass,
        diameter_m=diameter,
        initial_position_m=(0.0, 100.0, 0.0),
        initial_velocity_m_s=(0.0, 0.0, 0.0),
        duration_s=0.8,
        step_s=0.0005,
        gravity_m_s2=(0.0, -9.80665, 0.0),
        wind_velocity_m_s=(0.0, 0.0, 0.0),
        atmosphere=ConstantAtmosphere(
            density_kg_m3=air_density,
            temperature_k=temperature,
            viscosity_pa_s=viscosity,
        ),
        drag_model=StokesSphere(),
    )
    result = simulate(config)
    assert abs(result.velocity_m_s[-1, 1]) == pytest.approx(expected, rel=0.01)


def test_seed_and_checksum_are_recorded(gravity_only_config: SimulationConfig) -> None:
    result = simulate(gravity_only_config)
    assert result.provenance["seed"] == 1729
    assert len(result.checksum_sha256) == 64
    assert result.provenance["trajectory_checksum_quantization"] == "per-column relative 1e-9"


def test_quantized_checksum_is_stable_to_sub_quantum_float_noise() -> None:
    values = np.asarray(
        [
            [0.0, 0.0, 1.0],
            [0.123456789, 0.25, 0.75],
            [0.5, 0.5, 0.5],
            [1.0, 1.0, 0.0],
        ],
        dtype=float,
    )
    perturbed = values.copy()
    perturbed[1, 1] += 1e-12
    assert _trajectory_checksum(values) == _trajectory_checksum(perturbed)
    perturbed[1, 1] += 1e-5
    assert _trajectory_checksum(values) != _trajectory_checksum(perturbed)


def test_tabular_model_parameters_change_drag_hash() -> None:
    from trajectory_lab.core.drag import TabularDragModel

    base = dict(
        mass_kg=0.01,
        diameter_m=0.01,
        initial_position_m=(0.0, 1.0, 0.0),
        initial_velocity_m_s=(1.0, 0.0, 0.0),
        duration_s=0.1,
        step_s=0.01,
        gravity_m_s2=(0.0, -9.80665, 0.0),
        wind_velocity_m_s=(0.0, 0.0, 0.0),
        atmosphere=ConstantAtmosphere(),
        seed=7,
    )
    first = simulate(
        SimulationConfig(
            **base,
            drag_model=TabularDragModel([(1.0, 2.0), (1000.0, 1.0)], extrapolation="clamp"),
        )
    )
    second = simulate(
        SimulationConfig(
            **base,
            drag_model=TabularDragModel([(1.0, 2.1), (1000.0, 1.0)], extrapolation="clamp"),
        )
    )
    assert first.provenance["drag_model_sha256"] != second.provenance["drag_model_sha256"]


def test_rk4_and_dop853_use_the_same_optional_ground_stop_rule() -> None:
    base = dict(
        mass_kg=1.0,
        diameter_m=0.1,
        initial_position_m=(0.0, 1.0, 0.0),
        initial_velocity_m_s=(0.0, -10.0, 0.0),
        duration_s=0.2,
        step_s=0.07,
        gravity_m_s2=(0.0, -9.80665, 0.0),
        wind_velocity_m_s=(0.0, 0.0, 0.0),
        atmosphere=ConstantAtmosphere(),
        drag_model=None,
    )
    for method in ("rk4", "dop853"):
        stopped = simulate(SimulationConfig(**base, stop_at_ground=True), method=method)
        continued = simulate(SimulationConfig(**base, stop_at_ground=False), method=method)
        expected_impact = (-10.0 + math.sqrt(100.0 + 2.0 * 9.80665)) / 9.80665
        assert stopped.impact_time_s == pytest.approx(expected_impact, abs=1e-8)
        assert stopped.time_s[-1] < 0.2
        assert continued.impact_time_s is None
        assert continued.time_s[-1] == pytest.approx(0.2)
        assert continued.position_m[-1, 1] < 0.0


def test_duration_is_a_maximum_and_step_may_exceed_it() -> None:
    config = SimulationConfig(
        mass_kg=1.0,
        diameter_m=0.1,
        initial_position_m=(0.0, 4.0, 0.0),
        initial_velocity_m_s=(1.0, 0.0, 0.0),
        duration_s=0.2,
        step_s=1.0,
        gravity_m_s2=(0.0, -9.80665, 0.0),
        wind_velocity_m_s=(0.0, 0.0, 0.0),
        atmosphere=ConstantAtmosphere(),
        drag_model=None,
    )
    result = simulate(config, method="rk4")
    assert result.time_s.tolist() == [0.0, 0.2]
    assert result.provenance["termination_reason"] == "maximum_time"


def test_apogee_is_interpolated_between_output_samples(gravity_only_config: SimulationConfig) -> None:
    result = simulate(gravity_only_config, method="rk4")
    expected_time = 1.0 / 9.80665
    expected_height = 3.0 + 1.0 / (2.0 * 9.80665)
    assert result.maximum_height_time_s == pytest.approx(expected_time, abs=1e-10)
    assert result.maximum_height_m == pytest.approx(expected_height, abs=1e-10)
