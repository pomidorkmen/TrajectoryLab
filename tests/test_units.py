from __future__ import annotations

import pytest

import pint  # noqa: F401 - this test module must fail if the required dependency is absent

from pydantic import ValidationError

from trajectory_lab.io.schemas import ExperimentSpec


def valid_payload() -> dict[str, object]:
    return {
        "name": "unit validation",
        "mass": {"value": 1.0, "unit": "kg"},
        "diameter": {"value": 0.01, "unit": "m"},
        "initial_position": [
            {"value": 0.0, "unit": "m"},
            {"value": 1.0, "unit": "m"},
            {"value": 0.0, "unit": "m"},
        ],
        "initial_velocity": [
            {"value": 1.0, "unit": "m/s"},
            {"value": 0.0, "unit": "m/s"},
            {"value": 0.0, "unit": "m/s"},
        ],
        "duration": {"value": 1.0, "unit": "s"},
        "time_step": {"value": 0.01, "unit": "s"},
    }


def test_valid_unitful_parameters_are_accepted() -> None:
    spec = ExperimentSpec.model_validate(valid_payload())
    assert spec.mass.si("kg") == 1.0


def test_dimensionally_incompatible_unit_is_rejected() -> None:
    payload = valid_payload()
    payload["mass"] = {"value": 1.0, "unit": "m"}
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate(payload)


def test_parameter_without_unit_is_rejected() -> None:
    payload = valid_payload()
    payload["mass"] = 1.0
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate(payload)


def test_dynamic_viscosity_is_converted_to_pa_seconds_at_the_boundary() -> None:
    payload = valid_payload()
    payload["atmosphere"] = {
        "model": "constant",
        "viscosity": {"value": 18.0, "unit": "uPa*s"},
    }
    spec = ExperimentSpec.model_validate(payload)
    config = spec.to_core_config()
    ambient = config.atmosphere.at(0.0)
    assert ambient.viscosity == pytest.approx(1.8e-5, rel=1e-12)


def test_dynamic_viscosity_rejects_nonviscosity_dimensions() -> None:
    payload = valid_payload()
    payload["atmosphere"] = {
        "model": "constant",
        "viscosity": {"value": 18.0, "unit": "m/s"},
    }
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate(payload)


def test_dynamic_viscosity_requires_an_explicit_unit() -> None:
    payload = valid_payload()
    payload["atmosphere"] = {
        "model": "constant",
        "viscosity": {"value": 1.8e-5},
    }
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate(payload)


def test_time_step_may_exceed_maximum_simulation_time() -> None:
    payload = valid_payload()
    payload["duration"] = {"value": 0.1, "unit": "s"}
    payload["time_step"] = {"value": 1.0, "unit": "s"}
    spec = ExperimentSpec.model_validate(payload)
    assert spec.to_core_config().duration_s == 0.1
    assert spec.to_core_config().step_s == 1.0


def test_stop_at_ground_is_a_serializable_experiment_setting() -> None:
    payload = valid_payload()
    payload["stop_at_ground"] = False
    spec = ExperimentSpec.model_validate(payload)
    assert spec.stop_at_ground is False
    assert spec.to_core_config().stop_at_ground is False
