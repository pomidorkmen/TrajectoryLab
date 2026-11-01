from __future__ import annotations

import json
from pathlib import Path

import pytest

import pint  # noqa: F401 - unit-aware IO tests require the real Pint package

from trajectory_lab.core.simulation import simulate
from trajectory_lab.io.csv_io import export_trajectory_csv
from trajectory_lab.io.json_io import export_result_json, load_experiment, rerun_result_json

ROOT = Path(__file__).resolve().parents[1]


def test_json_export_and_rerun_checksum(tmp_path: Path) -> None:
    spec = load_experiment(ROOT / "examples" / "vacuum_reference.json")
    trajectory = simulate(spec.to_core_config(), method=spec.method)
    output = tmp_path / "result.json"
    export_result_json(output, spec, trajectory)
    _, rerun, expected = rerun_result_json(output)
    assert expected == trajectory.checksum_sha256
    assert rerun.checksum_sha256 == expected


def test_csv_export_contains_full_columns(tmp_path: Path) -> None:
    spec = load_experiment(ROOT / "examples" / "vacuum_reference.json")
    trajectory = simulate(spec.to_core_config(), method=spec.method)
    output = tmp_path / "result.csv"
    export_trajectory_csv(output, trajectory)
    lines = output.read_text(encoding="utf-8").splitlines()
    header = next(line for line in lines if not line.startswith("#"))
    assert "kinetic_energy_j" in header
    assert len(lines) > trajectory.time_s.size


def test_json_result_contains_impact_time_when_available(tmp_path: Path) -> None:
    spec = load_experiment(ROOT / "examples" / "vacuum_reference.json")
    from trajectory_lab.io.schemas import QuantityValue

    impact_spec = spec.model_copy(
        update={
            "duration": QuantityValue(value=1.5, unit="s"),
            "time_step": QuantityValue(value=0.037, unit="s"),
            "method": "dop853",
        }
    )
    trajectory = simulate(
        impact_spec.to_core_config(), method="dop853", atol=(1e-10,) * 6
    )
    assert trajectory.impact_time_s is not None
    output = tmp_path / "result.json"
    export_result_json(output, impact_spec, trajectory)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["trajectory"]["impact_time_s"] == trajectory.impact_time_s
