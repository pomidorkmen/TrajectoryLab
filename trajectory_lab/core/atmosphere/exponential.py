"""Exponential-density atmosphere with a configurable temperature lapse law."""

from __future__ import annotations

from dataclasses import dataclass
import math

from trajectory_lab.core.atmosphere.base import (
    AtmosphereState,
    ideal_gas_speed_of_sound,
    sutherland_viscosity,
)


@dataclass(frozen=True, slots=True)
class ExponentialAtmosphere:
    """Exponential density with temperature T(h)=T0-L*h.

    The density scale height and temperature lapse rate are independent user
    parameters; this is a compact experimental atmosphere, not a hydrostatic
    self-consistent multilayer standard atmosphere.
    """

    sea_level_density_kg_m3: float = 1.225
    scale_height_m: float = 8500.0
    temperature_k: float = 288.15
    temperature_lapse_rate_k_m: float = 0.0065

    def __post_init__(self) -> None:
        values = (
            self.sea_level_density_kg_m3,
            self.scale_height_m,
            self.temperature_k,
            self.temperature_lapse_rate_k_m,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Exponential-atmosphere parameters must be finite")
        if self.sea_level_density_kg_m3 <= 0 or self.scale_height_m <= 0 or self.temperature_k <= 0:
            raise ValueError("Density, scale height and sea-level temperature must be positive")
        if self.temperature_lapse_rate_k_m < 0:
            raise ValueError("Temperature lapse rate cannot be negative")

    def at(self, altitude_m: float) -> AtmosphereState:
        if self.scale_height_m <= 0:
            raise ValueError("Scale height must be positive")
        if not math.isfinite(altitude_m):
            raise ValueError("Altitude must be finite")
        density = self.sea_level_density_kg_m3 * math.exp(-altitude_m / self.scale_height_m)
        temperature = self.temperature_k - self.temperature_lapse_rate_k_m * altitude_m
        if not math.isfinite(temperature) or temperature <= 0:
            raise ValueError(
                "Exponential-atmosphere temperature became non-positive; "
                "reduce altitude or temperature lapse rate"
            )
        return AtmosphereState(
            density=density,
            temperature=temperature,
            viscosity=sutherland_viscosity(temperature),
            speed_of_sound=ideal_gas_speed_of_sound(temperature),
        )

    def describe(self) -> dict[str, object]:
        return {
            "id": "atmosphere.exponential",
            "name": "Exponential density / linear temperature lapse",
            "version": "1.1.0",
            "sea_level_density_kg_m3": self.sea_level_density_kg_m3,
            "scale_height_m": self.scale_height_m,
            "sea_level_temperature_k": self.temperature_k,
            "temperature_lapse_rate_k_m": self.temperature_lapse_rate_k_m,
            "density_formula": "rho(h)=rho0*exp(-h/H)",
            "temperature_formula": "T(h)=T0-L*h",
            "viscosity_law": "Sutherland",
        }
