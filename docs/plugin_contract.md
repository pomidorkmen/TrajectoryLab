# TrajectoryLab user drag models

TrajectoryLab 0.3.1 loads user models from `~/.trajectory_lab/models/`.
The directory is created automatically by the desktop application.

## Declarative table models

JSON table files are data-only and are loaded without executing Python. Example:
`models_examples/tabular_cd.json`.

Required fields:

- `schema_version`: currently `1.0`;
- `kind`: `tabular_drag`;
- `id`, `name`, `version`, `author`, `source`, `geometry`;
- `validity.reynolds_min` and `validity.reynolds_max` (use `null` for no upper bound);
- `interpolation`: `linear`, `log-log`, or `cubic-log-log`;
- `extrapolation`: `error` (default), `clamp`, or `extrapolate`;
- `points`: strictly increasing objects with positive `reynolds` and `cd`.

The lower and upper validity boundaries must match the first and last table nodes.
The interpolation and extrapolation policy are stored in the model metadata and in
experiment provenance. CSV import accepts `Re`/`Reynolds` and `Cd` headers, or two
numeric columns in that order. The editor validates and saves CSV data as JSON.

## Python extensions

A Python extension must subclass `trajectory_lab.core.drag.base.BaseDragModel` and
provide `cd(self, state: FlowState) -> float` and `describe(self) -> dict`.
It may expose one `MODEL_CLASS` class, a `create_model()` factory, or exactly one
`BaseDragModel` subclass. The instance must be constructible without arguments.

Example:

```python
from trajectory_lab.core.drag.base import BaseDragModel
from trajectory_lab.core.state import FlowState

class ExampleDrag(BaseDragModel):
    def cd(self, state: FlowState) -> float:
        return 0.44

    def describe(self) -> dict[str, object]:
        return {
            "id": "research.example_drag",
            "name": "Research example",
            "version": "1.0.0",
            "author": "Researcher",
            "source": "https://example.invalid/method",
            "geometry": "sphere",
            "validity": {
                "reynolds_min": 1.0,
                "reynolds_max": 10000.0,
            },
        }
```

A plugin must return finite `0 < Cd < 100`. During registration, TrajectoryLab
checks metadata and performs a small test call at an in-range `FlowState`. Model
applicability is subsequently checked during simulation; out-of-range use produces
an applicability warning that is recorded with the trajectory.

The registry computes SHA-256 over the original plugin file. The source hash and
model metadata are included in the model fingerprint, simulation provenance and
PDF report. Changing the plugin source therefore changes its model fingerprint.

## Security

Python extensions are arbitrary executable code. They run in the TrajectoryLab
process with the current user's permissions. There is no sandbox, subprocess
isolation or permission boundary. The manager displays this warning and asks for
confirmation before loading Python extensions. Only install code from sources you
trust. Declarative JSON tables do not execute code.

## Reproducibility

A saved experiment stores the selected ID as `plugin:<id>`. To repeat an experiment
on another computer, copy the referenced plugin/table file into that computer's
`~/.trajectory_lab/models/` directory. The report stores the model metadata, model
SHA-256, trajectory checksum, solver settings, seed, and package/runtime versions.


### CLI execution policy

The CLI loads JSON table files as data and does not execute Python plugins by default.
For `run` or `verify`, the user must pass `--allow-python-plugins`. This is an explicit
opt-in that executes every eligible `.py` file in the user model directory, not only
the plugin referenced by the experiment. Review the entire directory before using it.


The loader temporarily adds the plugin folder to `sys.path` while importing a module,
then removes it to avoid leaving the user model folder as a persistent module search path.
