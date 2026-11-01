# TrajectoryLab 0.4.2 — source security and privacy review

Review date: 2026-10-31  
Scope: first-party Python runtime, Builder, Windows bootstrapper, user-model registry, serialization/export paths, bundled assets and source archive.

## Summary

The current source scan found no known high-confidence API token patterns, private-key files, `.env` files, or hard-coded personal identifiers in the source tree. The first-party desktop runtime contains no imported HTTP, socket, email or telemetry client. No experiment-upload or analytics endpoint is implemented in the first-party runtime.

This is a static, scoped review. It is not an independent malware certification, penetration test, audit of all transitive dependencies, or proof that no data can ever leave the computer.

## What can leave the computer

1. **Builder first run:** the native bootstrapper downloads the pinned official Python installer from `python.org`. The download is checked against a hard-coded SHA-256 before execution. Ordinary network metadata (including source IP and request headers) is visible to the server as with any HTTPS request.
2. **Dependency installation:** Builder invokes `pip install` and `pip check`; pip contacts the configured Python package index (normally PyPI) to download the declared dependencies. Package names and versions are part of this request metadata. No TrajectoryLab experiment is intentionally attached to those requests.
3. **Python plugins:** user plugins are arbitrary Python programs loaded in-process. They may read or modify accessible files, create processes, and make network requests. The plugin interface is not a sandbox.
4. **Third-party libraries:** the review did not independently prove the runtime behaviour of every transitive dependency. The statement about no first-party runtime HTTP client does not cover arbitrary library vulnerabilities or future dependency changes.

## Local storage

- Main application settings are managed by Qt `QSettings` in the current user's application settings store.
- Application logs and user drag models are normally stored under `%USERPROFILE%\\.trajectory_lab`.
- Builder runtime and diagnostics are stored below `%LOCALAPPDATA%\\TrajectoryLabBuilder`.
- Experiment JSON, result JSON, CSV and PDF files are written to the path selected by the user.
- The application archive does not intentionally include the user's `.trajectory_lab` folder, experiment files, or Builder cache.

## Personal-data handling

- Main application logs redact known home/Profile/AppData roots. This is a convenience filter and not a general PII scrubber.
- Builder journals redact known local roots before displaying messages. Bootstrap diagnostics are also written with known roots redacted. A Python startup crash log may still contain source filenames/line paths; inspect it before sharing.
- Result provenance records software versions, platform description, model metadata, numeric parameters and trajectory/model SHA-256 hashes. These fields can reveal experiment details or OS information but are not designed to include the Windows account name or absolute user file path.
- User-provided model metadata may contain the author's name or source URL; review it before sharing result JSON/PDF.
- Never publish `%USERPROFILE%\\.trajectory_lab` wholesale. Review experiment exports and logs for confidential measurements, filenames, institution names and device identifiers.

## Findings and limitations

| Area | Result |
|---|---|
| Known token/private-key patterns | No findings in the source scan |
| `.env` / credential files | None found in the release tree |
| First-party runtime network client | None found by import/source scan |
| Builder network activity | python.org + pip package index on first setup |
| Python plugins | Arbitrary in-process code; no sandbox |
| JSON/CSV models | Parsed as declarative data, no Python execution |
| Log redaction | Known local path roots only; not universal PII sanitization |
| Dependency hashes | Not fully pinned in a hash-locked dependency manifest |
| Binary signing | Authenticode signature is not configured |
| Git history | A new empty local Git repository is prepared for the first owner-authored commit; no previous user Git history is included or audited |

## Verification performed

- `build.security_scan()` returned no findings after adding SVG/XML to the scanned text suffixes.
- Privacy tests cover known local-path redaction and absence of first-party network client imports in `trajectory_lab`.
- Builder and Win32 bootstrapper source were inspected for download, logging, path and process behaviour.
- 99 available tests passed. There are 110 test functions in the source tree; 11 tests in the two Pint-dependent modules could not be collected in this environment because Pint is not installed. PySide6/pyqtgraph are also unavailable here, so a live Qt run and the Windows EXE were not executed in this environment.
- The two PDF manuals were generated, rendered to page images and inspected; each has 35 pages.

## Recommendations before public stable release

1. Run the full test suite on a clean Windows 10/11 x64 environment with Pint, PySide6 and pyqtgraph installed by Builder.
2. Review dependency licenses and run a dependency vulnerability scan against the exact build lock.
3. Create a fully hash-locked dependency set for reproducible packaging.
4. Consider Authenticode signing for the Windows Builder and application.
5. Audit the full Git history locally before pushing to a public remote; the source archive cannot prove past commits were secret-free.
6. Obtain an independent review of the Windows bootstrapper and packaged PyInstaller binary.
