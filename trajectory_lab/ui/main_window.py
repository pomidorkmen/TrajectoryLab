"""Main PySide6 window: dock panels, plots, data table and experiment workflow."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
import traceback
from typing import Any
import warnings

from PySide6.QtCore import QObject, QSettings, Qt, QThread, QCoreApplication, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QFontDatabase, QIcon, QKeySequence, QPixmap
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPlainTextEdit,
    QPushButton,
    QStyle,
    QTabWidget,
    QVBoxLayout,
    QTableView,
    QToolBar,
)

import pyqtgraph as pg

from trajectory_lab import __version__
from trajectory_lab.core.simulation import Trajectory, simulate
from trajectory_lab.io.csv_io import export_trajectory_csv
from trajectory_lab.io.json_io import export_result_json, load_experiment
from trajectory_lab.io.pdf_report import export_pdf_report
from trajectory_lab.io.schemas import ExperimentSpec
from trajectory_lab.plugins.registry import DragModelRegistry
from trajectory_lab.privacy import LocalPathRedactionFilter
from trajectory_lab.ui.dialogs.model_manager import ModelManagerDialog
from trajectory_lab.ui.i18n.translator import CatalogTranslator
from trajectory_lab.ui.models.trajectory_table import TrajectoryTableModel
from trajectory_lab.ui.widgets.parameter_panel import ParameterPanel
from trajectory_lab.ui.widgets.results_panel import ResultsPanel
from trajectory_lab.ui.widgets.trajectory_plots import (
    TimeSeriesWidget,
    Trajectory2DWidget,
    Trajectory3DWidget,
)


LOGGER = logging.getLogger("trajectory_lab.ui")


def resource_path(relative_path: str) -> Path:
    """Resolve files in source mode and PyInstaller bundles."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    base = Path(frozen_root) if frozen_root else Path(__file__).resolve().parents[2]
    return base / relative_path


class LogEmitter(QObject):
    """Thread-safe bridge from Python logging to the Qt journal panel."""

    message = Signal(str)


class SignalLogHandler(logging.Handler):
    """Forward formatted log records through a Qt signal."""

    def __init__(self, emitter: LogEmitter) -> None:
        super().__init__()
        self.emitter = emitter
        self.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.emitter.message.emit(self.format(record))
        except Exception:
            self.handleError(record)


class SimulationWorker(QObject):
    """Run the numerical core away from the GUI thread."""

    completed = Signal(object, object)
    failed = Signal(str)

    def __init__(self, spec: ExperimentSpec, plugin_registry: DragModelRegistry) -> None:
        super().__init__()
        self.spec = spec
        self.plugin_registry = plugin_registry

    def run(self) -> None:
        try:
            LOGGER.info("Starting experiment calculation")
            config = self.spec.to_core_config(self.plugin_registry)
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                trajectory = simulate(
                    config,
                    method=self.spec.method,
                    rtol=self.spec.rtol,
                    atol=self.spec.atol,
                )
            for item in captured:
                LOGGER.warning("%s", item.message)
            LOGGER.info(
                "Calculation complete: %d samples; checksum %s",
                trajectory.time_s.size,
                trajectory.checksum_sha256,
            )
            self.completed.emit(self.spec, trajectory)
        except Exception as exc:
            LOGGER.exception("Simulation failed")
            self.failed.emit(f"{exc}\n\n{traceback.format_exc()}")


