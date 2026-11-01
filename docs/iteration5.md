# TrajectoryLab 0.4.1 — Builder usability release

- Reworked the Python Builder into one compact light scientific window.
- Added small UK and Russian flag controls for live RU/EN localization.
- Removed modal message boxes and the separate theme-picker window; theme selection is embedded in the Builder window after a successful build.
- Builder typography uses Segoe UI for controls and Consolas for numerical/build details, matching the desktop application's restrained technical style.
- Application default theme is Light. Dark and Soft Pink remain selectable for the built application.
- The About dialog reveals the original cow only after nine clicks on `pomidorkmen`.
- The native bootstrapper closes itself only after the main Builder window signals readiness; failures remain visible in the bootstrap journal.
- Bootstrap window uses a neutral light/system palette and the v0.4.1 label.

## Validation note

Python syntax, resource catalogs, Builder source contracts, Go formatting and Windows cross-compilation are checked in the build environment. The current execution environment is Linux and does not provide Win32 GUI execution, Pint or PySide6; final Windows Builder and application smoke tests must be performed on Windows 10/11.
