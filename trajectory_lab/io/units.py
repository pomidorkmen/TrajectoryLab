"""Pint-backed unit conversion at the application boundary only."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_unit_registry():
    """Create the shared Pint registry lazily so the numerical core stays Pint-free."""
    try:
        import pint
    except ImportError as exc:  # pragma: no cover - exercised when optional env is broken
        raise RuntimeError(
            "Pint is required for unit-aware JSON input. Install project dependencies with "
            "`python -m pip install -e .`."
        ) from exc
    return pint.UnitRegistry(autoconvert_offset_to_baseunit=True)


def convert_to_si(value: float, unit: str, target_unit: str) -> float:
    """Convert a numeric quantity carrying an explicit unit into the target SI unit."""
    if not unit or not isinstance(unit, str):
        raise ValueError("A physical quantity must include a unit")
    registry = get_unit_registry()
    try:
        converted = registry.Quantity(value, unit).to(target_unit)
    except Exception as exc:
        raise ValueError(f"Unit {unit!r} is not compatible with {target_unit!r}") from exc
    return float(converted.magnitude)
