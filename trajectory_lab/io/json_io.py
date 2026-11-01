"""Versioned JSON import/export and deterministic rerun helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


from trajectory_lab.core.simulation import Trajectory, simulate
from trajectory_lab.io.schemas import ExperimentSpec


def load_experiment(path: str | Path) -> ExperimentSpec:
    """Read and validate an experiment JSON file."""
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if "experiment" in payload:
        payload = payload["experiment"]
    return ExperimentSpec.model_validate(payload)


def trajectory_payload(trajectory: Trajectory) -> dict[str, Any]:
    """Create JSON-safe full trajectory data."""
    return {
        "columns": {
            "time_s": trajectory.time_s.tolist(),
            "position_m": trajectory.position_m.tolist(),
            "velocity_m_s": trajectory.velocity_m_s.tolist(),
            "speed_m_s": trajectory.speed_m_s.tolist(),
            "relative_speed_m_s": trajectory.relative_speed_m_s.tolist(),
            "mach": trajectory.mach.tolist(),
            "kinetic_energy_j": trajectory.kinetic_energy_j.tolist(),
            "reynolds": trajectory.reynolds.tolist(),
            "cd": trajectory.cd.tolist(),
        },
        "impact_time_s": trajectory.impact_time_s,
        "warnings": list(trajectory.warnings),
        "checksum_sha256": trajectory.checksum_sha256,
    }


def export_result_json(
    path: str | Path, experiment: ExperimentSpec, trajectory: Trajectory
) -> None:
    """Write input definition, provenance, full trajectory and checksum."""
    payload = {
        "format": "trajectory-lab-result",
        "format_version": "1.0",
        "experiment": experiment.model_dump(mode="json"),
        "provenance": trajectory.provenance,
        "trajectory": trajectory_payload(trajectory),
    }
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def rerun_result_json(
    path: str | Path, plugin_registry: Any | None = None
) -> tuple[ExperimentSpec, Trajectory, str | None]:
    """Re-run a result JSON and return the expected checksum if it was recorded."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    experiment = ExperimentSpec.model_validate(payload.get("experiment", payload))
    trajectory = simulate(
        experiment.to_core_config(plugin_registry),
        method=experiment.method,
        rtol=experiment.rtol,
        atol=experiment.atol,
    )
    expected = payload.get("trajectory", {}).get("checksum_sha256")
    return experiment, trajectory, expected
