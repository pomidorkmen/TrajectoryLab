"""PyInstaller entry point for the windowed desktop application."""
from __future__ import annotations
import sys
from trajectory_lab.ui.app import run_gui, run_ui_smoke_test

if __name__ == "__main__":
    if sys.argv[1:] == ["--ui-smoke-test"]:
        raise SystemExit(run_ui_smoke_test())
    raise SystemExit(run_gui())
