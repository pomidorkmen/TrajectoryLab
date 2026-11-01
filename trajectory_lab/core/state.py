"""Typed, SI-only flow state shared by drag models."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class FlowState:
    """Local flow state passed to a drag model; all dimensional values use SI.

    `velocity` is the magnitude of particle velocity relative to the fluid.
    `mach` is based on that same relative velocity.
    """

    reynolds: float
    mach: float
    velocity: float  # m/s
    density: float  # kg/m^3
    temperature: float  # K
    viscosity: float  # Pa*s (dynamic)
    diameter: float  # m

    def __post_init__(self) -> None:
        values = (
            self.reynolds,
            self.mach,
            self.velocity,
            self.density,
            self.temperature,
            self.viscosity,
            self.diameter,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("FlowState fields must all be finite")
        if self.reynolds < 0 or self.mach < 0 or self.velocity < 0:
            raise ValueError("Reynolds number, Mach number and velocity cannot be negative")
        if self.density <= 0 or self.temperature <= 0 or self.viscosity <= 0 or self.diameter <= 0:
            raise ValueError("Density, temperature, viscosity and diameter must be positive")

def reynolds_number(
    density_kg_m3: float,
    relative_speed_m_s: float,
    diameter_m: float,
    dynamic_viscosity_pa_s: float,
) -> float:
    """Calculate particle Reynolds number using sphere diameter and dynamic viscosity."""
    values = (density_kg_m3, relative_speed_m_s, diameter_m, dynamic_viscosity_pa_s)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Reynolds-number inputs must be finite")
    if density_kg_m3 <= 0 or diameter_m <= 0 or dynamic_viscosity_pa_s <= 0:
        raise ValueError("Density, diameter and dynamic viscosity must be positive")
    if relative_speed_m_s < 0:
        raise ValueError("Relative speed cannot be negative")
    return density_kg_m3 * relative_speed_m_s * diameter_m / dynamic_viscosity_pa_s

