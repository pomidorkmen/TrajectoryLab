from __future__ import annotations

import math

import pytest

from trajectory_lab.core.atmosphere import (
    ConstantAtmosphere,
    ExponentialAtmosphere,
    ISAAtmosphere,
    sutherland_viscosity,
)
from trajectory_lab.core.atmosphere.isa import (
    geopotential_to_geometric,
    geometric_to_geopotential,
)
from trajectory_lab.core.state import reynolds_number


def test_all_atmospheres_return_four_properties() -> None:
    models = [ConstantAtmosphere(), ExponentialAtmosphere(), ISAAtmosphere()]
    for model in models:
        state = model.at(1000.0)
        assert state.density > 0
        assert state.temperature > 0
        assert state.viscosity > 0
        assert state.speed_of_sound > 0


def test_exponential_density_ratio() -> None:
    model = ExponentialAtmosphere(sea_level_density_kg_m3=1.2, scale_height_m=8000.0)
    assert model.at(8000.0).density == pytest.approx(1.2 / math.e)


def test_exponential_temperature_is_altitude_dependent() -> None:
    model = ExponentialAtmosphere()
    assert model.at(1000.0).temperature == pytest.approx(281.65)
    assert model.at(1000.0).temperature < model.at(0.0).temperature


def test_isa_reference_sea_level() -> None:
    state = ISAAtmosphere().at(0.0)
    assert state.temperature == pytest.approx(288.15, abs=1e-12)
    assert state.density == pytest.approx(1.225, abs=1e-7)
    assert state.speed_of_sound == pytest.approx(340.294, rel=1e-4)


def test_isa_geopotential_tropopause_and_isothermal_layer_exact_values() -> None:
    model = ISAAtmosphere()
    assert model.at_geopotential(11_000.0).temperature == 216.65
    assert model.at_geopotential(20_000.0).temperature == 216.65
    geometric_tropopause = geopotential_to_geometric(11_000.0)
    assert model.at(geometric_tropopause).temperature == 216.65


def test_isa_geometric_altitude_is_converted_to_geopotential() -> None:
    geometric_altitude = 15_000.0
    expected = geometric_altitude * 6_356_766.0 / (6_356_766.0 + geometric_altitude)
    assert geometric_to_geopotential(geometric_altitude) == pytest.approx(expected)
    assert ISAAtmosphere().at(geometric_altitude).temperature == pytest.approx(
        ISAAtmosphere().at_geopotential(expected).temperature
    )


def test_sutherland_three_parameter_reference_values() -> None:
    assert sutherland_viscosity(273.15) == pytest.approx(1.716e-5, abs=1e-10)
    assert sutherland_viscosity(300.0) == pytest.approx(1.846e-5, abs=1e-9)


def test_isa_rejects_altitude_outside_documented_range() -> None:
    with pytest.raises(ValueError):
        ISAAtmosphere().at(25_000.0)


def test_exponential_rejects_nonpositive_scale_height_or_temperature() -> None:
    with pytest.raises(ValueError):
        ExponentialAtmosphere(scale_height_m=0).at(100.0)
    with pytest.raises(ValueError):
        ExponentialAtmosphere(temperature_k=250.0, temperature_lapse_rate_k_m=0.01).at(30_000.0)


def test_atmosphere_state_rejects_nonphysical_properties() -> None:
    from trajectory_lab.core.atmosphere.base import AtmosphereState

    with pytest.raises(ValueError):
        AtmosphereState(density=-1.0, temperature=280.0, viscosity=1.8e-5, speed_of_sound=330.0)


def test_flow_atmosphere_viscosity_is_dynamic_si_pa_seconds() -> None:
    from trajectory_lab.core.state import FlowState

    state = FlowState(
        reynolds=100.0,
        mach=0.01,
        velocity=1.0,
        density=1.2,
        temperature=288.15,
        viscosity=1.8e-5,
        diameter=0.015,
    )
    assert state.viscosity == pytest.approx(1.8e-5)
    assert reynolds_number(
        state.density, state.velocity, state.diameter, state.viscosity
    ) == pytest.approx(1000.0)
