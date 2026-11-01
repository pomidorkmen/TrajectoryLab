"""Constant-property atmosphere."""

from __future__ import annotations

from dataclasses import dataclass
import math

from trajectory_lab.core.atmosphere.base import (
    AtmosphereState,
    ideal_gas_speed_of_sound,
    sutherland_viscosity,
)


@dataclass(frozen=True, slots=True)
class ConstantAtmosphere:
    """Constant density and temperature, useful for controlled experiments."""

    density_kg_m3: float = 1.225
    temperature_k: float = 288.15
    viscosity_pa_s: float | None = None

    def __post_init__(self) -> None:
        values = (self.density_kg_m3, self.temperature_k)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Constant-atmosphere properties must be finite")
        if self.density_kg_m3 <= 0 or self.temperature_k <= 0:
            raise ValueError("Constant-atmosphere density and temperature must be positive")
        if self.viscosity_pa_s is not None and (
            not math.isfinite(self.viscosity_pa_s) or self.viscosity_pa_s <= 0
        ):
            raise ValueError("Constant-atmosphere dynamic viscosity must be positive and finite")

    def at(self, altitude_m: float) -> AtmosphereState:
        del altitude_m
        viscosity = (
            self.viscosity_pa_s
            if self.viscosity_pa_s is not None
            else sutherland_viscosity(self.temperature_k)
        )
        return AtmosphereState(
            density=self.density_kg_m3,
            temperature=self.temperature_k,
            viscosity=viscosity,
            speed_of_sound=ideal_gas_speed_of_sound(self.temperature_k),
        )

    def describe(self) -> dict[str, object]:
        return {
            "id": "atmosphere.constant",
            "name": "Constant properties",
            "version": "1.0.0",
            "density_kg_m3": self.density_kg_m3,
            "temperature_k": self.temperature_k,
            "viscosity_pa_s": (
                self.viscosity_pa_s
                if self.viscosity_pa_s is not None
                else sutherland_viscosity(self.temperature_k)
            ),
        }
