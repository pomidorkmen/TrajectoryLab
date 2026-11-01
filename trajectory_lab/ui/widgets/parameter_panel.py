"""Compact dockable experiment parameter editor."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trajectory_lab.io.schemas import ExperimentSpec


class ParameterPanel(QWidget):
    """Create validated Pydantic experiment specs from SI-valued controls."""

    experiment_edited = Signal()

    def __init__(self, translate: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tr_key = translate
        self.fields: dict[str, QDoubleSpinBox] = {}
        self.unit_keys: dict[str, str] = {}
        self.labels: dict[str, Any] = {}
        self.groups: dict[str, QGroupBox] = {}
        self.combos: dict[str, QComboBox] = {}
        self._loaded_atol_vector: tuple[float, float, float, float, float, float] | None = None
        self._seed = 1729
        self._build()

    def _spin(
        self, key: str, value: float, unit_key: str, *, minimum: float = -1e9,
        maximum: float = 1e9, decimals: int = 8, step: float = 0.1,
    ) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setDecimals(decimals)
        widget.setSingleStep(step)
        widget.setValue(value)
        widget.setSuffix(" " + self.tr_key(unit_key) if unit_key else "")
        widget.setKeyboardTracking(False)
        widget.setAlignment(Qt.AlignmentFlag.AlignRight)
        widget.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.fields[key] = widget
        self.unit_keys[key] = unit_key
        return widget

    def _combo(self, key: str, entries: tuple[tuple[str, str], ...]) -> QComboBox:
        combo = QComboBox()
        for data, text_key in entries:
            combo.addItem(self.tr_key(text_key), data)
        self.combos[key] = combo
        return combo

    def _form_group(self, group_key: str) -> QFormLayout:
        group = QGroupBox(self.tr_key(group_key))
        layout = QFormLayout(group)
        layout.setContentsMargins(6, 9, 6, 5)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(3)
        self.groups[group_key] = group
        self._content_layout.addWidget(group)
        return layout

    def _add(self, layout: QFormLayout, key: str, widget: QWidget) -> None:
        label = self.tr_key(key)
        qlabel = QLabel(label)
        qlabel.setMinimumWidth(100)
        layout.addRow(qlabel, widget)
        self.labels[key] = qlabel

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        self._content_layout = QVBoxLayout(body)
        self._content_layout.setContentsMargins(6, 5, 6, 5)
        self._content_layout.setSpacing(5)

        self.name_edit = QLineEdit()
        obj = self._form_group("group.object")
        self._add(obj, "field.name", self.name_edit)
        self._add(obj, "field.mass", self._spin("mass", 1.308996939e-9, "units.kg", minimum=1e-15, decimals=15, step=1e-9))
        self._add(obj, "field.diameter", self._spin("diameter", 1e-4, "units.m", minimum=1e-9, decimals=9, step=1e-5))

        initial = self._form_group("group.initial")
        self._add(initial, "field.x", self._spin("x", 0.0, "units.m", decimals=6))
        self._add(initial, "field.y", self._spin("y", 2.0, "units.m", minimum=-1e6, decimals=6))
        self._add(initial, "field.z", self._spin("z", 0.0, "units.m", decimals=6))
        self._add(initial, "field.vx", self._spin("vx", 0.0, "units.ms", decimals=6))
        self._add(initial, "field.vy", self._spin("vy", 0.0, "units.ms", decimals=6))
        self._add(initial, "field.vz", self._spin("vz", 0.0, "units.ms", decimals=6))
        self._add(initial, "field.duration", self._spin("duration", 0.75, "units.s", minimum=1e-6, decimals=5, step=0.1))
        self._add(initial, "field.step", self._spin("step", 0.001, "units.s", minimum=1e-7, decimals=7, step=0.001))
        self.stop_at_ground = QCheckBox(self.tr_key("field.stop_at_ground"))
        self.stop_at_ground.setChecked(True)
        self.stop_at_ground.setToolTip(self.tr_key("help.stop_at_ground"))
        initial.addRow(self.stop_at_ground)

        env = self._form_group("group.environment")
        self._add(env, "field.gravity_x", self._spin("gravity_x", 0.0, "units.accel", minimum=-100, maximum=100, decimals=6))
        self._add(env, "field.gravity_y", self._spin("gravity_y", -9.80665, "units.accel", minimum=-100, maximum=100, decimals=6))
        self._add(env, "field.gravity_z", self._spin("gravity_z", 0.0, "units.accel", minimum=-100, maximum=100, decimals=6))
        self._add(env, "field.wind_x", self._spin("wind_x", 0.0, "units.ms", decimals=5))
        self._add(env, "field.wind_y", self._spin("wind_y", 0.0, "units.ms", decimals=5))
        self._add(env, "field.wind_z", self._spin("wind_z", 0.0, "units.ms", decimals=5))
        self._add(env, "field.atmosphere", self._combo("atmosphere", (
            ("isa", "atmosphere.isa"), ("constant", "atmosphere.constant"),
            ("exponential", "atmosphere.exponential"),
        )))
        self._add(env, "field.density", self._spin("density", 1.225, "units.kgm3", minimum=1e-9, decimals=6))
        self._add(env, "field.temperature", self._spin("temperature", 288.15, "units.k", minimum=1, decimals=3))
        self._add(env, "field.viscosity", self._spin("viscosity", 1.7894e-5, "units.pas", minimum=1e-12, decimals=10))
        self._add(env, "field.scale_height", self._spin("scale_height", 8500, "units.m", minimum=1, decimals=1))
        self._add(env, "field.lapse", self._spin("lapse", 0.0065, "units.kms", minimum=0, decimals=7))

        drag = self._form_group("group.drag")
        self._add(drag, "field.drag", self._combo("drag", (
            ("none", "drag.none"), ("stokes", "drag.stokes"),
            ("schiller_naumann", "drag.schiller_naumann"),
            ("cgw_composite", "drag.cgw_composite"),
            ("quadratic", "drag.quadratic"), ("tabular", "drag.tabular"),
        )))
        self._add(drag, "field.cd", self._spin("cd", 0.44, "", minimum=1e-6, maximum=99.999, decimals=5))
        self._add(drag, "field.interpolation", self._combo("interpolation", (
            ("linear", "interpolation.linear"), ("log-log", "interpolation.log-log"),
            ("cubic-log-log", "interpolation.cubic-log-log"),
        )))
        self._add(drag, "field.extrapolation", self._combo("extrapolation", (
            ("error", "extrapolation.error"), ("clamp", "extrapolation.clamp"),
            ("extrapolate", "extrapolation.extrapolate"),
        )))

        numerical = self._form_group("group.numerical")
        self._add(numerical, "field.method", self._combo("method", (
            ("rk4", "integrator.rk4"), ("dop853", "integrator.dop853"),
        )))
        self._add(numerical, "field.rtol", self._spin("rtol", 1e-9, "", minimum=1e-14, maximum=0.1, decimals=15))
        self._add(numerical, "field.atol", self._spin("atol", 1e-12, "", minimum=1e-15, maximum=0.1, decimals=16))

        self.run_button = QPushButton(self.tr_key("button.run"))
        self.run_button.setMinimumHeight(28)
        self.reset_button = QPushButton(self.tr_key("button.reset"))
        self._content_layout.addWidget(self.run_button)
        self._content_layout.addWidget(self.reset_button)
        self._content_layout.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll)

        self.combos["atmosphere"].currentIndexChanged.connect(self._update_field_enablement)
        self.combos["drag"].currentIndexChanged.connect(self._update_field_enablement)
        for field in self.fields.values():
            field.valueChanged.connect(lambda _value: self.experiment_edited.emit())
        for combo in self.combos.values():
            combo.currentIndexChanged.connect(lambda _index: self.experiment_edited.emit())
        self.name_edit.textChanged.connect(lambda _text: self.experiment_edited.emit())
        self.stop_at_ground.toggled.connect(lambda _checked: self.experiment_edited.emit())
        self.fields["atol"].valueChanged.connect(self._clear_loaded_atol_vector)
        self._default_tabular_points = [
            {"reynolds": 1.0, "cd": 24.0},
            {"reynolds": 10.0, "cd": 4.15},
            {"reynolds": 100.0, "cd": 1.09},
            {"reynolds": 1000.0, "cd": 0.44},
            {"reynolds": 10000.0, "cd": 0.40},
        ]
        self._tabular_points = list(self._default_tabular_points)
        self._tabular_name = "User tabular sphere model"
        self._tabular_version = "1.0.0"
        self._update_field_enablement()

    def _update_field_enablement(self) -> None:
        atmosphere = self.combos["atmosphere"].currentData()
        for key in ("density", "temperature", "viscosity", "scale_height", "lapse"):
            enabled = atmosphere != "isa"
            if key == "viscosity":
                enabled = atmosphere == "constant"
            if key in ("scale_height", "lapse"):
                enabled = atmosphere == "exponential"
            self.fields[key].setEnabled(enabled)
        is_quadratic = self.combos["drag"].currentData() == "quadratic"
        self.fields["cd"].setEnabled(is_quadratic)
        is_tabular = self.combos["drag"].currentData() == "tabular"
        self.combos["interpolation"].setEnabled(is_tabular)
        self.combos["extrapolation"].setEnabled(is_tabular)

    def set_plugin_models(self, models: list[tuple[str, str]]) -> None:
        """Append currently registered user models to the drag selector."""
        combo = self.combos["drag"]
        current = combo.currentData()
        while combo.count() and str(combo.itemData(combo.count() - 1)).startswith("plugin:"):
            combo.removeItem(combo.count() - 1)
        for model_id, name in models:
            combo.addItem(name, model_id)
        index = combo.findData(current)
        if index >= 0:
            combo.setCurrentIndex(index)

    def retranslate(self) -> None:
        for key, label in self.labels.items():
            label.setText(self.tr_key(key))
        for key, unit_key in self.unit_keys.items():
            self.fields[key].setSuffix(" " + self.tr_key(unit_key) if unit_key else "")
        for key, group in self.groups.items():
            group.setTitle(self.tr_key(key))
        for combo_key, combo in self.combos.items():
            entry_prefix = {
                "atmosphere": "atmosphere.", "drag": "drag.",
                "interpolation": "interpolation.", "extrapolation": "extrapolation.",
                "method": "integrator.",
            }[combo_key]
            for index in range(combo.count()):
                item_data = str(combo.itemData(index))
                if combo_key == "drag" and item_data.startswith("plugin:"):
                    continue
                combo.setItemText(index, self.tr_key(entry_prefix + item_data))
        self.stop_at_ground.setText(self.tr_key("field.stop_at_ground"))
        self.stop_at_ground.setToolTip(self.tr_key("help.stop_at_ground"))
        self.run_button.setText(self.tr_key("button.run"))
        self.reset_button.setText(self.tr_key("button.reset"))

    def to_spec(self) -> ExperimentSpec:
        """Validate all user entries through Pint-backed Pydantic schemas."""
        def q(key: str, unit: str) -> dict[str, Any]:
            return {"value": self.fields[key].value(), "unit": unit}

        atmosphere_model = str(self.combos["atmosphere"].currentData())
        atmosphere: dict[str, Any] = {"model": atmosphere_model}
        if atmosphere_model != "isa":
            atmosphere.update({
                "density": q("density", "kg/m^3"),
                "temperature": q("temperature", "K"),
            })
        if atmosphere_model == "constant":
            atmosphere["viscosity"] = q("viscosity", "Pa*s")
        if atmosphere_model == "exponential":
            atmosphere.update({
                "scale_height": q("scale_height", "m"),
                "temperature_lapse_rate": q("lapse", "K/m"),
            })

        drag_model = str(self.combos["drag"].currentData())
        drag: dict[str, Any] = {"model": drag_model}
        if drag_model == "quadratic":
            drag["cd"] = self.fields["cd"].value()
        if drag_model == "tabular":
            drag.update({
                "points": self._tabular_points,
                "interpolation": self.combos["interpolation"].currentData(),
                "extrapolation": self.combos["extrapolation"].currentData(),
                "name": self._tabular_name,
                "version": self._tabular_version,
            })

        payload = {
            "schema_version": "1.0",
            "name": self.name_edit.text().strip() or "Untitled experiment",
            "mass": q("mass", "kg"),
            "diameter": q("diameter", "m"),
            "initial_position": [q("x", "m"), q("y", "m"), q("z", "m")],
            "initial_velocity": [q("vx", "m/s"), q("vy", "m/s"), q("vz", "m/s")],
            "duration": q("duration", "s"),
            "time_step": q("step", "s"),
            "gravity": [q("gravity_x", "m/s^2"), q("gravity_y", "m/s^2"), q("gravity_z", "m/s^2")],
            "wind_velocity": [q("wind_x", "m/s"), q("wind_y", "m/s"), q("wind_z", "m/s")],
            "atmosphere": atmosphere,
            "drag": drag,
            "method": self.combos["method"].currentData(),
            "stop_at_ground": self.stop_at_ground.isChecked(),
            "rtol": self.fields["rtol"].value(),
            "atol": list(self._loaded_atol_vector) if self._loaded_atol_vector is not None else self.fields["atol"].value(),
            "seed": self._seed,
        }
        return ExperimentSpec.model_validate(payload)

    def load_spec(self, spec: ExperimentSpec) -> None:
        """Populate controls from a validated JSON experiment."""
        self.name_edit.setText(spec.name)
        self._tabular_points = [point.model_dump() for point in spec.drag.points] or list(self._default_tabular_points)
        self._tabular_name = spec.drag.name
        self._tabular_version = spec.drag.version
        values = {
            "mass": spec.mass.si("kg"), "diameter": spec.diameter.si("m"),
            "x": spec.initial_position[0].si("m"), "y": spec.initial_position[1].si("m"),
            "z": spec.initial_position[2].si("m"), "vx": spec.initial_velocity[0].si("m/s"),
            "vy": spec.initial_velocity[1].si("m/s"), "vz": spec.initial_velocity[2].si("m/s"),
            "duration": spec.duration.si("s"), "step": spec.time_step.si("s"),
            "gravity_x": spec.gravity[0].si("m/s^2"), "gravity_y": spec.gravity[1].si("m/s^2"),
            "gravity_z": spec.gravity[2].si("m/s^2"),
            "wind_x": spec.wind_velocity[0].si("m/s"), "wind_y": spec.wind_velocity[1].si("m/s"),
            "wind_z": spec.wind_velocity[2].si("m/s"),
            "density": spec.atmosphere.density.si("kg/m^3"),
            "temperature": spec.atmosphere.temperature.si("K"),
            "scale_height": spec.atmosphere.scale_height.si("m"),
            "lapse": spec.atmosphere.temperature_lapse_rate.si("K/m"),
            "viscosity": spec.atmosphere.viscosity.si("Pa*s") if spec.atmosphere.viscosity else 1.7894e-5,
            "cd": spec.drag.cd, "rtol": spec.rtol, "atol": float(spec.atol) if isinstance(spec.atol, (int, float)) else float(spec.atol[0]),
        }
        for key, value in values.items():
            self.fields[key].setValue(value)
        self._loaded_atol_vector = (
            tuple(float(value) for value in spec.atol)
            if isinstance(spec.atol, tuple)
            else None
        )
        self._seed = spec.seed
        self.stop_at_ground.setChecked(spec.stop_at_ground)
        self._set_combo("atmosphere", spec.atmosphere.model)
        self._set_combo("drag", spec.drag.model)
        self._set_combo("method", spec.method)
        self._set_combo("interpolation", spec.drag.interpolation)
        self._set_combo("extrapolation", spec.drag.extrapolation)
        self._update_field_enablement()

    def _clear_loaded_atol_vector(self, value: float) -> None:
        del value
        self._loaded_atol_vector = None

    def _set_combo(self, key: str, value: str) -> None:
        index = self.combos[key].findData(value)
        if index >= 0:
            self.combos[key].setCurrentIndex(index)

    def reset(self, spec: ExperimentSpec) -> None:
        self.load_spec(spec)
