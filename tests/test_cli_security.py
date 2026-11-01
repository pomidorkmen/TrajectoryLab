"""Security regression tests for explicit opt-in to executable CLI plugins."""

from __future__ import annotations

from pathlib import Path

import pytest

from trajectory_lab.plugins.cli_policy import registry_for_model
from trajectory_lab.plugins.registry import PluginLoadError


def test_cli_registry_does_not_execute_python_plugins_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    models = tmp_path / ".trajectory_lab" / "models"
    models.mkdir(parents=True)
    marker = tmp_path / "plugin_was_executed.txt"
    (models / "unexpected.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )

    registry = registry_for_model("builtin:stokes", allow_python_plugins=False)

    assert marker.exists() is False
    assert registry.pending_python_files


def test_cli_requires_explicit_opt_in_for_missing_python_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    models = tmp_path / ".trajectory_lab" / "models"
    models.mkdir(parents=True)
    (models / "example.py").write_text("# trusted only after explicit opt-in\n", encoding="utf-8")

    with pytest.raises(PluginLoadError, match="--allow-python-plugins"):
        registry_for_model("plugin:some.model", allow_python_plugins=False)
