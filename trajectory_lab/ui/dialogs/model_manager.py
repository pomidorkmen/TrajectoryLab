"""Dock-independent manager and editor for user drag models."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from trajectory_lab.core.drag.tabular import TabularDragModel
from trajectory_lab.plugins.registry import DragModelRegistry, csv_points


class TabularModelEditor(QDialog):
    """Create or import a versioned Cd(Re) table and save it as a JSON model."""

    def __init__(self, translate: Any, registry: DragModelRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tr_key = translate
        self.registry = registry
        self.setWindowTitle(self.tr_key("models.table_editor"))
        self.resize(700, 520)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.model_id = QLineEdit("custom_sphere_table")
        self.name = QLineEdit(self.tr_key("models.default_table_name"))
        self.version = QLineEdit("1.0.0")
        self.author = QLineEdit(self.tr_key("models.default_author"))
        self.source = QLineEdit(self.tr_key("models.default_source"))
        self.geometry = QLineEdit("sphere")
        self.interpolation = QComboBox()
        self.interpolation.addItem(self.tr_key("models.interp_loglog"), "log-log")
        self.interpolation.addItem(self.tr_key("models.interp_linear"), "linear")
        self.interpolation.addItem(self.tr_key("models.interp_cubic"), "cubic-log-log")
        self.extrapolation = QComboBox()
        self.extrapolation.addItem(self.tr_key("models.extra_error"), "error")
        self.extrapolation.addItem(self.tr_key("models.extra_clamp"), "clamp")
        self.extrapolation.addItem(self.tr_key("models.extra_extrapolate"), "extrapolate")
        for label, widget in (
            (self.tr_key("models.id"), self.model_id),
            (self.tr_key("models.name"), self.name),
            (self.tr_key("models.version"), self.version),
            (self.tr_key("models.author"), self.author),
            (self.tr_key("models.source"), self.source),
            (self.tr_key("models.geometry"), self.geometry),
            (self.tr_key("models.interpolation"), self.interpolation),
            (self.tr_key("models.extrapolation"), self.extrapolation),
        ):
            form.addRow(label, widget)
        root.addLayout(form)

        self.table = QTableWidget(4, 2)
        self.table.setHorizontalHeaderLabels([
            self.tr_key("models.table_re"), self.tr_key("models.table_cd")
        ])
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        for row, pair in enumerate(((0.1, 240.0), (1.0, 27.6), (10.0, 4.15), (100.0, 1.118))):
            self._set_row(row, pair[0], pair[1])
        root.addWidget(self.table, 1)

        row_actions = QHBoxLayout()
        self.add_row_button = QPushButton(self.tr_key("models.add_row"))
        self.remove_row_button = QPushButton(self.tr_key("models.remove_row"))
        self.import_csv_button = QPushButton(self.tr_key("models.import_csv"))
        row_actions.addWidget(self.add_row_button)
        row_actions.addWidget(self.remove_row_button)
        row_actions.addStretch(1)
        row_actions.addWidget(self.import_csv_button)
        root.addLayout(row_actions)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)
        self.add_row_button.clicked.connect(self._add_row)
        self.remove_row_button.clicked.connect(self._remove_row)
        self.import_csv_button.clicked.connect(self._import_csv)
        self.saved_path: Path | None = None

    def _set_row(self, row: int, reynolds: float, cd_value: float) -> None:
        for column, value in enumerate((reynolds, cd_value)):
            item = QTableWidgetItem(f"{value:.12g}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, column, item)

    def _add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._set_row(row, 1000.0 if row == 0 else 10.0 ** (row - 1), 0.44)

    def _remove_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr_key("models.select_csv"), str(Path.home()), "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            points = csv_points(Path(path))
            self.table.setRowCount(len(points))
            for row, point in enumerate(points):
                self._set_row(row, point["reynolds"], point["cd"])
            self.source.setText(f"Imported from {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, self.tr_key("models.error"), str(exc))

    def _collect_points(self) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for row in range(self.table.rowCount()):
            re_item = self.table.item(row, 0)
            cd_item = self.table.item(row, 1)
            if re_item is None or cd_item is None:
                continue
            if not re_item.text().strip() and not cd_item.text().strip():
                continue
            points.append((float(re_item.text()), float(cd_item.text())))
        return points

    def _save(self) -> None:
        try:
            model_id = self.model_id.text().strip()
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", model_id):
                raise ValueError("Model ID may contain only letters, digits, dot, underscore and hyphen")
            points = self._collect_points()
            model = TabularDragModel(
                points=points,
                interpolation=str(self.interpolation.currentData()),
                extrapolation=str(self.extrapolation.currentData()),
                model_name=self.name.text().strip(),
                model_version=self.version.text().strip(),
            )
            if not self.name.text().strip() or not self.version.text().strip():
                raise ValueError("Model name and version are required")
            validity = model.describe()["validity"]
            payload = {
                "schema_version": "1.0",
                "kind": "tabular_drag",
                "id": model_id,
                "name": self.name.text().strip(),
                "version": self.version.text().strip(),
                "author": self.author.text().strip() or "Researcher",
                "source": self.source.text().strip() or "User-provided data",
                "geometry": self.geometry.text().strip() or "sphere",
                "validity": validity,
                "interpolation": str(self.interpolation.currentData()),
                "extrapolation": str(self.extrapolation.currentData()),
                "points": [{"reynolds": re_value, "cd": cd_value} for re_value, cd_value in points],
            }
            filename = f"{model_id}.json"
            target = self.registry.model_dir / filename
            if target.exists():
                raise FileExistsError(f"A model file already exists: {target.name}")
            target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            self.registry.reload(load_python=False)
            self.saved_path = target
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, self.tr_key("models.error"), str(exc))


class ModelManagerDialog(QDialog):
    """Inspect, import, validate and remove user drag models."""

    def __init__(self, translate: Any, registry: DragModelRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tr_key = translate
        self.registry = registry
        self.setWindowTitle(self.tr_key("models.manager"))
        self.resize(780, 540)
        root = QVBoxLayout(self)
        self.security_note = QLabel(self.tr_key("models.security_note"))
        self.security_note.setWordWrap(True)
        root.addWidget(self.security_note)
        body = QHBoxLayout()
        self.list_widget = QListWidget()
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        body.addWidget(self.list_widget, 2)
        body.addWidget(self.details, 3)
        root.addLayout(body, 1)
        actions = QHBoxLayout()
        self.reload_button = QPushButton(self.tr_key("models.reload"))
        self.import_python_button = QPushButton(self.tr_key("models.import_python"))
        self.load_python_button = QPushButton(self.tr_key("models.load_python"))
        self.import_table_button = QPushButton(self.tr_key("models.import_table"))
        self.create_table_button = QPushButton(self.tr_key("models.create_table"))
        self.remove_button = QPushButton(self.tr_key("models.remove"))
        for button in (
            self.reload_button, self.import_python_button, self.load_python_button,
            self.import_table_button, self.create_table_button, self.remove_button,
        ):
            actions.addWidget(button)
        root.addLayout(actions)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        close.accepted.connect(self.accept)
        close.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        root.addWidget(close)
        self.list_widget.currentRowChanged.connect(self._show_details)
        self.reload_button.clicked.connect(self._reload)
        self.import_python_button.clicked.connect(self._import_python)
        self.load_python_button.clicked.connect(self._load_python)
        self.import_table_button.clicked.connect(self._import_table)
        self.create_table_button.clicked.connect(self._create_table)
        self.remove_button.clicked.connect(self._remove)
        self._reload()

    def _reload(self) -> None:
        self.registry.reload(load_python=False)
        self._populate()

    def _populate(self, preferred: str | None = None) -> None:
        self.list_widget.clear()
        for record in self.registry.records:
            kind_label = self.tr_key("models.kind_python" if record.kind == "python" else "models.kind_table")
            item = f"{record.name}  v{record.version}  [{kind_label}]"
            from PySide6.QtWidgets import QListWidgetItem
            list_item = QListWidgetItem(item)
            list_item.setData(Qt.ItemDataRole.UserRole, record.model_id)
            self.list_widget.addItem(list_item)
        for path in self.registry.pending_python_files:
            from PySide6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(f"{path.name}  [{self.tr_key('models.pending')}] ")
            item.setData(Qt.ItemDataRole.UserRole, f"pending:{path.name}")
            self.list_widget.addItem(item)
        for path, error in self.registry.errors:
            from PySide6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(f"{path.name}  [{self.tr_key('models.invalid')}] ")
            item.setData(Qt.ItemDataRole.UserRole, f"error:{path.name}")
            item.setToolTip(error)
            self.list_widget.addItem(item)
        if preferred:
            for row in range(self.list_widget.count()):
                if self.list_widget.item(row).data(Qt.ItemDataRole.UserRole) == preferred:
                    self.list_widget.setCurrentRow(row)
                    break
        if self.list_widget.count() and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)
        self._show_details(self.list_widget.currentRow())

    def _show_details(self, row: int) -> None:
        if row < 0:
            self.details.setPlainText(self.tr_key("models.empty"))
            return
        model_id = self.list_widget.item(row).data(Qt.ItemDataRole.UserRole)
        if str(model_id).startswith("plugin:"):
            record = self.registry.record(model_id)
            self.details.setPlainText(json.dumps(record.public_metadata(), indent=2, ensure_ascii=False))
        elif str(model_id).startswith("pending:"):
            self.details.setPlainText(
                self.tr_key("models.pending_detail") + "\n\n"
                + str(self.registry.model_dir / str(model_id).removeprefix("pending:"))
            )
        else:
            path = str(model_id).removeprefix("error:")
            error = next((message for file_path, message in self.registry.errors if file_path.name == path), "")
            self.details.setPlainText(f"{path}\n\n{error}")

    def _import_python(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr_key("models.select_python"), str(Path.home()), "Python files (*.py)"
        )
        if not path:
            return
        answer = QMessageBox.warning(
            self, self.tr_key("models.security_title"), self.tr_key("models.security_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            target = self.registry.install_python_file(Path(path))
            self._reload()
            QMessageBox.information(
                self, self.tr_key("models.manager"), self.tr_key("models.imported").format(path=str(target))
            )
        except Exception as exc:
            QMessageBox.critical(self, self.tr_key("models.error"), str(exc))

    def _load_python(self) -> None:
        if not self.registry.pending_python_files:
            QMessageBox.information(self, self.tr_key("models.manager"), self.tr_key("models.no_pending"))
            return
        answer = QMessageBox.warning(
            self, self.tr_key("models.security_title"), self.tr_key("models.security_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.registry.load_python_plugins()
        self._populate()

    def _import_table(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr_key("models.select_table"), str(Path.home()), "JSON files (*.json)"
        )
        if not path:
            return
        try:
            target = self.registry.install_table_file(Path(path))
            self._reload()
            QMessageBox.information(
                self, self.tr_key("models.manager"), self.tr_key("models.imported").format(path=str(target))
            )
        except Exception as exc:
            QMessageBox.critical(self, self.tr_key("models.error"), str(exc))

    def _create_table(self) -> None:
        editor = TabularModelEditor(self.tr_key, self.registry, self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self._populate(f"plugin:{editor.saved_path.stem}" if editor.saved_path else None)

    def _remove(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0:
            return
        model_id = str(self.list_widget.item(row).data(Qt.ItemDataRole.UserRole))
        if not model_id.startswith("plugin:"):
            QMessageBox.information(self, self.tr_key("models.manager"), self.tr_key("models.remove_only_user"))
            return
        answer = QMessageBox.question(
            self, self.tr_key("models.manager"), self.tr_key("models.remove_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.registry.remove(model_id)
            self._populate()
