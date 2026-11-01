"""Pydantic v2 input schemas with strict dimensional validation via Pint."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trajectory_lab.io.units import convert_to_si

if TYPE_CHECKING:
    from trajectory_lab.core.simulation import SimulationConfig


class QuantityValue(BaseModel):
    """A numeric value with a mandatory unit string, e.g. `{value: 2, unit: 'cm'}`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float
    unit: str

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Quantity value must be finite")
        return value

    @field_validator("unit")
    @classmethod
    def nonempty_unit(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Physical quantity must include a unit")
        return value.strip()

    def si(self, target_unit: str) -> float:
        """Convert the quantity to a canonical SI value."""
        return convert_to_si(self.value, self.unit, target_unit)


class AtmosphereSpec(BaseModel):
    """Atmospheric model selection and dimensional parameters."""

    model_config = ConfigDict(extra="forbid")

    model: Literal["constant", "exponential", "isa"] = "isa"
    density: QuantityValue = Field(default_factory=lambda: QuantityValue(value=1.225, unit="kg/m^3"))
    temperature: QuantityValue = Field(default_factory=lambda: QuantityValue(value=288.15, unit="K"))
    scale_height: QuantityValue = Field(default_factory=lambda: QuantityValue(value=8500.0, unit="m"))
    temperature_lapse_rate: QuantityValue = Field(
        default_factory=lambda: QuantityValue(value=0.0065, unit="K/m")
    )
    viscosity: QuantityValue | None = None


class TablePoint(BaseModel):
    """One dimensionless Re/Cd data point."""

    model_config = ConfigDict(extra="forbid")

    reynolds: float = Field(gt=0)
    cd: float = Field(gt=0, lt=1.0e8)


class DragSpec(BaseModel):
    """Built-in or registered user drag model configuration."""

    model_config = ConfigDict(extra="forbid")

    model: str = "schiller_naumann"
    cd: float = Field(default=0.44, gt=0, lt=100.0)
    points: list[TablePoint] = Field(default_factory=list)
    interpolation: Literal["linear", "log-log", "cubic-log-log"] = "log-log"
    extrapolation: Literal["clamp", "extrapolate", "error"] = "error"
    name: str = "User tabular sphere model"
    version: str = "1.0.0"

    @field_validator("model")
    @classmethod
    def validate_model_id(cls, value: str) -> str:
        builtins = {"none", "stokes", "schiller_naumann", "cgw_composite", "quadratic", "tabular"}
        if value not in builtins and not value.startswith("plugin:"):
            raise ValueError("Drag model must be a built-in ID or a registered plugin:<id>")
        if value.startswith("plugin:") and not value.removeprefix("plugin:").strip():
            raise ValueError("Plugin drag model ID cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_table(self) -> "DragSpec":
        if self.model == "tabular":
            if len(self.points) < 2:
                raise ValueError("Tabular drag model requires at least two points")
            reynolds = [point.reynolds for point in self.points]
            if any(right <= left for left, right in zip(reynolds, reynolds[1:])):
                raise ValueError("Tabular Reynolds values must be strictly increasing")
        return self


class ExperimentSpec(BaseModel):
    """Versioned experiment definition with all dimensional inputs unit-tagged."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    name: str = "Untitled experiment"
    mass: QuantityValue
    diameter: QuantityValue
    initial_position: tuple[QuantityValue, QuantityValue, QuantityValue]
    initial_velocity: tuple[QuantityValue, QuantityValue, QuantityValue]
    duration: QuantityValue
    time_step: QuantityValue
    gravity: tuple[QuantityValue, QuantityValue, QuantityValue] = Field(
        default_factory=lambda: (
            QuantityValue(value=0.0, unit="m/s^2"),
            QuantityValue(value=-9.80665, unit="m/s^2"),
            QuantityValue(value=0.0, unit="m/s^2"),
        )
    )
    wind_velocity: tuple[QuantityValue, QuantityValue, QuantityValue] = Field(
        default_factory=lambda: (
            QuantityValue(value=0.0, unit="m/s"),
            QuantityValue(value=0.0, unit="m/s"),
            QuantityValue(value=0.0, unit="m/s"),
        )
    )
    atmosphere: AtmosphereSpec = Field(default_factory=AtmosphereSpec)
    drag: DragSpec = Field(default_factory=DragSpec)
    method: Literal["rk4", "dop853"] = "rk4"
    stop_at_ground: bool = True
    rtol: float = Field(default=1e-9, gt=0)
    atol: float | tuple[float, float, float, float, float, float] = 1e-12
    seed: int = 0

    @model_validator(mode="after")
    def validate_dimensions_and_ranges(self) -> "ExperimentSpec":
        self.mass.si("kg")
        self.diameter.si("m")
        for quantity in self.initial_position:
            quantity.si("m")
        for quantity in self.initial_velocity:
            quantity.si("m/s")
        self.duration.si("s")
        self.time_step.si("s")
        for quantity in self.gravity:
            quantity.si("m/s^2")
        for quantity in self.wind_velocity:
            quantity.si("m/s")
        self.atmosphere.density.si("kg/m^3")
        self.atmosphere.temperature.si("K")
        self.atmosphere.scale_height.si("m")
        self.atmosphere.temperature_lapse_rate.si("K/m")
        if self.atmosphere.viscosity is not None:
            self.atmosphere.viscosity.si("Pa*s")

        mass_si = self.mass.si("kg")
        diameter_si = self.diameter.si("m")
        duration_si = self.duration.si("s")
        step_si = self.time_step.si("s")
        if mass_si <= 0 or diameter_si <= 0 or duration_si <= 0 or step_si <= 0:
            raise ValueError("Mass, diameter, maximum simulation time and time step must be positive")
        if self.stop_at_ground and self.initial_position[1].si("m") < 0.0:
            raise ValueError("Initial height cannot be below y=0 when ground stopping is enabled")
        if self.atmosphere.density.si("kg/m^3") <= 0:
            raise ValueError("Atmosphere density must be positive")
        if self.atmosphere.temperature.si("K") <= 0:
            raise ValueError("Atmosphere temperature must be positive")
        if self.atmosphere.scale_height.si("m") <= 0:
            raise ValueError("Atmosphere scale height must be positive")
        if self.atmosphere.temperature_lapse_rate.si("K/m") < 0:
            raise ValueError("Atmosphere temperature lapse rate cannot be negative")
        if self.atmosphere.viscosity is not None and self.atmosphere.viscosity.si("Pa*s") <= 0:
            raise ValueError("Atmosphere viscosity must be positive")
        if self.atmosphere.model == "isa":
            isa_defaults_unchanged = (
                math.isclose(self.atmosphere.density.si("kg/m^3"), 1.225, rel_tol=0.0, abs_tol=1e-12)
                and math.isclose(self.atmosphere.temperature.si("K"), 288.15, rel_tol=0.0, abs_tol=1e-12)
                and math.isclose(self.atmosphere.scale_height.si("m"), 8500.0, rel_tol=0.0, abs_tol=1e-9)
                and math.isclose(self.atmosphere.temperature_lapse_rate.si("K/m"), 0.0065, rel_tol=0.0, abs_tol=1e-12)
                and self.atmosphere.viscosity is None
            )
            if not isa_defaults_unchanged:
                raise ValueError("ISA properties are fixed; do not override density, temperature, scale height or viscosity")
        if self.atmosphere.model == "exponential" and self.atmosphere.viscosity is not None:
            raise ValueError("Exponential atmosphere uses Sutherland viscosity; constant viscosity is only for model='constant'")
        if self.atmosphere.model == "constant" and (
            not math.isclose(self.atmosphere.scale_height.si("m"), 8500.0, rel_tol=0.0, abs_tol=1e-9)
            or not math.isclose(self.atmosphere.temperature_lapse_rate.si("K/m"), 0.0065, rel_tol=0.0, abs_tol=1e-12)
        ):
            raise ValueError("Scale height and temperature lapse apply only to the exponential atmosphere")
        if isinstance(self.atol, tuple) and (
            len(self.atol) != 6 or any(not math.isfinite(value) or value <= 0 for value in self.atol)
        ):
            raise ValueError("atol vector must contain six finite positive values")
        return self

    def to_core_config(self, plugin_registry: Any | None = None) -> "SimulationConfig":
        """Convert validated values into the Pint-free SI core.

        User model IDs use the ``plugin:<id>`` namespace and are resolved by
        the optional registry supplied by the desktop application or CLI.
        """
        from trajectory_lab.core.atmosphere import (
            ConstantAtmosphere,
            ExponentialAtmosphere,
            ISAAtmosphere,
        )
        from trajectory_lab.core.drag.registry import build_drag_model
        from trajectory_lab.core.simulation import SimulationConfig

        if self.atmosphere.model == "constant":
            atmosphere = ConstantAtmosphere(
                density_kg_m3=self.atmosphere.density.si("kg/m^3"),
                temperature_k=self.atmosphere.temperature.si("K"),
                viscosity_pa_s=(
                    self.atmosphere.viscosity.si("Pa*s")
                    if self.atmosphere.viscosity is not None
                    else None
                ),
            )
        elif self.atmosphere.model == "exponential":
            atmosphere = ExponentialAtmosphere(
                sea_level_density_kg_m3=self.atmosphere.density.si("kg/m^3"),
                scale_height_m=self.atmosphere.scale_height.si("m"),
                temperature_k=self.atmosphere.temperature.si("K"),
                temperature_lapse_rate_k_m=self.atmosphere.temperature_lapse_rate.si("K/m"),
            )
        else:
            atmosphere = ISAAtmosphere()

        drag_options: dict[str, Any] = {
            "cd": self.drag.cd,
            "points": [point.model_dump() for point in self.drag.points],
            "interpolation": self.drag.interpolation,
            "extrapolation": self.drag.extrapolation,
            "name": self.drag.name,
            "version": self.drag.version,
        }
        if self.drag.model.startswith("plugin:"):
            if plugin_registry is None:
                raise ValueError(
                    f"Experiment requires {self.drag.model!r}; load the user model registry first"
                )
            drag_model = plugin_registry.get(self.drag.model)
        else:
            drag_model = build_drag_model(self.drag.model, drag_options)

        return SimulationConfig(
            mass_kg=self.mass.si("kg"),
            diameter_m=self.diameter.si("m"),
            initial_position_m=(
                self.initial_position[0].si("m"),
                self.initial_position[1].si("m"),
                self.initial_position[2].si("m"),
            ),
            initial_velocity_m_s=(
                self.initial_velocity[0].si("m/s"),
                self.initial_velocity[1].si("m/s"),
                self.initial_velocity[2].si("m/s"),
            ),
            duration_s=self.duration.si("s"),
            step_s=self.time_step.si("s"),
            gravity_m_s2=(
                self.gravity[0].si("m/s^2"),
                self.gravity[1].si("m/s^2"),
                self.gravity[2].si("m/s^2"),
            ),
            wind_velocity_m_s=(
                self.wind_velocity[0].si("m/s"),
                self.wind_velocity[1].si("m/s"),
                self.wind_velocity[2].si("m/s"),
            ),
            atmosphere=atmosphere,
            drag_model=drag_model,
            seed=self.seed,
            stop_at_ground=self.stop_at_ground,
        )


def parse_experiment(payload: dict[str, Any]) -> ExperimentSpec:
    """Validate an experiment dictionary."""
    return ExperimentSpec.model_validate(payload)
