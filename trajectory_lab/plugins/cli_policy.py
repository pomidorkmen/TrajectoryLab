"""CLI policy for loading declarative tables and explicitly trusted Python plugins."""

from __future__ import annotations

import json
from pathlib import Path

from trajectory_lab.plugins.registry import DragModelRegistry, PluginLoadError


def registry_for_model(
    model_id: str, *, allow_python_plugins: bool
) -> DragModelRegistry:
    """Load data-only tables by default; execute Python extensions only by explicit opt-in."""
    registry = DragModelRegistry()
    registry.reload(load_python=allow_python_plugins)
    if model_id.startswith("plugin:"):
        try:
            registry.get(model_id)
        except PluginLoadError as exc:
            if registry.pending_python_files and not allow_python_plugins:
                raise PluginLoadError(
                    f"Model {model_id!r} is not loaded. Python plugins are not executed by default. "
                    "Review the files in ~/.trajectory_lab/models, then rerun with "
                    "--allow-python-plugins only if you trust every Python file in that folder."
                ) from exc
            raise
    return registry


def model_id_from_result(path: Path) -> str:
    """Read the drag model ID from a result JSON without executing plugin code."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    experiment = payload.get("experiment", payload)
    drag = experiment.get("drag", {})
    return str(drag.get("model", ""))
