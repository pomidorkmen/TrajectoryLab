from __future__ import annotations

import math

import pytest

from trajectory_lab.core.drag import (
    CliftGraceWeberCompositeSphere,
    ConstantCdSphere,
    SchillerNaumannSphere,
    StokesSphere,
    TabularDragModel,
    validate_cd,
)
from trajectory_lab.core.drag.base import BaseDragModel, DragModelApplicabilityWarning, DragModelError, applicability_warning, evaluate_cd
from trajectory_lab.core.state import FlowState, reynolds_number


def flow(re: float, *, velocity: float = 1.0, density: float = 1.2, viscosity: float = 1.8e-5, diameter: float = 0.01) -> FlowState:
    return FlowState(
        reynolds=re,
        mach=0.01,
        velocity=velocity,
        density=density,
        temperature=288.15,
        viscosity=viscosity,
        diameter=diameter,
    )


def test_stokes_formula() -> None:
    assert StokesSphere().cd(flow(0.5)) == pytest.approx(48.0)


def test_schiller_naumann_formula() -> None:
    re = 100.0
    expected = 24.0 / re * (1.0 + 0.15 * re**0.687)
    assert SchillerNaumannSphere().cd(flow(re)) == pytest.approx(expected)


def test_reynolds_number_uses_diameter_not_radius() -> None:
    state = flow(1000.0, velocity=1.0, density=1.2, viscosity=1.8e-5, diameter=1.5e-2)
    calculated = reynolds_number(state.density, state.velocity, state.diameter, state.viscosity)
    assert calculated == pytest.approx(1000.0)


def test_cgw_piecewise_curve_is_finite_and_positive() -> None:
    model = CliftGraceWeberCompositeSphere()
    for re in (1e-4, 0.1, 20.0, 100.0, 260.0, 261.0, 1e4, 2.99e5):
        result = model.cd(flow(re))
        assert math.isfinite(result)
        assert result > 0


def test_cgw_join_continuity_at_every_piecewise_boundary() -> None:
    model = CliftGraceWeberCompositeSphere()
    for boundary in model._BOUNDARIES:
        delta = boundary * 1e-8
        left = model.cd(flow(boundary - delta))
        right = model.cd(flow(boundary + delta))
        assert abs(left - right) < 1e-3, (boundary, left, right)


def test_cgw_rejects_above_supported_range_and_metadata_matches() -> None:
    model = CliftGraceWeberCompositeSphere()
    assert model.describe()["validity"]["reynolds_max"] == model.validity_range()[1]  # type: ignore[index]
    with pytest.raises(ValueError):
        model.cd(flow(3.1e5))


def test_constant_cd() -> None:
    assert ConstantCdSphere(0.42).cd(flow(1000.0)) == pytest.approx(0.42)


def test_tabular_default_is_log_log_and_preserves_power_law() -> None:
    model = TabularDragModel([(1.0, 24.0), (10.0, 2.4)])
    value = model.cd(flow(math.sqrt(10.0)))
    assert value == pytest.approx(24.0 / math.sqrt(10.0), rel=1e-12)
    assert value == pytest.approx(7.6, abs=0.02)
    assert model.describe()["interpolation"] == "log-log"
    assert model.describe()["interpolation_axes"] == "log(Re), log(Cd)"


def test_tabular_linear_and_extrapolation_policies() -> None:
    linear = TabularDragModel(
        [(1.0, 2.0), (10.0, 1.0)], interpolation="linear", extrapolation="clamp"
    )
    assert linear.cd(flow(5.5)) == pytest.approx(1.5)
    assert linear.cd(flow(0.1)) == pytest.approx(2.0)
    strict = TabularDragModel([(1.0, 2.0), (10.0, 1.0)])
    with pytest.raises(ValueError):
        strict.cd(flow(0.1))
    extrapolate = TabularDragModel(
        [(1.0, 24.0), (10.0, 2.4)], extrapolation="extrapolate"
    )
    assert extrapolate.cd(flow(0.1)) == pytest.approx(240.0)