class MainWindow(QMainWindow):
    """Strict, compact scientific desktop application."""

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.settings = QSettings("TrajectoryLab", "TrajectoryLab")
        self.language = str(self.settings.value("language", "en"))
        self.theme = str(self.settings.value("theme", "light"))
        self.catalog_dir = resource_path("trajectory_lab/ui/i18n")
        self.translator = CatalogTranslator(self.catalog_dir / f"{self.language}.json", self)
        self.app.installTranslator(self.translator)
        self.current_spec: ExperimentSpec | None = None
        self.baseline_spec: ExperimentSpec | None = None
        self.current_trajectory: Trajectory | None = None
        self.model_registry = DragModelRegistry()
        self.model_registry.reload(load_python=False)
        self._qt_log_handler: SignalLogHandler | None = None
        self._thread: QThread | None = None
        self._worker: SimulationWorker | None = None
        self.log_emitter = LogEmitter(self)
        self.log_emitter.message.connect(self._append_journal)
        self._configure_logging()
        self._build_widgets()
        self._build_actions()
        self._apply_theme()
        self.retranslate_ui()

        default_example = resource_path("examples/air_resistance_drop.json")
        if not default_example.is_file():
            default_example = Path(__file__).resolve().parents[1] / "examples" / "air_resistance_drop.json"
        try:
            self.current_spec = load_experiment(default_example)
            self.baseline_spec = self.current_spec
            self.parameter_panel.load_spec(self.current_spec)
        except Exception:
            LOGGER.exception("Could not load built-in default example")
        self.resize(
            int(self.settings.value("window/width", 1320)),
            int(self.settings.value("window/height", 860)),
        )
        dock_state = self.settings.value("window/state")
        if dock_state is not None:
            self.restoreState(dock_state)
        LOGGER.info("TrajectoryLab desktop interface initialized")

    def tr_key(self, key: str) -> str:
        return QCoreApplication.translate("TrajectoryLab", key)

    def _configure_logging(self) -> None:
        log_dir = Path.home() / ".trajectory_lab" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.setLevel(logging.INFO)
        if not any(isinstance(item, LocalPathRedactionFilter) for item in LOGGER.filters):
            LOGGER.addFilter(LocalPathRedactionFilter())
        if not any(isinstance(handler, logging.FileHandler) for handler in LOGGER.handlers):
            file_handler = logging.FileHandler(log_dir / "trajectory_lab.log", encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
            LOGGER.addHandler(file_handler)
        self._qt_log_handler = SignalLogHandler(self.log_emitter)
        LOGGER.addHandler(self._qt_log_handler)

    def _build_widgets(self) -> None:
        self.parameter_panel = ParameterPanel(self.tr_key)
        self.parameter_panel.set_plugin_models([
            (record.model_id, f"{record.name} v{record.version}")
            for record in self.model_registry.records
        ])
        self.parameter_panel.experiment_edited.connect(self._experiment_edited)
        self.parameter_dock = QDockWidget(self)
        self.parameter_dock.setObjectName("ParameterDock")
        self.parameter_dock.setWidget(self.parameter_panel)
        self.parameter_dock.setMinimumWidth(305)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.parameter_dock)

        self.results_panel = ResultsPanel(self.tr_key)
        self.results_dock = QDockWidget(self)
        self.results_dock.setObjectName("ResultsDock")
        self.results_dock.setWidget(self.results_panel)
        self.results_dock.setMinimumWidth(300)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.results_dock)

        self.journal = QPlainTextEdit()
        self.journal.setReadOnly(True)
        self.journal.setMaximumBlockCount(2500)
        self.journal_dock = QDockWidget(self)
        self.journal_dock.setObjectName("JournalDock")
        self.journal_dock.setWidget(self.journal)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.journal_dock)

        self.tabs = QTabWidget()
        self.plot_2d = Trajectory2DWidget(self.tr_key)
        self.plot_3d = Trajectory3DWidget(self.tr_key)
        self.time_series = TimeSeriesWidget(self.tr_key)
        self.table_model = TrajectoryTableModel(self.tr_key, self)
        self.sample_table = QTableView()
        self.sample_table.setModel(self.table_model)
        self.sample_table.setSortingEnabled(False)
        self.sample_table.setAlternatingRowColors(True)
        self.sample_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.sample_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.sample_table.horizontalHeader().setStretchLastSection(True)
        self.sample_table.horizontalHeader().setDefaultSectionSize(95)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.sample_table.setFont(fixed_font)
        self.tabs.addTab(self.plot_2d, "")
        self.tabs.addTab(self.plot_3d, "")
        self.tabs.addTab(self.time_series, "")
        self.tabs.addTab(self.sample_table, "")
        self.setCentralWidget(self.tabs)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMaximumWidth(130)
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().showMessage(self.tr_key("status.ready"))

        self.parameter_panel.run_button.clicked.connect(self.run_simulation)
        self.parameter_panel.reset_button.clicked.connect(self.reset_parameters)

    def _build_actions(self) -> None:
        style = self.style()
        self.action_open = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "", self)
        self.action_save = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "", self)
        self.action_run = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "", self)
        self.action_export_json = QAction("", self)
        self.action_export_csv = QAction("", self)
        self.action_export_pdf = QAction("", self)
        self.action_manage_models = QAction("", self)
        self.action_exit = QAction("", self)
        self.action_about = QAction("", self)
        self.action_manual_ru = QAction("", self)
        self.action_manual_en = QAction("", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_run.setShortcut(QKeySequence("F5"))
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_open.triggered.connect(self.open_experiment)
        self.action_save.triggered.connect(self.save_experiment)
        self.action_run.triggered.connect(self.run_simulation)
        self.action_export_json.triggered.connect(self.export_json)
        self.action_export_csv.triggered.connect(self.export_csv)
        self.action_export_pdf.triggered.connect(self.export_pdf)
        self.action_manage_models.triggered.connect(self.manage_models)
        self.action_exit.triggered.connect(self.close)
        self.action_about.triggered.connect(self.show_about)
        self.action_manual_ru.triggered.connect(lambda: self.open_manual("ru"))
        self.action_manual_en.triggered.connect(lambda: self.open_manual("en"))

        self.file_menu = self.menuBar().addMenu("")
        self.experiment_menu = self.menuBar().addMenu("")
        self.view_menu = self.menuBar().addMenu("")
        self.help_menu = self.menuBar().addMenu("")
        self.file_menu.addAction(self.action_open)
        self.file_menu.addAction(self.action_save)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.action_export_json)
        self.file_menu.addAction(self.action_export_csv)
        self.file_menu.addAction(self.action_export_pdf)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.action_exit)
        self.experiment_menu.addAction(self.action_run)
        self.experiment_menu.addSeparator()
        self.experiment_menu.addAction(self.action_manage_models)
        self.view_menu.addAction(self.parameter_dock.toggleViewAction())
        self.view_menu.addAction(self.results_dock.toggleViewAction())
        self.view_menu.addAction(self.journal_dock.toggleViewAction())
        self.view_menu.addSeparator()
        self.language_menu = self.view_menu.addMenu("")
        self.theme_menu = self.view_menu.addMenu("")
        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        self.action_language_en = QAction("", self)
        self.action_language_ru = QAction("", self)
        self.action_language_en.setCheckable(True)
        self.action_language_ru.setCheckable(True)
        self.language_group.addAction(self.action_language_en)
        self.language_group.addAction(self.action_language_ru)
        self.language_menu.addAction(self.action_language_en)
        self.language_menu.addAction(self.action_language_ru)
        self.action_language_en.triggered.connect(lambda: self.set_language("en"))
        self.action_language_ru.triggered.connect(lambda: self.set_language("ru"))
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.action_theme_light = QAction("", self)
        self.action_theme_dark = QAction("", self)
        self.action_theme_pink = QAction("", self)
        for action in (self.action_theme_light, self.action_theme_dark, self.action_theme_pink):
            action.setCheckable(True)
            self.theme_group.addAction(action)
            self.theme_menu.addAction(action)
        self.action_theme_light.triggered.connect(lambda: self.set_theme("light"))
        self.action_theme_dark.triggered.connect(lambda: self.set_theme("dark"))
        self.action_theme_pink.triggered.connect(lambda: self.set_theme("pink"))
        self.help_menu.addAction(self.action_manual_ru)
        self.help_menu.addAction(self.action_manual_en)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.action_about)

        self.toolbar = QToolBar(self)
        self.toolbar.setObjectName("MainToolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.toolbar.addAction(self.action_open)
        self.toolbar.addAction(self.action_save)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_run)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_export_json)
        self.toolbar.addAction(self.action_export_csv)
        self.toolbar.addAction(self.action_export_pdf)

    def retranslate_ui(self) -> None:
        self.setWindowTitle(self.tr_key("app.title"))
        icon_path = resource_path("trajectory_lab/ui/resources/trajectorylab.png")
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.parameter_dock.setWindowTitle(self.tr_key("dock.parameters"))
        self.results_dock.setWindowTitle(self.tr_key("dock.results"))
        self.journal_dock.setWindowTitle(self.tr_key("dock.journal"))
        for index, key in enumerate(("tab.trajectory", "tab.view3d", "tab.timeseries", "tab.samples")):
            self.tabs.setTabText(index, self.tr_key(key))
        self.file_menu.setTitle(self.tr_key("menu.file"))
        self.experiment_menu.setTitle(self.tr_key("menu.experiment"))
        self.view_menu.setTitle(self.tr_key("menu.view"))
        self.help_menu.setTitle(self.tr_key("menu.help"))
        self.language_menu.setTitle(self.tr_key("menu.language"))
        self.theme_menu.setTitle(self.tr_key("menu.theme"))
        self.action_open.setText(self.tr_key("action.open"))
        self.action_save.setText(self.tr_key("action.save"))
        self.action_run.setText(self.tr_key("action.run"))
        self.action_export_json.setText(self.tr_key("action.export_json"))
        self.action_export_csv.setText(self.tr_key("action.export_csv"))
        self.action_export_pdf.setText(self.tr_key("action.export_pdf"))
        self.action_manage_models.setText(self.tr_key("action.manage_models"))
        self.action_exit.setText(self.tr_key("action.exit"))
        self.action_about.setText(self.tr_key("action.about"))
        self.action_theme_light.setText(self.tr_key("action.light"))
        self.action_language_en.setText(self.tr_key("language.en"))
        self.action_language_ru.setText(self.tr_key("language.ru"))
        self.action_theme_dark.setText(self.tr_key("action.dark"))
        self.action_theme_pink.setText(self.tr_key("action.pink"))
        self.action_manual_ru.setText(self.tr_key("action.manual_ru"))
        self.action_manual_en.setText(self.tr_key("action.manual_en"))
        self.action_language_en.setChecked(self.language == "en")
        self.action_language_ru.setChecked(self.language == "ru")
        self.action_theme_light.setChecked(self.theme == "light")
        self.action_theme_dark.setChecked(self.theme == "dark")
        self.action_theme_pink.setChecked(self.theme == "pink")
        self.parameter_panel.retranslate()
        self.results_panel.retranslate()
        self.plot_2d.retranslate()
        self.time_series.retranslate()
        self.plot_3d.retranslate()
        self.table_model.retranslate()

    def _apply_theme(self) -> None:
        palette = {
            "light": ("#f5f7f8", "#252a2e", "#347ba5"),
            "dark": ("#202429", "#d8dcdf", "#5c9bc4"),
            "pink": ("#f7f0f4", "#382d34", "#c47f9c"),
        }
        if self.theme not in palette:
            self.theme = "light"
        background, foreground, accent = palette[self.theme]
        theme_path = resource_path(f"trajectory_lab/ui/resources/themes/{self.theme}.qss")
        self.app.setStyleSheet(theme_path.read_text(encoding="utf-8"))
        pg.setConfigOptions(background=background, foreground=foreground)
        self.plot_2d.setBackground(background)
        self.plot_2d.set_accent(accent)
        for plot in (*self.time_series.plots,):
            plot.setBackground(background)
        self.time_series.set_accent(accent)
        self.plot_3d.set_theme(background, accent)
        self.settings.setValue("theme", self.theme)

    def set_theme(self, theme: str) -> None:
        if theme not in {"light", "dark", "pink"}:
            return
        self.theme = theme
        self._apply_theme()
        self.retranslate_ui()
        LOGGER.info("Theme changed to %s", theme)

    def set_language(self, language: str) -> None:
        if language not in {"en", "ru"} or language == self.language:
            return
        self.app.removeTranslator(self.translator)
        self.translator.load_catalog(self.catalog_dir / f"{language}.json")
        self.language = language
        self.app.installTranslator(self.translator)
        self.settings.setValue("language", language)
        self.retranslate_ui()
        LOGGER.info("Language changed to %s", language)

    def _append_journal(self, message: str) -> None:
        self.journal.appendPlainText(message)

    def _clear_current_result(self) -> None:
        self.current_trajectory = None
        self.plot_2d.set_trajectory(None)
        self.plot_3d.set_trajectory(None)
        self.time_series.set_trajectory(None)
        self.table_model.set_trajectory(None)
        self.results_panel.clear()

    def _experiment_edited(self) -> None:
        if self.current_trajectory is None:
            return
        self._clear_current_result()
        self.statusBar().showMessage(self.tr_key("message.modified"), 5000)
        LOGGER.info("Experiment inputs changed; previous result invalidated")

    def reset_parameters(self) -> None:
        if self.baseline_spec is None:
            return
        self.parameter_panel.reset(self.baseline_spec)

    def run_simulation(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        try:
            spec = self.parameter_panel.to_spec()
            self._ensure_plugin_for_spec(spec)
            spec.to_core_config(self.model_registry)  # validate before starting the worker thread
        except Exception as exc:
            QMessageBox.warning(self, self.tr_key("message.validation"), str(exc))
            LOGGER.warning("Input validation failed: %s", exc)
            return

        self.current_spec = spec
        self._clear_current_result()
        self.action_run.setEnabled(False)
        self.parameter_panel.run_button.setEnabled(False)
        self.progress.show()
        self.statusBar().showMessage(self.tr_key("status.running"))
        self._thread = QThread(self)
        self._worker = SimulationWorker(spec, self.model_registry)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.completed.connect(self._simulation_completed)
        self._worker.failed.connect(self._simulation_failed)
        self._worker.completed.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._simulation_thread_finished)
        self._thread.start()

    def _simulation_completed(self, spec: ExperimentSpec, trajectory: Trajectory) -> None:
        self.current_spec = spec
        self.current_trajectory = trajectory
        self.plot_2d.set_trajectory(trajectory)
        self.plot_3d.set_trajectory(trajectory)
        self.time_series.set_trajectory(trajectory)
        self.table_model.set_trajectory(trajectory)
        self.results_panel.update_trajectory(trajectory)
        self.statusBar().showMessage(
            f"{self.tr_key('status.completed')} — {self.tr_key('status.samples')}: {trajectory.time_s.size}",
            10000,
        )
        for warning_text in trajectory.warnings:
            LOGGER.warning("%s", warning_text)

    def _simulation_failed(self, message: str) -> None:
        self.statusBar().showMessage(self.tr_key("status.failed"), 10000)
        QMessageBox.critical(self, self.tr_key("status.failed"), message.split("\n\n", 1)[0])

    def _simulation_thread_finished(self) -> None:
        self.progress.hide()
        self.action_run.setEnabled(True)
        self.parameter_panel.run_button.setEnabled(True)
        self._thread = None
        self._worker = None

    def open_experiment(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr_key("dialog.open_title"), str(Path.home()), self.tr_key("dialog.json_filter")
        )
        if not path:
            return
        try:
            spec = load_experiment(path)
            self._ensure_plugin_for_spec(spec)
            self._refresh_plugin_models()
            self._clear_current_result()
            self.parameter_panel.load_spec(spec)
            self.current_spec = spec
            self.baseline_spec = spec
            self.statusBar().showMessage(self.tr_key("message.loaded").format(name=spec.name), 8000)
            LOGGER.info("Loaded experiment file %s", Path(path).name)
        except Exception as exc:
            QMessageBox.critical(self, self.tr_key("message.validation"), str(exc))
            LOGGER.exception("Failed to load experiment")

    def save_experiment(self) -> None:
        try:
            spec = self.parameter_panel.to_spec()
        except Exception as exc:
            QMessageBox.warning(self, self.tr_key("message.validation"), str(exc))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr_key("dialog.save_title"), "experiment.json", self.tr_key("dialog.json_filter")
        )
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")
        target.write_text(spec.model_dump_json(indent=2) + "\n", encoding="utf-8")
        self.current_spec = spec
        self.baseline_spec = spec
        self.statusBar().showMessage(
            self.tr_key("message.saved").format(path=str(target)), 8000
        )
        LOGGER.info("Saved experiment file %s", target.name)

    def export_json(self) -> None:
        if self.current_trajectory is None or self.current_spec is None:
            QMessageBox.information(self, self.tr_key("menu.file"), self.tr_key("message.no_result"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr_key("dialog.export_json_title"), "trajectory_result.json", self.tr_key("dialog.json_filter")
        )
        if not path:
            return
        target = Path(path).with_suffix(".json")
        export_result_json(target, self.current_spec, self.current_trajectory)
        self.statusBar().showMessage(self.tr_key("message.exported").format(path=str(target)), 8000)
        LOGGER.info("Exported JSON result as %s", target.name)

    def export_csv(self) -> None:
        if self.current_trajectory is None:
            QMessageBox.information(self, self.tr_key("menu.file"), self.tr_key("message.no_result"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr_key("dialog.export_csv_title"), "trajectory_result.csv", self.tr_key("dialog.csv_filter")
        )
        if not path:
            return
        target = Path(path).with_suffix(".csv")
        export_trajectory_csv(target, self.current_trajectory)
        self.statusBar().showMessage(self.tr_key("message.exported").format(path=str(target)), 8000)
        LOGGER.info("Exported CSV trajectory as %s", target.name)

    def _refresh_plugin_models(self) -> None:
        self.model_registry.reload()
        self.parameter_panel.set_plugin_models([
            (record.model_id, f"{record.name} v{record.version}")
            for record in self.model_registry.records
        ])
        for path, error in self.model_registry.errors:
            LOGGER.error("Could not load user model %s: %s", Path(path).name, error)

    def _ensure_plugin_for_spec(self, spec: ExperimentSpec) -> None:
        model_id = spec.drag.model
        if not model_id.startswith("plugin:"):
            return
        try:
            self.model_registry.get(model_id)
            return
        except Exception:
            pass
        answer = QMessageBox.warning(
            self,
            self.tr_key("models.security_title"),
            self.tr_key("models.required_plugin_warning").format(model=model_id),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            raise ValueError(f"Required user model {model_id!r} has not been loaded")
        self.model_registry.reload(load_python=True)
        self._refresh_plugin_models()
        self.model_registry.get(model_id)

    def manage_models(self) -> None:
        dialog = ModelManagerDialog(self.tr_key, self.model_registry, self)
        dialog.exec()
        self._refresh_plugin_models()

    def export_pdf(self) -> None:
        if self.current_trajectory is None or self.current_spec is None:
            QMessageBox.information(self, self.tr_key("menu.file"), self.tr_key("message.no_result"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr_key("dialog.export_pdf_title"), "trajectory_report.pdf", self.tr_key("dialog.pdf_filter")
        )
        if not path:
            return
        language_labels = [
            self.tr_key("dialog.pdf_language_ru"),
            self.tr_key("dialog.pdf_language_en"),
            self.tr_key("dialog.pdf_language_bilingual"),
        ]
        selected, accepted = QInputDialog.getItem(
            self, self.tr_key("dialog.pdf_language_title"),
            self.tr_key("dialog.pdf_language_prompt"), language_labels, 0, False,
        )
        if not accepted:
            return
        language = {language_labels[0]: "ru", language_labels[1]: "en", language_labels[2]: "both"}[selected]
        try:
            target = export_pdf_report(path, self.current_spec, self.current_trajectory, language=language)
            self.statusBar().showMessage(self.tr_key("message.exported").format(path=str(target)), 8000)
            LOGGER.info("Exported PDF report as %s", target.name)
        except Exception as exc:
            QMessageBox.critical(self, self.tr_key("models.error"), str(exc))
            LOGGER.exception("PDF report export failed")

    def open_manual(self, language: str) -> None:
        manual = resource_path(f"trajectory_lab/ui/resources/manuals/TrajectoryLab_Manual_{language.upper()}.pdf")
        if not manual.is_file():
            QMessageBox.warning(self, self.tr_key("action.about"), self.tr_key("help.manual_missing"))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(manual)))

    def show_about(self) -> None:
        """Show project information; the cow is revealed after nine signature clicks."""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr_key("action.about"))
        dialog.setModal(True)
        dialog.setFixedWidth(560)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(14, 14, 14, 10)
        layout.setSpacing(7)

        title = QLabel(f"TrajectoryLab {__version__}")
        title.setStyleSheet("font-size: 11pt; font-weight: 600;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        brand_logo = QLabel()
        brand_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = resource_path("trajectory_lab/ui/resources/trajectorylab_logo.png")
        logo_pixmap = QPixmap(str(logo_path))
        if not logo_pixmap.isNull():
            brand_logo.setPixmap(logo_pixmap.scaled(
                235, 250, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            layout.addWidget(brand_logo)

        product = QLabel(self.tr_key("about.product"))
        product.setWordWrap(True)
        product.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(product)

        details = QLabel(self.tr_key("about.details"))
        details.setWordWrap(True)
        details.setAlignment(Qt.AlignmentFlag.AlignLeft)
        details.setStyleSheet(
            "QLabel { color: palette(text); padding: 7px 5px; "
            "font-size: 8pt; line-height: 125%; }"
        )
        layout.addWidget(details)

        project_line = QLabel(self.tr_key("about.project_line"))
        project_line.setWordWrap(True)
        project_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        project_line.setStyleSheet("QLabel { color: #56616a; font-size: 8pt; }")
        layout.addWidget(project_line)

        signature = QPushButton(self.tr_key("about.signature"))
        signature.setFlat(True)
        signature.setCursor(Qt.CursorShape.PointingHandCursor)
        signature.setToolTip("")
        signature.setStyleSheet(
            "QPushButton { border: 0; background: transparent; padding: 3px; "
            "font-family: Consolas, monospace; font-size: 10pt; font-weight: 600; color: #466f8e; } "
            "QPushButton:hover { color: #284c68; text-decoration: underline; }"
        )
        layout.addWidget(signature)

        image = QLabel()
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.hide()
        layout.addWidget(image)
        caption = QLabel(self.tr_key("about.cow_caption"))
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption.hide()
        layout.addWidget(caption)

        click_state = {"count": 0, "revealed": False}

        def reveal_cow() -> None:
            if click_state["revealed"]:
                return
            click_state["count"] += 1
            if click_state["count"] < 9:
                return
            click_state["revealed"] = True
            cow_path = resource_path("trajectory_lab/ui/resources/cow.png")
            pixmap = QPixmap(str(cow_path))
            if not pixmap.isNull():
                image.setPixmap(pixmap.scaled(
                    480, 240, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
                image.show()
                caption.show()
                dialog.adjustSize()

        signature.clicked.connect(reveal_cow)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        self.settings.setValue("window/width", self.width())
        self.settings.setValue("window/height", self.height())
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("language", self.language)
        self.settings.setValue("theme", self.theme)
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(5000):
                event.ignore()
                self.statusBar().showMessage(self.tr_key("status.running"), 5000)
                return
        if self._qt_log_handler is not None:
            LOGGER.removeHandler(self._qt_log_handler)
            self._qt_log_handler.close()
            self._qt_log_handler = None
        super().closeEvent(event)
