"""Point-mass sphere simulation; no dependency on the graphical UI."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import platform
import sys
import warnings
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Sequence

import numpy as np
import numpy.typing as npt
import scipy

from trajectory_lab import __version__
from trajectory_lab.core.atmosphere.base import Atmosphere
from trajectory_lab.core.drag.base import (
    BaseDragModel,
    DragModelApplicabilityWarning,
    applicability_warning,
    cd_validation_limit,
    validate_cd,
)
from trajectory_lab.core.integrators.base import IntegrationResult
from trajectory_lab.core.integrators.dop853 import DOP853Integrator
from trajectory_lab.core.integrators.rk4 import RK4Integrator
from trajectory_lab.core.state import FlowState, reynolds_number


Vector3 = tuple[float, float, float]
Atol = float | Sequence[float] | npt.NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Validated SI-only settings for one spherical-particle experiment."""

    mass_kg: float
    diameter_m: float
    initial_position_m: Vector3
    initial_velocity_m_s: Vector3
    duration_s: float
    step_s: float
    gravity_m_s2: Vector3
    wind_velocity_m_s: Vector3
    atmosphere: Atmosphere
    drag_model: BaseDragModel | None
    seed: int = 0
    stop_at_ground: bool = True

    def __post_init__(self) -> None:
        scalar_values = (self.mass_kg, self.diameter_m, self.duration_s, self.step_s)
        if not all(math.isfinite(value) and value > 0 for value in scalar_values):
            raise ValueError("Mass, diameter, duration and step must be finite and positive")
        for vector_name, vector in (
            ("initial_position_m", self.initial_position_m),
            ("initial_velocity_m_s", self.initial_velocity_m_s),
            ("gravity_m_s2", self.gravity_m_s2),
            ("wind_velocity_m_s", self.wind_velocity_m_s),
        ):
            if len(vector) != 3 or not all(math.isfinite(value) for value in vector):
                raise ValueError(f"{vector_name} must contain three finite SI values")
        if self.stop_at_ground and self.initial_position_m[1] < 0.0:
            raise ValueError("Initial height cannot be below y=0 when ground stopping is enabled")


