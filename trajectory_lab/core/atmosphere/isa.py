"""Dry-air ISA model using geometric input altitude and geopotential layers."""

from __future__ import annotations

from dataclasses import dataclass
import math

from trajectory_lab.core.atmosphere.base import (
    AtmosphereState,
    ideal_gas_speed_of_sound,
    sutherland_viscosity,
)

EARTH_RADIUS_M = 6_356_766.0
SEA_LEVEL_TEMPERATURE_K = 288.15
SEA_LEVEL_PRESSURE_PA = 101_325.0
DRY_AIR_GAS_CONSTANT_J_KG_K = 287.05287
STANDARD_GRAVITY_M_S2 = 9.80665
TROPOPAUSE_GEOPOTENTIAL_M = 11_000.0
LOWER_STRATOSPHERE_TOP_GEOPOTENTIAL_M = 20_000.0
TROPOPAUSE_TEMPERATURE_K = 216.65
TROPOSPHERIC_LAPSE_RATE_K_M = -0.0065


def geometric_to_geopotential(geometric_altitude_m: float) -> float:
    """Convert geometric altitude h to geopotential altitude H (ISA convention)."""
    if not math.isfinite(geometric_altitude_m) or geometric_altitude_m <= -EARTH_RADIUS_M:
        raise ValueError("Geometric altitude must be finite and greater than -Earth radius")
    return geometric_altitude_m * EARTH_RADIUS_M / (EARTH_RADIUS_M + geometric_altitude_m)


def geopotential_to_geometric(geopotential_altitude_m: float) -> float:
    """Convert geopotential altitude H to geometric altitude h."""
    if not math.isfinite(geopotential_altitude_m) or geopotential_altitude_m >= EARTH_RADIUS_M:
        raise ValueError("Geopotential altitude must be finite and smaller than Earth radius")
    return geopotential_altitude_m * EARTH_RADIUS_M / (EARTH_RADIUS_M - geopotential_altitude_m)


@dataclass(frozen=True, slots=True)
class ISAAtmosphere:
    """Dry-air ISA from -500 m to 20 km geopotential altitude.

    ``at(altitude_m)`` accepts geometric altitude, as supplied by the simulation
    coordinate. The standard ISA layer equations are evaluated after converting
    it to geopotential altitude. ``at_geopotential`` is available for reference
    tables whose altitude coordinate is already geopotential.
    """

    minimum_geopotential_altitude_m: float = -500.0
    maximum_geopotential_altitude_m: float = LOWER_STRATOSPHERE_TOP_GEOPOTENTIAL_M

    def at(self, altitude_m: float) -> AtmosphereState:
        """Return ISA properties at geometric altitude in metres."""
        geopotential_m = geometric_to_geopotential(altitude_m)
        for boundary in (0.0, TROPOPAUSE_GEOPOTENTIAL_M, LOWER_STRATOSPHERE_TOP_GEOPOTENTIAL_M):
            if math.isclose(geopotential_m, boundary, rel_tol=0.0, abs_tol=1e-9):
                geopotential_m = boundary
                break
        return self.at_geopotential(geopotential_m)

    def at_geopotential(self, altitude_m: float) -> AtmosphereState:
        """Return ISA properties at geopotential altitude in metres."""
        if not self.minimum_geopotential_altitude_m <= altitude_m <= self.maximum_geopotential_altitude_m:
            raise ValueError(
                f"ISA geopotential altitude {altitude_m:g} m outside supported range "
                f"[{self.minimum_geopotential_altitude_m:g}, "
                f"{self.maximum_geopotential_altitude_m:g}] m"
            )

        t0 = SEA_LEVEL_TEMPERATURE_K
        p0 = SEA_LEVEL_PRESSURE_PA
        gas_constant = DRY_AIR_GAS_CONSTANT_J_KG_K
        gravity = STANDARD_GRAVITY_M_S2
        lapse = TROPOSPHERIC_LAPSE_RATE_K_M
        tropopause = TROPOPAUSE_GEOPOTENTIAL_M

        if altitude_m < tropopause:
            temperature = t0 + lapse * altitude_m
            exponent = -gravity / (lapse * gas_constant)
            pressure = p0 * (temperature / t0) ** exponent
        else:
            # Используем точную опорную температуру на границе из ISA.
            temperature = TROPOPAUSE_TEMPERATURE_K
            exponent = -gravity * (altitude_m - tropopause) / (gas_constant * temperature)
            t11 = TROPOPAUSE_TEMPERATURE_K
            p11 = p0 * (t11 / t0) ** (-gravity / (lapse * gas_constant))
            pressure = p11 * math.exp(exponent)

        density = pressure / (gas_constant * temperature)
        return AtmosphereState(
            density=density,
            temperature=temperature,
            viscosity=sutherland_viscosity(temperature),
            speed_of_sound=ideal_gas_speed_of_sound(temperature),
        )

    def describe(self) -> dict[str, object]:
        return {
            "id": "atmosphere.isa",
            "name": "ISA dry air",
            "version": "1.1.0",
            "altitude_input": "geometric_m",
            "altitude_equations": "H = h*R/(R+h), R = 6356766 m",
            "geopotential_altitude_range_m": [
                self.minimum_geopotential_altitude_m,
                self.maximum_geopotential_altitude_m,
            ],
            "layers": "troposphere to 11 km geopotential; isothermal layer to 20 km",
            "viscosity_law": "Sutherland: mu0=1.716e-5 Pa*s, T0=273.15 K, S=110.4 K",
        }
