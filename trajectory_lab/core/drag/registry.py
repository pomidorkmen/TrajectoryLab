"""Factory for built-in drag models (external plugins arrive in iteration 3)."""

from __future__ import annotations

from typing import Any

from trajectory_lab.core.drag.base import BaseDragModel
from trajectory_lab.core.drag.clift_grace_weber import CliftGraceWeberCompositeSphere
from trajectory_lab.core.drag.quadratic import ConstantCdSphere
from trajectory_lab.core.drag.schiller_naumann import SchillerNaumannSphere
from trajectory_lab.core.drag.stokes import StokesSphere
from trajectory_lab.core.drag.tabular import TabularDragModel


def build_drag_model(model_id: str, options: dict[str, Any] | None = None) -> BaseDragModel | None:
    """Create a built-in model by stable ID."""
    options = options or {}
    factories: dict[str, Any] = {
        "none": lambda: None,
        "stokes": StokesSphere,
        "schiller_naumann": SchillerNaumannSphere,
        "cgw_composite": CliftGraceWeberCompositeSphere,
        "quadratic": lambda: ConstantCdSphere(coefficient=float(options.get("cd", 0.44))),
        "tabular": lambda: TabularDragModel(
            points=[(float(p["reynolds"]), float(p["cd"])) for p in options["points"]],
            interpolation=options.get("interpolation", "linear"),
            extrapolation=options.get("extrapolation", "error"),
            model_name=options.get("name", "User tabular sphere model"),
            model_version=options.get("version", "1.0.0"),
        ),
    }
    try:
        factory = factories[model_id]
    except KeyError as exc:
        raise ValueError(f"Unknown built-in drag model: {model_id}") from exc
    model = factory()
    if model is not None and not isinstance(model, BaseDragModel):
        raise TypeError(f"Factory for {model_id!r} did not return a BaseDragModel")
    return model
