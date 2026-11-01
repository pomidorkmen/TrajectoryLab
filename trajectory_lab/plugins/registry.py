"""User drag-model registry for JSON tables and trusted Python extensions.

Python extensions execute in-process and are NOT sandboxed. Only load files you trust.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import re
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from trajectory_lab.core.drag.base import BaseDragModel, validate_cd
from trajectory_lab.core.drag.tabular import TabularDragModel
from trajectory_lab.core.state import FlowState

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


class PluginLoadError(RuntimeError):
    """Raised when a user model cannot be loaded or validated."""


@dataclass(frozen=True, slots=True)
class DragModelRecord:
    """Loaded model and the provenance needed by the manager UI."""

    model_id: str
    name: str
    version: str
    author: str
    source: str
    geometry: str
    validity: dict[str, Any]
    sha256: str
    path: Path
    kind: str
    model: BaseDragModel

    def public_metadata(self) -> dict[str, Any]:
        return {
            "id": self.model_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "source": self.source,
            "geometry": self.geometry,
            "validity": self.validity,
            "sha256": self.sha256,
            "path": str(self.path),
            "kind": self.kind,
        }


class RegisteredModelAdapter(BaseDragModel):
    """Attach stable identity and file checksum to an already validated model."""

    def __init__(
        self,
        wrapped: BaseDragModel,
        metadata: dict[str, Any],
        file_sha256: str,
        *,
        allow_large_table_cd: bool = False,
    ) -> None:
        self._wrapped = wrapped
        self._metadata = dict(metadata)
        self._file_sha256 = file_sha256
        self._allow_large_table_cd = allow_large_table_cd
        self.cd_upper_limit = 1.0e12 if allow_large_table_cd else 100.0

    def cd(self, state: FlowState) -> float:
        value = float(self._wrapped.cd(state))
        return validate_cd(value, upper_limit=self.cd_upper_limit)

    def describe(self) -> dict[str, Any]:
        result = dict(self._metadata)
        result["file_sha256"] = self._file_sha256
        result["plugin_kind"] = "table" if self._allow_large_table_cd else "python"
        return result

    def validity_range(self) -> tuple[float, float]:
        validity = self._metadata.get("validity", {})
        lower = float(validity.get("reynolds_min", 0.0))
        upper_raw = validity.get("reynolds_max")
        upper = float(upper_raw) if upper_raw is not None else math.inf
        return lower, upper

    def fingerprint_payload(self) -> dict[str, Any]:
        wrapped_payload = self._wrapped.fingerprint_payload()
        return {
            "registered_model": self.describe(),
            "file_sha256": self._file_sha256,
            "model_parameters": wrapped_payload,
        }


class DragModelRegistry:
    """Load user models from ``~/.trajectory_lab/models``.

    JSON table files are declarative and safe to parse. Python files execute as
    normal Python modules in the application process; they are never sandboxed.
    """

    def __init__(self, model_dir: Path | None = None) -> None:
        self.model_dir = model_dir or (Path.home() / ".trajectory_lab" / "models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, DragModelRecord] = {}
        self._errors: list[tuple[Path, str]] = []
        self.python_plugins_enabled = False

    @property
    def records(self) -> tuple[DragModelRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    @property
    def errors(self) -> tuple[tuple[Path, str], ...]:
        return tuple(self._errors)

    def reload(self, *, load_python: bool | None = None) -> tuple[DragModelRecord, ...]:
        """Reload JSON tables; Python code is loaded only after an explicit trust action."""
        if load_python is not None:
            self.python_plugins_enabled = load_python
        self._records.clear()
        self._errors.clear()
        if not self.model_dir.exists():
            self.model_dir.mkdir(parents=True, exist_ok=True)
        for source in sorted(self.model_dir.glob("*.json")):
            try:
                record = self._load_table(source)
                self._add_record(record)
            except Exception as exc:
                self._errors.append((source, str(exc)))
        if self.python_plugins_enabled:
            self.load_python_plugins()
        return self.records

    def load_python_plugins(self) -> tuple[DragModelRecord, ...]:
        """Execute and validate every Python plugin in the user model folder."""
        self.python_plugins_enabled = True
        for source in sorted(self.model_dir.glob("*.py")):
            if source.name.startswith("_"):
                continue
            try:
                record = self._load_python(source)
                if record.model_id not in self._records:
                    self._add_record(record)
            except Exception as exc:
                self._errors.append((source, str(exc)))
        return self.records

    @property
    def pending_python_files(self) -> tuple[Path, ...]:
        loaded_paths = {record.path.resolve() for record in self._records.values() if record.kind == "python"}
        return tuple(
            source for source in sorted(self.model_dir.glob("*.py"))
            if not source.name.startswith("_") and source.resolve() not in loaded_paths
        )

    def get(self, model_id: str) -> BaseDragModel:
        try:
            return self._records[model_id].model
        except KeyError as exc:
            raise PluginLoadError(f"User drag model {model_id!r} is not loaded") from exc

    def record(self, model_id: str) -> DragModelRecord:
        try:
            return self._records[model_id]
        except KeyError as exc:
            raise PluginLoadError(f"User drag model {model_id!r} is not loaded") from exc

    def install_python_file(self, source: Path) -> Path:
        """Copy a Python extension into the user model directory after path checks."""
        source = source.expanduser().resolve()
        if not source.is_file() or source.suffix.lower() != ".py":
            raise PluginLoadError("Select an existing .py plugin file")
        target = self.model_dir / source.name
        if target.exists():
            target = self.model_dir / f"{source.stem}_{uuid.uuid4().hex[:8]}.py"
        shutil.copy2(source, target)
        return target

    def install_table_file(self, source: Path) -> Path:
        """Validate and copy a declarative JSON drag table."""
        source = source.expanduser().resolve()
        if not source.is_file() or source.suffix.lower() != ".json":
            raise PluginLoadError("Select an existing JSON table model")
        payload = json.loads(source.read_text(encoding="utf-8"))
        _table_model_from_payload(payload)
        target = self.model_dir / source.name
        if target.exists():
            target = self.model_dir / f"{source.stem}_{uuid.uuid4().hex[:8]}.json"
        shutil.copy2(source, target)
        return target

    def remove(self, model_id: str) -> None:
        """Remove a registered file after ensuring it belongs to model_dir."""
        record = self.record(model_id)
        resolved = record.path.resolve()
        if resolved.parent != self.model_dir.resolve():
            raise PluginLoadError("Refusing to remove a model outside the user models directory")
        resolved.unlink(missing_ok=True)
        self.reload()

    def _add_record(self, record: DragModelRecord) -> None:
        if record.model_id in self._records:
            raise PluginLoadError(f"Duplicate user model ID: {record.model_id}")
        self._records[record.model_id] = record

    def _load_table(self, source: Path) -> DragModelRecord:
        payload = json.loads(source.read_text(encoding="utf-8"))
        model = _table_model_from_payload(payload)
        metadata = _validated_metadata(payload)
        file_hash = _sha256_file(source)
        computed_validity = model.describe()["validity"]
        for field in ("reynolds_min", "reynolds_max"):
            supplied = metadata["validity"].get(field)
            computed = computed_validity.get(field)
            if supplied != computed:
                raise PluginLoadError(
                    f"Tabular model validity.{field} must match the actual table boundary ({computed!r})"
                )
        adapter = RegisteredModelAdapter(
            model, metadata, file_hash, allow_large_table_cd=True
        )
        return _record_from_metadata(metadata, adapter, source, file_hash, "table")

    def _load_python(self, source: Path) -> DragModelRecord:
        file_hash = _sha256_file(source)
        module_name = f"trajectory_lab_user_model_{file_hash[:16]}"
        spec = importlib.util.spec_from_file_location(module_name, source)
        if spec is None or spec.loader is None:
            raise PluginLoadError("Could not create an import specification for this plugin")
        module = importlib.util.module_from_spec(spec)
        model_path = str(source.parent.resolve())
        path_was_present = model_path in sys.path
        if not path_was_present:
            # Временно добавляем папку для импортов соседних модулей во время загрузки.
            # Не оставляем пользовательский каталог в sys.path после импорта: иначе
            # файлы из него могли бы затенять стандартные/сторонние модули приложения.
            sys.path.insert(0, model_path)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            model = _instantiate_plugin(module)
            metadata = _validated_metadata(model.describe())
            _validate_plugin_probe(model, metadata)
            adapter = RegisteredModelAdapter(model, metadata, file_hash)
            return _record_from_metadata(metadata, adapter, source, file_hash, "python")
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        finally:
            if not path_was_present:
                try:
                    sys.path.remove(model_path)
                except ValueError:
                    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _instantiate_plugin(module: ModuleType) -> BaseDragModel:
    factory: Callable[[], Any] | None = getattr(module, "create_model", None)
    if callable(factory):
        model = factory()
    else:
        model_class = getattr(module, "MODEL_CLASS", None)
        if model_class is None:
            candidates = [
                value
                for value in vars(module).values()
                if isinstance(value, type)
                and issubclass(value, BaseDragModel)
                and value is not BaseDragModel
                and value.__module__ == module.__name__
            ]
            if len(candidates) != 1:
                raise PluginLoadError(
                    "Plugin must expose create_model(), MODEL_CLASS, or exactly one BaseDragModel subclass"
                )
            model_class = candidates[0]
        if not isinstance(model_class, type) or not issubclass(model_class, BaseDragModel):
            raise PluginLoadError("MODEL_CLASS must inherit BaseDragModel")
        model = model_class()
    if not isinstance(model, BaseDragModel):
        raise PluginLoadError("Plugin factory must return a BaseDragModel instance")
    if not callable(getattr(model, "cd", None)) or not callable(getattr(model, "describe", None)):
        raise PluginLoadError("Plugin model must implement cd(state) and describe()")
    return model


def _validated_metadata(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PluginLoadError("describe() must return a dictionary")
    required = ("id", "name", "version", "author", "source", "validity")
    missing = [key for key in required if key not in raw]
    if missing:
        raise PluginLoadError("Model metadata is missing: " + ", ".join(missing))
    model_id = str(raw["id"])
    if not _ID_PATTERN.fullmatch(model_id):
        raise PluginLoadError("Model metadata id must use letters, digits, '.', '_' or '-'")
    for key in ("name", "version", "author", "source"):
        if not str(raw[key]).strip():
            raise PluginLoadError(f"Model metadata field {key!r} cannot be empty")
    validity = raw["validity"]
    if not isinstance(validity, dict):
        raise PluginLoadError("Model metadata validity must be a dictionary")
    lower = float(validity.get("reynolds_min", 0.0))
    upper_raw = validity.get("reynolds_max")
    upper = math.inf if upper_raw is None else float(upper_raw)
    if not math.isfinite(lower) or lower < 0 or upper <= lower or math.isnan(upper):
        raise PluginLoadError("Model validity must define 0 <= Re_min < Re_max")
    metadata = dict(raw)
    metadata["id"] = model_id
    metadata["name"] = str(raw["name"])
    metadata["version"] = str(raw["version"])
    metadata["author"] = str(raw["author"])
    metadata["source"] = str(raw["source"])
    metadata["geometry"] = str(raw.get("geometry", "sphere"))
    metadata["validity"] = dict(validity)
    return metadata


def _validate_plugin_probe(model: BaseDragModel, metadata: dict[str, Any]) -> None:
    validity = metadata["validity"]
    lower = float(validity.get("reynolds_min", 0.0))
    upper_raw = validity.get("reynolds_max")
    upper = math.inf if upper_raw is None else float(upper_raw)
    if math.isinf(upper):
        probe_re = max(10.0, lower * 10.0, 1.0)
    elif lower <= 0:
        probe_re = max(min(10.0, upper * 0.5), upper * 0.01)
    else:
        probe_re = math.sqrt(lower * upper)
    if not math.isfinite(probe_re) or probe_re <= 0:
        probe_re = max(lower, 1e-6)
    density = 1.2
    viscosity = 1.8e-5
    diameter = 0.01
    speed = probe_re * viscosity / (density * diameter)
    state = FlowState(
        reynolds=probe_re,
        mach=speed / 343.0,
        velocity=speed,
        density=density,
        temperature=293.15,
        viscosity=viscosity,
        diameter=diameter,
    )
    try:
        validate_cd(float(model.cd(state)))
    except Exception as exc:
        raise PluginLoadError(f"Plugin probe failed at Re={probe_re:.6g}: {exc}") from exc


def _record_from_metadata(
    metadata: dict[str, Any],
    model: BaseDragModel,
    source: Path,
    file_hash: str,
    kind: str,
) -> DragModelRecord:
    return DragModelRecord(
        model_id=f"plugin:{metadata['id']}",
        name=str(metadata["name"]),
        version=str(metadata["version"]),
        author=str(metadata["author"]),
        source=str(metadata["source"]),
        geometry=str(metadata["geometry"]),
        validity=dict(metadata["validity"]),
        sha256=file_hash,
        path=source,
        kind=kind,
        model=model,
    )


def _table_model_from_payload(payload: Any) -> TabularDragModel:
    if not isinstance(payload, dict):
        raise PluginLoadError("Tabular model JSON root must be an object")
    if payload.get("schema_version") != "1.0":
        raise PluginLoadError("Unsupported tabular model schema_version")
    if payload.get("kind") != "tabular_drag":
        raise PluginLoadError("JSON model kind must be 'tabular_drag'")
    metadata = _validated_metadata(payload)
    points_payload = payload.get("points")
    if not isinstance(points_payload, list):
        raise PluginLoadError("Tabular model points must be a list")
    try:
        points = [(float(item["reynolds"]), float(item["cd"])) for item in points_payload]
        return TabularDragModel(
            points=points,
            interpolation=payload.get("interpolation", "log-log"),
            extrapolation=payload.get("extrapolation", "error"),
            model_name=metadata["name"],
            model_version=metadata["version"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PluginLoadError(f"Invalid tabular model data: {exc}") from exc


def csv_points(path: Path) -> list[dict[str, float]]:
    """Read a CSV with Re/Cd headers or two numeric columns."""
    path = path.expanduser().resolve()
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.reader(stream))
    if not rows:
        raise PluginLoadError("CSV table is empty")
    header = [cell.strip().lower() for cell in rows[0]]
    has_header = any(value in {"re", "reynolds", "cd"} for value in header)
    data_rows = rows[1:] if has_header else rows
    if has_header:
        re_index = next((i for i, value in enumerate(header) if value in {"re", "reynolds"}), None)
        cd_index = next((i for i, value in enumerate(header) if value == "cd"), None)
        if re_index is None or cd_index is None:
            raise PluginLoadError("CSV header must contain Re/Reynolds and Cd columns")
    else:
        re_index, cd_index = 0, 1
    points: list[dict[str, float]] = []
    for line_number, row in enumerate(data_rows, start=2 if has_header else 1):
        if not row or all(not value.strip() for value in row):
            continue
        try:
            points.append({"reynolds": float(row[re_index]), "cd": float(row[cd_index])})
        except (IndexError, ValueError) as exc:
            raise PluginLoadError(f"Invalid CSV values on line {line_number}") from exc
    # Reuse the numerical table validator to catch duplicate, unsorted or nonpositive values.
    try:
        TabularDragModel(
            [(item["reynolds"], item["cd"]) for item in points],
            interpolation="log-log",
            extrapolation="error",
        )
    except ValueError as exc:
        raise PluginLoadError(str(exc)) from exc
    return points