@dataclass(frozen=True, slots=True)
class Trajectory:
    """Sampled trajectory and derived quantities, all in SI units."""

    time_s: npt.NDArray[np.float64]
    position_m: npt.NDArray[np.float64]
    velocity_m_s: npt.NDArray[np.float64]
    speed_m_s: npt.NDArray[np.float64]
    relative_speed_m_s: npt.NDArray[np.float64]
    mach: npt.NDArray[np.float64]
    kinetic_energy_j: npt.NDArray[np.float64]
    reynolds: npt.NDArray[np.float64]
    cd: npt.NDArray[np.float64]
    impact_time_s: float | None
    warnings: tuple[str, ...]
    provenance: dict[str, Any]
    checksum_sha256: str

    @property
    def range_m(self) -> float:
        """Horizontal displacement magnitude from the initial position."""
        displacement = self.position_m[-1, (0, 2)] - self.position_m[0, (0, 2)]
        return float(np.linalg.norm(displacement))

    @property
    def apogee(self) -> tuple[float, float]:
        """Return (maximum height, time at maximum) using cubic Hermite segments.

        The interpolation uses sampled height and vertical velocity at each
        segment endpoint. For constant acceleration it is exact even when the
        apex falls between output samples; for varying acceleration it is a
        local dense-output approximation.
        """
        times = self.time_s
        heights = self.position_m[:, 1]
        vertical_speeds = self.velocity_m_s[:, 1]
        best_height = float(heights[0])
        best_time = float(times[0])
        for index in range(max(0, times.size - 1)):
            t0 = float(times[index])
            h = float(times[index + 1] - times[index])
            y0 = float(heights[index])
            y1 = float(heights[index + 1])
            v0 = float(vertical_speeds[index])
            v1 = float(vertical_speeds[index + 1])
            c0 = y0
            c1 = h * v0
            c2 = -3.0 * y0 - 2.0 * h * v0 + 3.0 * y1 - h * v1
            c3 = 2.0 * y0 + h * v0 - 2.0 * y1 + h * v1
            roots: list[float] = []
            if abs(c3) < 1e-15:
                if abs(c2) > 1e-15:
                    roots.append(-c1 / (2.0 * c2))
            else:
                for root in np.roots((3.0 * c3, 2.0 * c2, c1)):
                    if abs(float(np.imag(root))) < 1e-10:
                        roots.append(float(np.real(root)))
            for fraction in roots:
                if 0.0 < fraction < 1.0:
                    height = c0 + c1 * fraction + c2 * fraction**2 + c3 * fraction**3
                    if height > best_height:
                        best_height = float(height)
                        best_time = t0 + fraction * h
            if y1 > best_height:
                best_height = y1
                best_time = float(times[index + 1])
        return best_height, best_time

    @property
    def maximum_height_m(self) -> float:
        """Interpolated maximum height in metres."""
        return self.apogee[0]

    @property
    def maximum_height_time_s(self) -> float:
        """Time of interpolated maximum height in seconds."""
        return self.apogee[1]


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def _trajectory_checksum(columns: npt.NDArray[np.float64]) -> str:
    """Hash a per-column, relative-1e-9 quantization of the trajectory.

    Each numeric column is normalized by its largest absolute value and then
    rounded to a 1e-9 relative grid. The scale is serialized with 9 significant
    digits; integer bins avoid platform-specific binary-float byte layouts.
    This is a tolerant regression checksum, not a claim of exact reproducibility.
    """
    values = np.asarray(columns, dtype=np.float64)
    if values.ndim != 2 or not np.all(np.isfinite(values)):
        raise ValueError("Trajectory checksum requires a finite 2-D numeric array")

    canonical_columns: list[dict[str, object]] = []
    for column_index in range(values.shape[1]):
        column = values[:, column_index]
        scale = float(np.max(np.abs(column)))
        if scale == 0.0:
            scale = 1.0
            quantized = [0] * int(column.size)
        else:
            quantized = [int(round(float(value / scale) * 1_000_000_000)) for value in column]
        canonical_columns.append(
            {"scale": format(scale, ".10g"), "values_1e9": quantized}
        )

    payload = json.dumps(
        {"quantization": "per-column relative 1e-9", "columns": canonical_columns},
        separators=(",", ":"),
        ensure_ascii=True,
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _atol_for_provenance(atol: Atol) -> float | list[float]:
    if isinstance(atol, (float, int)):
        return float(atol)
    return np.asarray(atol, dtype=float).tolist()


def simulate(
    config: SimulationConfig,
    *,
    method: str = "rk4",
    rtol: float = 1e-9,
    atol: Atol = 1e-12,
) -> Trajectory:
    """Integrate a rigid sphere under gravity, buoyancy and fluid drag.

    Coordinates are x/z horizontal and y upward. ``duration_s`` is always a
    maximum time. When ``stop_at_ground`` is enabled, both RK4 and DOP853 stop
    at the first downward y=0 crossing and localize the event between samples.
    Otherwise the trajectory continues to the maximum time.
    """
    if method not in {"rk4", "dop853"}:
        raise ValueError("method must be 'rk4' or 'dop853'")
    if rtol <= 0 or not math.isfinite(rtol):
        raise ValueError("rtol must be finite and positive")
    if isinstance(atol, (float, int)):
        if atol <= 0 or not math.isfinite(float(atol)):
            raise ValueError("atol must be finite and positive")
    else:
        atol_array = np.asarray(atol, dtype=float)
        if atol_array.shape != (6,) or not np.all(np.isfinite(atol_array)) or np.any(atol_array <= 0):
            raise ValueError("atol vector must contain six finite positive state tolerances")

    mass = config.mass_kg
    diameter = config.diameter_m
    area = math.pi * diameter**2 / 4.0
    volume = math.pi * diameter**3 / 6.0
    gravity = np.asarray(config.gravity_m_s2, dtype=float)
    wind = np.asarray(config.wind_velocity_m_s, dtype=float)
    drag_model = config.drag_model
    warning_set: set[str] = set()

    def calculate_cd(flow_state: FlowState) -> float:
        assert drag_model is not None
        warning_message = applicability_warning(drag_model, flow_state.reynolds)
        if warning_message:
            # Emit one Python warning per simulation; the warning text records the first
            # out-of-range Re and the trajectory keeps the summary in its metadata.
            if not warning_set:
                warnings.warn(warning_message, DragModelApplicabilityWarning, stacklevel=3)
                warning_set.add(warning_message)
        return validate_cd(drag_model.cd(flow_state), upper_limit=cd_validation_limit(drag_model))

    def rhs(time_s: float, state: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        del time_s
        position = state[:3]
        velocity = state[3:]
        acceleration = gravity.copy()

        # Atmosphere and drag coefficient are deliberately recomputed on every RK stage.
        ambient = config.atmosphere.at(float(position[1]))
        relative_velocity = velocity - wind
        relative_speed = float(np.linalg.norm(relative_velocity))

        if drag_model is not None:
            acceleration -= (ambient.density * volume / mass) * gravity
            if relative_speed > 1e-14:
                reynolds = reynolds_number(
                    ambient.density, relative_speed, diameter, ambient.viscosity
                )
                mach = relative_speed / ambient.speed_of_sound
                flow_state = FlowState(
                    reynolds=reynolds,
                    mach=mach,
                    velocity=relative_speed,
                    density=ambient.density,
                    temperature=ambient.temperature,
                    viscosity=ambient.viscosity,
                    diameter=diameter,
                )
                cd_value = calculate_cd(flow_state)
                drag_force = (
                    -0.5
                    * ambient.density
                    * cd_value
                    * area
                    * relative_speed
                    * relative_velocity
                )
                acceleration += drag_force / mass

        return np.concatenate((velocity, acceleration))

    initial_state = np.asarray((*config.initial_position_m, *config.initial_velocity_m_s), dtype=float)
    terminal_event = {"terminal_event_index": 1, "terminal_event_value": 0.0} if config.stop_at_ground else {}
    if method == "rk4":
        integrator = RK4Integrator()
        integration: IntegrationResult = integrator.integrate(
            rhs, initial_state, config.duration_s, config.step_s, **terminal_event
        )
    else:
        integrator = DOP853Integrator()
        integration = integrator.integrate(
            rhs,
            initial_state,
            config.duration_s,
            config.step_s,
            rtol=rtol,
            atol=atol,
            **terminal_event,
        )

    positions = integration.state[:, :3]
    velocities = integration.state[:, 3:]
    speeds = np.linalg.norm(velocities, axis=1)
    relative_velocities = velocities - wind[None, :]
    relative_speeds = np.linalg.norm(relative_velocities, axis=1)
    mach = np.empty(integration.time_s.size, dtype=float)
    reynolds = np.zeros(integration.time_s.size, dtype=float)
    cd_values = np.zeros(integration.time_s.size, dtype=float)

    for index, (position, relative_speed) in enumerate(zip(positions, relative_speeds, strict=True)):
        ambient = config.atmosphere.at(float(position[1]))
        mach[index] = relative_speed / ambient.speed_of_sound
        if relative_speed > 1e-14:
            reynolds[index] = reynolds_number(
                ambient.density, float(relative_speed), diameter, ambient.viscosity
            )
            if drag_model is not None:
                state = FlowState(
                    reynolds=float(reynolds[index]),
                    mach=float(mach[index]),
                    velocity=float(relative_speed),
                    density=ambient.density,
                    temperature=ambient.temperature,
                    viscosity=ambient.viscosity,
                    diameter=diameter,
                )
                cd_values[index] = calculate_cd(state)

    kinetic_energy = 0.5 * mass * speeds**2
    checksum_columns = np.column_stack(
        (
            integration.time_s,
            positions,
            velocities,
            speeds,
            relative_speeds,
            mach,
            kinetic_energy,
            reynolds,
            cd_values,
        )
    )
    model_description = (
        drag_model.describe()
        if drag_model is not None
        else {
            "id": "drag.disabled",
            "name": "Drag disabled (gravity-only reference)",
            "version": "1.0.0",
        }
    )
    fingerprint_payload = (
        drag_model.fingerprint_payload() if drag_model is not None else model_description
    )
    model_hash = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    provenance = {
        "trajectory_lab_version": __version__,
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "pint_version": _package_version("pint"),
        "platform": platform.platform(),
        "method": integrator.name,
        "step_s": config.step_s,
        "rtol": rtol if method == "dop853" else None,
        "atol": _atol_for_provenance(atol) if method == "dop853" else None,
        "trajectory_checksum_quantization": "per-column relative 1e-9",
        "seed": config.seed,
        "drag_model": model_description,
        "drag_model_sha256": model_hash,
        "atmosphere_model": config.atmosphere.describe(),
        "stop_at_ground": config.stop_at_ground,
        "termination_reason": "ground" if integration.event_time_s is not None else "maximum_time",
        "ground_impact_time_s": integration.event_time_s,
    }
    return Trajectory(
        time_s=integration.time_s,
        position_m=positions,
        velocity_m_s=velocities,
        speed_m_s=speeds,
        relative_speed_m_s=relative_speeds,
        mach=mach,
        kinetic_energy_j=kinetic_energy,
        reynolds=reynolds,
        cd=cd_values,
        impact_time_s=integration.event_time_s,
        warnings=tuple(sorted(warning_set)),
        provenance=provenance,
        checksum_sha256=_trajectory_checksum(checksum_columns),
    )


def stokes_terminal_velocity(
    particle_density_kg_m3: float,
    fluid_density_kg_m3: float,
    radius_m: float,
    dynamic_viscosity_pa_s: float,
    gravity_m_s2: float = 9.80665,
) -> float:
    """Terminal settling speed from effective mass and Stokes' drag law.

    This is ``m_effective*g/(6*pi*mu*r)``, where m_effective is particle
    mass minus displaced-fluid mass. It is algebraically identical to the
    density-difference form commonly quoted for a sphere.
    """
    values = (
        particle_density_kg_m3,
        fluid_density_kg_m3,
        radius_m,
        dynamic_viscosity_pa_s,
        gravity_m_s2,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Terminal-velocity inputs must be finite")
    if particle_density_kg_m3 <= fluid_density_kg_m3:
        raise ValueError("Particle density must exceed fluid density for downward settling")
    if radius_m <= 0 or dynamic_viscosity_pa_s <= 0 or gravity_m_s2 <= 0:
        raise ValueError("Radius, viscosity and gravity must be positive")

    volume = 4.0 * math.pi * radius_m**3 / 3.0
    effective_mass = (particle_density_kg_m3 - fluid_density_kg_m3) * volume
    return effective_mass * gravity_m_s2 / (6.0 * math.pi * dynamic_viscosity_pa_s * radius_m)
