"""Regression tests for user model loading, metadata validation and CSV import."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trajectory_lab.core.state import FlowState
from trajectory_lab.plugins.registry import DragModelRegistry, PluginLoadError, csv_points


EXAMPLES = Path(__file__).resolve().parents[1] / "models_examples"


def flow(reynolds: float = 10.0) -> FlowState:
    density = 1.2
    viscosity = 1.8e-5
    diameter = 0.01
    speed = reynolds * viscosity / (density * diameter)
    return FlowState(
        reynolds=reynolds,
        mach=speed / 343.0,
        velocity=speed,
        density=density,
        temperature=293.15,
        viscosity=viscosity,
        diameter=diameter,
    )


def test_python_plugin_is_not_executed_until_explicit_load(tmp_path: Path) -> None:
    registry = DragModelRegistry(tmp_path / "models")
    registry.install_python_file(EXAMPLES / "constant_cd.py")
    registry.reload()
    assert registry.pending_python_files
    assert not registry.records

    registry.load_python_plugins()
    record = registry.record("plugin:example.constant_cd")
    assert record.kind == "python"
    assert len(record.sha256) == 64
    assert record.model.cd(flow()) == pytest.approx(0.47)
    assert record.model.describe()["file_sha256"] == record.sha256


def test_python_plugin_fingerprint_changes_when_source_changes(tmp_path: Path) -> None:
    target = tmp_path / "models" / "mutable.py"
    target.parent.mkdir()
    target.write_text((EXAMPLES / "constant_cd.py").read_text(encoding="utf-8"), encoding="utf-8")
    registry = DragModelRegistry(target.parent)
    registry.reload(load_python=True)
    first = registry.record("plugin:example.constant_cd").sha256
    target.write_text(target.read_text(encoding="utf-8") + "\n# updated\n", encoding="utf-8")
    registry.reload(load_python=True)
    second = registry.record("plugin:example.constant_cd").sha256
    assert first != second


def test_invalid_python_plugin_interface_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "models"
    target.mkdir()
    (target / "bad.py").write_text(
        "class NotADragModel:\n    pass\n", encoding="utf-8"
    )
    registry = DragModelRegistry(target)
    registry.reload(load_python=True)
    assert not registry.records
    assert registry.errors
    assert "BaseDragModel" in registry.errors[0][1]


def test_python_plugin_cd_outside_strict_contract_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "models"
    target.mkdir()
    (target / "bad_cd.py").write_text(
        "from trajectory_lab.core.drag.base import BaseDragModel\n"
        "class BadCd(BaseDragModel):\n"
        "    def cd(self, state): return 100.0\n"
        "    def describe(self): return {'id':'bad.cd','name':'Bad','version':'1.0','author':'x','source':'x','validity':{'reynolds_min':0.0,'reynolds_max':100.0}}\n",
        encoding="utf-8",
    )
    registry = DragModelRegistry(target)
    registry.reload(load_python=True)
    assert not registry.records
    assert "expected 0 < Cd < 100" in registry.errors[0][1]


def test_json_table_model_loads_and_file_hash_is_in_metadata(tmp_path: Path) -> None:
    registry = DragModelRegistry(tmp_path / "models")
    installed = registry.install_table_file(EXAMPLES / "tabular_cd.json")
    registry.reload()
    model_id = "plugin:example.tabular_sphere"
    record = registry.record(model_id)
    assert record.path == installed
    assert len(record.sha256) == 64
    assert record.model.describe()["file_sha256"] == record.sha256
    assert record.model.cd(flow(1.0)) > 0


def test_table_validity_metadata_cannot_lie_about_nodes(tmp_path: Path) -> None:
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    payload = {
        "schema_version": "1.0", "kind": "tabular_drag", "id": "misstated",
        "name": "Wrong validity", "version": "1.0", "author": "test", "source": "test",
        "geometry": "sphere", "validity": {"reynolds_min": 2.0, "reynolds_max": 20.0},
        "interpolation": "log-log", "extrapolation": "error",
        "points": [{"reynolds": 1.0, "cd": 24.0}, {"reynolds": 10.0, "cd": 2.4}],
    }
    (model_dir / "misstated.json").write_text(json.dumps(payload), encoding="utf-8")
    registry = DragModelRegistry(model_dir)
    registry.reload()
    assert not registry.records
    assert "must match the actual table boundary" in registry.errors[0][1]


def test_csv_points_accepts_named_header_and_checks_sort_order(tmp_path: Path) -> None:
    csv_file = tmp_path / "table.csv"
    csv_file.write_text("Reynolds,Cd\n1,24\n10,2.4\n", encoding="utf-8")
    assert csv_points(csv_file) == [
        {"reynolds": 1.0, "cd": 24.0},
        {"reynolds": 10.0, "cd": 2.4},
    ]
    csv_file.write_text("Re,Cd\n10,2.4\n1,24\n", encoding="utf-8")
    with pytest.raises(PluginLoadError, match="strictly increasing"):
        csv_points(csv_file)


def test_table_models_can_keep_large_low_reynolds_cd(tmp_path: Path) -> None:
    from trajectory_lab.core.drag.base import cd_validation_limit

    registry = DragModelRegistry(tmp_path / "models")
    registry.install_table_file(EXAMPLES / "tabular_cd.json")
    registry.reload()
    model = registry.get("plugin:example.tabular_sphere")
    assert model.cd(flow(0.01)) == pytest.approx(2415.0)
    assert cd_validation_limit(model) >= 2415.0


def test_plugin_hash_and_metadata_are_embedded_in_simulation_provenance(tmp_path: Path) -> None:
    from trajectory_lab.core.atmosphere.constant import ConstantAtmosphere
    from trajectory_lab.core.simulation import SimulationConfig, simulate

    registry = DragModelRegistry(tmp_path / "models")
    registry.install_python_file(EXAMPLES / "constant_cd.py")
    registry.reload(load_python=True)
    record = registry.record("plugin:example.constant_cd")
    config = SimulationConfig(
        mass_kg=1.0,
        diameter_m=0.01,
        initial_position_m=(0.0, 10.0, 0.0),
        initial_velocity_m_s=(1.0, 0.0, 0.0),
        duration_s=0.1,
        step_s=0.01,
        gravity_m_s2=(0.0, -9.80665, 0.0),
        wind_velocity_m_s=(0.0, 0.0, 0.0),
        atmosphere=ConstantAtmosphere(1.2, 293.15, 1.8e-5),
        drag_model=record.model,
        seed=1729,
    )
    trajectory = simulate(config, method="rk4")
    assert trajectory.provenance["drag_model"]["file_sha256"] == record.sha256
    assert trajectory.provenance["drag_model_sha256"]
    assert len(trajectory.checksum_sha256) == 64


def test_experiment_schema_accepts_plugin_namespace_and_rejects_unknown_builtin_ids() -> None:
    from pydantic import ValidationError

    from trajectory_lab.io.schemas import DragSpec

    assert DragSpec(model="plugin:research.model_v1").model == "plugin:research.model_v1"
    with pytest.raises(ValidationError):
        DragSpec(model="not_a_builtin")


def test_plugin_applicability_warning_uses_declared_reynolds_interval(tmp_path: Path) -> None:
    from trajectory_lab.core.drag.base import applicability_warning

    registry = DragModelRegistry(tmp_path / "models")
    registry.install_python_file(EXAMPLES / "reynolds_power.py")
    registry.reload(load_python=True)
    model = registry.get("plugin:example.reynolds_power")

    inside = applicability_warning(model, 10.0)
    outside = applicability_warning(model, 2000.0)

    assert inside is None
    assert outside is not None
    assert "Re=2000" in outside
    assert "[0.1, 1000]" in outside


def test_python_plugin_directory_is_removed_from_sys_path_after_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    model_dir = tmp_path / "models"
    model_dir.mkdir()
    source = model_dir / "plugin.py"
    source.write_text(
        (EXAMPLES / "constant_cd.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    registry = DragModelRegistry(model_dir)
    path = str(model_dir.resolve())
    assert path not in sys.path

    registry.reload(load_python=True)

    assert path not in sys.path
    assert registry.record("plugin:example.constant_cd").model.cd(flow()) == pytest.approx(0.47)
