# Changelog

## 0.4.2 — public preview preparation

- Selected MIT for original TrajectoryLab source code and authored documentation; artwork and third-party components remain separately licensed.
- Added an explicit license-scope statement and asset provenance/redistribution notes.

- Clarified maximum simulation time and optional ground-stop behaviour for RK4 and DOP853.
- RK4 and DOP853 now share the same first descending `y = 0` event policy; RK4 localizes the event inside the final step and DOP853 uses SciPy event localization.
- The final integration interval is shortened automatically when the configured output step does not divide the maximum duration.
- Maximum height and apogee time are interpolated between output samples using cubic Hermite segments.
- Added detailed Russian and English user manuals (35 pages each) with workflow-focused UI chapters.
- Expanded About information with scientific scope, technology stack, local data storage and explicit network/plugin security notes.
- Added a project-level security and privacy policy.

## Earlier versions

See `docs/` for historical iteration notes and security review details. Older notes describe the version at the time they were written and should not be treated as the current release specification.
