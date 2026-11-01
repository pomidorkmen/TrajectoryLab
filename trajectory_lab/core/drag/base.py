"""Drag-model contract, validity warnings and coefficient validation."""

from __future__ import annotations

from abc import ABC, abstractmethod
import math
import warnings

from trajectory_lab.core.state import FlowState


class DragModelError(ValueError):
    """Raised when a drag-model result is invalid."""


class DragModelApplicabilityWarning(RuntimeWarning):
    """A drag model is being evaluated outside its documented Re interval."""


class BaseDragModel(ABC):
    """Base interface for a spherical-particle drag coefficient model."""

    cd_upper_limit = 100.0

    @abstractmethod
    def cd(self, state: FlowState) -> float:
        """Return dimensionless drag coefficient for the supplied flow state."""

    @abstractmethod
    def describe(self) -> dict[str, object]:
        """Return model name, version, provenance and range of applicability."""

    def validity_range(self) -> tuple[float, float]:
        """Return the documented Reynolds-number interval."""
        return (0.0, math.inf)

    def fingerprint_payload(self) -> dict[str, object]:
        """Return canonical, JSON-safe parameters used to identify this model."""
        return self.describe()


def validate_cd(value: float, *, upper_limit: float = 100.0) -> float:
    """Validate a drag coefficient before using it in the force equation.

    The default 0 < Cd < 100 limit is used for custom/plugin models. Exact
    creeping-flow Stokes coefficients can exceed 100, so that built-in model
    opts into a separately documented, wider finite numerical ceiling.
    """
    if not math.isfinite(value) or not 0.0 < value < upper_limit:
        raise DragModelError(
            f"Drag model returned invalid Cd={value!r}; expected 0 < Cd < {upper_limit:g}"
        )
    return float(value)



def cd_validation_limit(model: BaseDragModel) -> float:
    """Return the coefficient ceiling, keeping plugin models on the strict contract.

    Exact built-in low-Re correlations and tabulated reference data may legitimately
    exceed Cd=100. Third-party subclasses cannot relax the plugin contract by
    overriding ``cd_upper_limit``; their result remains constrained to 0 < Cd < 100.
    """
    trusted_builtin_modules = {
        "trajectory_lab.core.drag.stokes",
        "trajectory_lab.core.drag.schiller_naumann",
        "trajectory_lab.core.drag.clift_grace_weber",
        "trajectory_lab.core.drag.tabular",
    }
    if type(model).__module__ in trusted_builtin_modules:
        return float(model.cd_upper_limit)
    if (
        type(model).__module__ == "trajectory_lab.plugins.registry"
        and type(model).__name__ == "RegisteredModelAdapter"
    ):
        return float(model.cd_upper_limit)
    return 100.0

def applicability_warning(model: BaseDragModel, reynolds: float) -> str | None:
    """Return a warning when Re is outside the exact interval in model metadata.

    Metadata carries explicit endpoint inclusivity because common correlations
    are defined on open intervals such as 0 < Re < 1, while tabular nodes are
    valid at both endpoints.
    """
    validity = model.describe().get("validity", {})
    if not isinstance(validity, dict):
        raise DragModelError("Drag model describe()['validity'] must be a mapping")

    lower_raw = validity.get("reynolds_min", 0.0)
    upper_raw = validity.get("reynolds_max")
    lower = float(lower_raw) if lower_raw is not None else -math.inf
    upper = float(upper_raw) if upper_raw is not None else math.inf
    lower_inclusive = bool(validity.get("reynolds_min_inclusive", True))
    upper_inclusive = bool(validity.get("reynolds_max_inclusive", True))
    lower_ok = reynolds >= lower if lower_inclusive else reynolds > lower
    upper_ok = reynolds <= upper if upper_inclusive else reynolds < upper

    if not lower_ok or not upper_ok:
        lower_bracket = "[" if lower_inclusive else "("
        upper_bracket = "]" if upper_inclusive else ")"
        upper_text = "∞" if math.isinf(upper) else f"{upper:g}"
        return (
            f"{validity.get('name', model.describe().get('name', type(model).__name__))} "
            f"is documented for Re in {lower_bracket}{lower:g}, {upper_text}{upper_bracket}, "
            f"but this run reached Re={reynolds:.6g}."
        )
    return None


def evaluate_cd(model: BaseDragModel, state: FlowState) -> tuple[float, str | None]:
    """Evaluate, warn about validity and validate one coefficient value."""
    warning_message = applicability_warning(model, state.reynolds)
    if warning_message:
        warnings.warn(warning_message, DragModelApplicabilityWarning, stacklevel=2)
    return (validate_cd(model.cd(state), upper_limit=cd_validation_limit(model)), warning_message)
