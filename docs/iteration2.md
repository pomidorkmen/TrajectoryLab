# TrajectoryLab 0.2.0 — Iteration 2

## Delivered

Iteration 2 adds a PySide6 desktop application over the existing SI-only
numerical core. The core modules do not import Qt. The UI validates editor
values through the existing Pydantic + Pint `ExperimentSpec` boundary and runs
`simulate()` on a worker thread.

The main window uses `QMainWindow`, a menu bar, toolbar, status bar and three
`QDockWidget` panels: experiment parameters, key results and journal. The center
contains 2D trajectory, OpenGL 3D, speed/Mach/energy time-series, and sampled
trajectory-table tabs. The results panel reports displacement, elapsed time,
ground-event time, maximum height, speed, Mach, Reynolds, energy and checksum.

English and Russian are switched at runtime using a JSON-backed `QTranslator`.
The message catalogs have matching keys. Light and dark styles are external QSS
files. Language, theme, window size and dock layout are saved using `QSettings`.
The file logger writes to `~/.trajectory_lab/logs/trajectory_lab.log`; a Qt
signal forwards log records to the journal dock.

The UI opens the included `examples/air_resistance_drop.json` and starts a
small demonstration calculation. JSON experiment files can be opened/saved;
completed trajectories can be exported to JSON and CSV. The CLI remains
available by passing a CLI command, for example `python -m trajectory_lab run
examples/vacuum_reference.json`.

## Build and launch

- Source GUI: `python -m trajectory_lab`
- CLI help: `python -m trajectory_lab --help`
- Standalone build: `python build.py`

The build script installs missing dependencies into its local `.venv`, runs
pytest, builds an onedir PyInstaller application and performs CLI and offscreen
Qt-window smoke tests. `--onefile`, `--clean` and `--skip-tests` remain optional.

## Boundaries of this iteration

The drag selector exposes built-in low-speed sphere models and the configured
tabular model. The UI does not yet include a full interactive tabular-data
editor or an external Python-plugin manager; those are iteration 3 items.
OpenGL 3D view is optional at runtime. If the GL stack is unavailable, the
other views and numerical workflow remain usable.

## Verification notes

Static compilation, translation/resource checks, and the dependency-independent
regression subset passed in the development container. The development
container did not have Pint, PySide6 or pyqtgraph installed and network package
installation was unavailable, so it was not possible there to launch the real
Qt window or build a frozen binary. The root `build.py` now includes an
on-machine offscreen UI smoke test; a successful Windows build is the final
runtime acceptance check.