def test_tabular_model_is_continuous_at_nodes() -> None:
    model = TabularDragModel(
        [(1.0, 24.0), (10.0, 2.4), (100.0, 0.24)], extrapolation="extrapolate"
    )
    for boundary in (1.0, 10.0, 100.0):
        left = model.cd(flow(boundary * (1.0 - 1e-9)))
        right = model.cd(flow(boundary * (1.0 + 1e-9)))
        assert abs(left - right) < 1e-3


def test_tabular_rejects_non_monotonic_points() -> None:
    with pytest.raises(ValueError):
        TabularDragModel([(1.0, 1.0), (1.0, 2.0)])


def test_cd_validator_default_contract_is_zero_to_100() -> None:
    assert validate_cd(99.999) == pytest.approx(99.999)
    for value in (0.0, -1.0, float("nan"), float("inf"), 100.0, 100.001):
        with pytest.raises(DragModelError):
            validate_cd(value)


def test_stokes_can_exceed_cd_100_in_its_physical_domain() -> None:
    assert StokesSphere().cd(flow(0.1)) == pytest.approx(240.0)
    assert validate_cd(240.0, upper_limit=StokesSphere.cd_upper_limit) == pytest.approx(240.0)


def test_applicability_warning_uses_exact_open_and_closed_metadata_bounds() -> None:
    stokes = StokesSphere()
    assert applicability_warning(stokes, 0.5) is None
    # Stokes' stated domain is 0 < Re < 1: Re=1 is outside.
    assert applicability_warning(stokes, 1.0) is not None
    with pytest.warns(DragModelApplicabilityWarning):
        evaluate_cd(stokes, flow(1.0))

    schiller = SchillerNaumannSphere()
    assert applicability_warning(schiller, 799.999) is None
    assert applicability_warning(schiller, 800.0) is not None

    cgw = CliftGraceWeberCompositeSphere()
    assert applicability_warning(cgw, 3.0e5) is None
    assert applicability_warning(cgw, 3.0e5 + 1.0) is not None


def test_tabular_metadata_range_matches_data_and_warns_outside() -> None:
    model = TabularDragModel([(2.0, 10.0), (20.0, 1.0)], extrapolation="clamp")
    assert model.describe()["validity"] == {
        "reynolds_min": 2.0,
        "reynolds_min_inclusive": True,
        "reynolds_max": 20.0,
        "reynolds_max_inclusive": True,
    }
    assert applicability_warning(model, 2.0) is None
    assert applicability_warning(model, 20.0) is None
    with pytest.warns(DragModelApplicabilityWarning):
        evaluate_cd(model, flow(1.0))


def test_tabular_rejects_bad_interpolation_and_large_cd() -> None:
    with pytest.raises(ValueError):
        TabularDragModel([(1.0, 1.0), (2.0, 2.0)], interpolation="nearest")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        TabularDragModel([(1.0, 1.0e12), (2.0, 2.0)])


def test_models_reject_zero_reynolds() -> None:
    with pytest.raises(ValueError):
        StokesSphere().cd(flow(0.0))
    with pytest.raises(ValueError):
        SchillerNaumannSphere().cd(flow(0.0))


def test_builtin_registry_factory() -> None:
    from trajectory_lab.core.drag.registry import build_drag_model

    assert isinstance(build_drag_model("stokes"), StokesSphere)
    assert isinstance(build_drag_model("quadratic", {"cd": 0.5}), ConstantCdSphere)
    with pytest.raises(ValueError):
        build_drag_model("does_not_exist")


def test_python_plugin_cannot_override_strict_cd_ceiling() -> None:
    class InvalidPlugin(BaseDragModel):
        cd_upper_limit = 1.0e12

        def cd(self, state: FlowState) -> float:
            del state
            return 101.0

        def describe(self) -> dict[str, object]:
            return {
                "id": "test.invalid_plugin",
                "name": "Invalid plugin",
                "validity": {"reynolds_min": 0.0, "reynolds_max": None},
            }

    with pytest.raises(DragModelError, match="0 < Cd < 100"):
        evaluate_cd(InvalidPlugin(), flow(10.0))
