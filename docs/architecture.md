# TrajectoryLab architecture

## Dependency direction

`ui -> io -> core` is the intended direction. The physics modules never import
Qt, pyqtgraph or UI resources. `core` accepts validated SI floats and returns
NumPy arrays. Pydantic schemas convert unit-tagged input to SI through Pint at
the boundary.

## Desktop application (iteration 2)

- `trajectory_lab.ui.app` creates `QApplication` and the main window.
- `trajectory_lab.ui.main_window` owns the menus, toolbar, dock widgets,
  settings, logging and background simulation worker.
- `trajectory_lab.ui.widgets.parameter_panel` translates form values into a
  Pydantic `ExperimentSpec`; `to_core_config()` performs Pint conversion.
- `trajectory_lab.ui.widgets.trajectory_plots` draws 2D, OpenGL 3D and
  time-series views using pyqtgraph.
- `trajectory_lab.ui.models.trajectory_table` exposes sampled values through
  `QAbstractTableModel`.
- `trajectory_lab.ui.i18n` contains JSON message catalogs used by a
  `QTranslator` subclass. `retranslate_ui()` updates all visible labels when
  the language changes.
- `trajectory_lab.ui.resources.themes` contains the QSS light and dark themes.

The simulation executes in a `QThread`; the core is called by a worker object
and returns immutable metadata plus NumPy trajectory arrays through Qt signals.

## Packaging

The single root `build.py` installs dependencies in a local virtual environment,
executes tests, invokes PyInstaller, runs the frozen CLI help test and creates
the Qt window with the offscreen platform as a GUI smoke test. UI catalogs, QSS
files, examples and model examples are added as data resources.
The default PyInstaller layout is `onedir`; `--onefile` is optional.
