"""Atmosphere protocols and common transport-property utilities."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AtmosphereState:
    """Thermodynamic state at altitude, expressed entirely in SI units."""

    density: float  # kg/m^3
    temperature: float  # K
    viscosity: float  # Pa*s
    speed_of_sound: float  # m/s

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(value)
            for value in (self.density, self.temperature, self.viscosity, self.speed_of_sound)
        ):
            raise ValueError("Atmosphere properties must be finite")
        if (
            self.density < 0
            or self.temperature <= 0
            or self.viscosity <= 0
            or self.speed_of_sound <= 0
        ):
            raise ValueError("Invalid atmospheric properties")


@runtime_checkable
class Atmosphere(Protocol):
    """Interface implemented by all atmospheric models."""

    def at(self, altitude_m: float) -> AtmosphereState:
        """Return density, temperature, dynamic viscosity and sound speed."""

    def describe(self) -> dict[str, object]:
        """Return serializable model metadata."""


def sutherland_viscosity(
    temperature_k: float,
    *,
    reference_temperature_k: float = 273.15,
    reference_viscosity_pa_s: float = 1.716e-5,
    sutherland_constant_k: float = 110.4,
) -> float:
    """Dynamic viscosity of dry air using the three-parameter Sutherland law.

    Defaults: mu0=1.716e-5 Pa*s, T0=273.15 K, S=110.4 K. This is a
    continuum-gas approximation and is not intended for rarefied flow.
    """
    if temperature_k <= 0 or not math.isfinite(temperature_k):
        raise ValueError("Temperature must be finite and greater than zero kelvin")
    if (
        not math.isfinite(reference_temperature_k)
        or not math.isfinite(reference_viscosity_pa_s)
        or not math.isfinite(sutherland_constant_k)
        or reference_temperature_k <= 0
        or reference_viscosity_pa_s <= 0
        or sutherland_constant_k < 0
    ):
        raise ValueError("Sutherland reference parameters must be finite and physical")
    ratio = temperature_k / reference_temperature_k
    return (
        reference_viscosity_pa_s
        * ratio**1.5
        * (reference_temperature_k + sutherland_constant_k)
        / (temperature_k + sutherland_constant_k)
    )


def ideal_gas_speed_of_sound(
    temperature_k: float, *, gamma: float = 1.4, gas_constant_j_kg_k: float = 287.05287
) -> float:
    """Return ideal-gas speed of sound for dry air."""
    if temperature_k <= 0:
        raise ValueError("Temperature must be positive")
    return math.sqrt(gamma * gas_constant_j_kg_k * temperature_k)
