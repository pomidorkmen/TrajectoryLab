# TrajectoryLab 0.3.1 — Iteration 3

Iteration 3 closes the user drag-model workflow and report output.

## Desktop workflow

1. Open **Experiment → Drag model manager**.
2. Use **Create table** to define a `Cd(Re)` model, or import an existing JSON
   table / CSV file. CSV accepts `Re` or `Reynolds` and `Cd` headers, or two
   numeric columns ordered as Re, Cd.
3. Python extensions can be imported separately. Use **Load Python** only after
   reviewing the execution warning and trusting the code.
4. Close the manager. The user model appears in the drag model selector in the
   experiment parameter panel.
5. Run the experiment and export its result JSON/CSV or a PDF report.

## Model identity and reproducibility

User model IDs are serialized as `plugin:<id>`. Each imported file receives a
SHA-256 over its original bytes. That source hash is added to the model
fingerprint and provenance. The model's own name, version, author, source,
geometry and Reynolds validity interval are kept alongside the hash.

Table validity bounds are checked against the first and last Re nodes. Table
interpolation can be linear, log-log or cubic log-log; extrapolation policy is
explicit (`error`, `clamp`, `extrapolate`). Python model metadata is validated
and a representative in-range call is performed before registration. Python
plugin coefficients must satisfy finite `0 < Cd < 100`.

## PDF report

The report includes experiment inputs with units, atmosphere, drag-model
metadata and hashes, numerical method and tolerances, seed, Python/NumPy/SciPy/
Pint/platform provenance, result summary, trajectory checksum, warnings, and
vector plots of height/time and speed/time.

## Windows integration

The selected TrajectoryLab application icon is included in the Windows EXE.
After a successful Windows build, the build script attempts to create
`%USERPROFILE%\\Desktop\\TrajectoryLab.lnk` through the Windows Shell COM API.
No additional Python package is required for the shortcut. If the Desktop
folder is redirected or unavailable, the builder reports that it skipped the
shortcut; the executable remains in `dist/`.

## Security boundary

JSON table models are parsed as data. Python plugins are ordinary executable
code in the application process. They are not sandboxed and can access files,
network and other resources available to the current user. The application
requires explicit confirmation before loading Python plugins. Never load an
untrusted extension.
