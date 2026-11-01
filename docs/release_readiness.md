# TrajectoryLab 0.4.2 — release-readiness report

## Release scope

This is release-candidate preparation for the existing 0.4.2 code line. MeteoLab is a separate project and is out of scope. The stable 1.0.0 label should only be applied after a clean Windows 10/11 acceptance run and review of package provenance/signing requirements.

## Simulation time semantics

- `duration_s` is the maximum requested simulation time, not a mandatory stopping time when a terminal event is enabled.
- `stop_at_ground=True` stops on the first descending crossing of `y = 0`.
- `stop_at_ground=False` continues to the configured maximum duration, including below ground if the model is intentionally used that way.
- RK4 localizes the event within the current RK4 output interval; DOP853 uses the SciPy event locator and returns the event state.
- A final partial step is inserted when `duration_s` is not an integer multiple of `step_s`.
- The interpolated apogee is calculated from the sampled position and vertical-velocity values, so the maximum is not restricted to saved sample timestamps.

## Manuals and About window

- `TrajectoryLab_Manual_RU.pdf`: 35 pages.
- `TrajectoryLab_Manual_EN.pdf`: 35 pages.
- Each manual has a cover, contents and 33 interface/workflow chapters.
- The About dialog describes physical scope, technology, local data, network behaviour and Python plugin risk. Nine clicks on `pomidorkmen` reveal the cow easter egg.

## Privacy/security review

- No first-party runtime HTTP client or telemetry uploader was found by static import/source review.
- Builder contacts python.org to retrieve the pinned Python installer and PyPI through pip to install dependencies on first setup.
- Python plugins are arbitrary code running in-process with the current user's permissions; no sandbox is provided.
- User state is stored under the user's `.trajectory_lab` directory. This directory is not part of the source release archive.
- Log path redaction handles known home/AppData roots but is not a general personal-data scrubber.
- The source secret scan checks selected token patterns and private-key-like files only; it does not inspect prior Git history, all binary formats, or every possible credential format.
- The application/Builder binaries are not Authenticode-signed in this candidate. SmartScreen unknown-publisher warnings may occur.

## Verification boundaries

Local source-level checks, selected numerical tests, resource tests and PDF rendering were run in the build environment. Pint and PySide6 are not installed in that environment, so the full unit-boundary and GUI runtime test suite could not be run there. A final Windows acceptance run must verify: Builder first-run bootstrap, all tests with real Pint, PyInstaller build, GUI startup, theme/language changes, PDF export, user model handling, Desktop shortcut creation and uninstallation/update behaviour.


## Public repository status

- The project owner selected MIT for original TrajectoryLab source code and
  project-authored documentation. Artwork and third-party components are
  explicitly excluded; see `LICENSE_SCOPE.md` and `LICENSE_STATUS.md`.
- The supplied Recraft-generated wordmark and cow photograph are retained in
  the application at the owner's request, but are not covered by MIT. Public
  redistribution must wait until the owner confirms the generation plan and
  applicable Recraft terms for the logo, and the redistribution rights for
  the photograph. See `ASSET_RIGHTS.md`.
- The source repository is separate from the Windows binary release package.
