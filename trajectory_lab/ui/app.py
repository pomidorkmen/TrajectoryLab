"""Desktop application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from trajectory_lab.ui.main_window import MainWindow


def _configure_application(arguments: list[str] | None = None) -> QApplication:
    application = QApplication(arguments if arguments is not None else sys.argv)
    application.setApplicationName("TrajectoryLab")
    application.setOrganizationName("TrajectoryLab")
    application.setStyle("Fusion")
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    icon_path = bundle_root / "trajectory_lab" / "ui" / "resources" / "trajectorylab.png"
    if icon_path.is_file():
        application.setWindowIcon(QIcon(str(icon_path)))
    return application


def run_gui(argv: list[str] | None = None) -> int:
    """Start the TrajectoryLab Qt desktop application."""
    application = _configure_application(argv)
    window = MainWindow(application)
    window.show()
    QTimer.singleShot(200, window.run_simulation)
    return application.exec()


def run_ui_smoke_test() -> int:
    """Construct and show the main window once, then exit without an event loop."""
    application = _configure_application(["TrajectoryLab", "--ui-smoke-test"])
    window = MainWindow(application)
    window.show()
    application.processEvents()
    window.close()
    application.processEvents()
    return 0
