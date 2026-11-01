> Historical review for versions 0.3.1–0.4.1. For the current 0.4.2 security/privacy scope and verification limitations, see [`security_audit_0_4_2.md`](security_audit_0_4_2.md), [`release_readiness.md`](release_readiness.md), and the repository-level [`SECURITY.md`](../SECURITY.md).

# TrajectoryLab 0.3.1 — security review

Review date: 2026-10-31  
Scope: application source, plugin registry, CLI policy, build script, JSON/CSV/PDF I/O, and the delivered source archive.

## Summary

No obvious malware, hidden telemetry, credential collection, remote-control logic, or application-level outbound network client was found in the reviewed source files. This is a static source review, not a formal penetration test, malware certification, or audit of every transitive dependency.

**The project must not be described as fully secure.** Python plugins are intentionally executable code and run with the current user's Windows permissions. Only load Python plugins that you authored or have reviewed and trust.

## Findings and changes in 0.3.1

### Fixed: CLI loaded Python plugins without an explicit opt-in

Version 0.3.0 called `registry.reload(load_python=True)` for both CLI `run` and `verify`. This executed eligible `.py` files from the user's model directory even when the selected experiment used a built-in drag model.

Version 0.3.1 changes the default:

- CLI loads JSON table models as data.
- CLI does not execute `.py` plugin files by default.
- `run` and `verify` expose `--allow-python-plugins` as explicit opt-in.
- If the selected plugin is unavailable and Python files are pending, the CLI explains the opt-in requirement.
- The flag executes every eligible Python plugin in the user model folder, not only the file matching the selected model ID. Review the entire folder before using it.

Regression test: `tests/test_cli_security.py::test_cli_registry_does_not_execute_python_plugins_by_default` uses a marker file and verifies that the marker is not created without opt-in. The companion test verifies the explicit opt-in error.

### Hardened: plugin import path lifetime

The plugin directory is added temporarily to `sys.path` while a plugin module is imported, then removed in a `finally` block. This reduces the chance that files in the model folder shadow unrelated application or standard-library modules after plugin loading.

Regression test: `test_python_plugin_directory_is_removed_from_sys_path_after_load`.

## Current security boundaries

| Area | Assessment |
|---|---|
| GUI plugin loading | Confirmation is shown before executing Python plugin code. Plugins still run in-process with full current-user permissions. |
| CLI plugin loading | Disabled by default; explicit `--allow-python-plugins` required. |
| JSON table models | Parsed as declarative data; no Python execution. Input sizes are not currently capped, so avoid untrusted, extremely large files. |
| Experiment JSON | Parsed with Python's JSON parser and validated with Pydantic; no pickle or dynamic evaluation is used. |
| PDF report | ReportLab-generated; user/model strings are XML-escaped before being inserted into Paragraph/table content. |
| Build script | Creates a local `.venv`, installs packages with pip, executes pytest and PyInstaller. It does not request administrator privileges. Only run it from a source archive you trust. |
| Dependency supply chain | `pyproject.toml` uses version ranges, not a fully hash-locked dependency file. First build contacts the configured package index through pip. Transitive dependencies were not independently audited. |
| Runtime network behavior | No application-level HTTP, socket, requests, or urllib client was found in the reviewed first-party runtime source. This does not make a claim about the behavior of all third-party libraries. |
| Windows executable | No Authenticode code signature is configured. Windows SmartScreen may show an unknown-publisher warning. Do not bypass antivirus/Defender alerts. |

## Safe operating guidance

1. Use JSON table models when possible; they do not execute code.
2. Do not import or load Python plugins received from unknown people or websites.
3. Before enabling Python plugins, inspect every `.py` file in `%USERPROFILE%\\.trajectory_lab\\models` because the opt-in loads all eligible files in that folder.
4. Do not run `build.py` from an archive whose origin or contents you do not trust; the build installs dependencies and executes project tests/build hooks.
5. Keep Windows Defender and other endpoint protection enabled. Do not run TrajectoryLab as Administrator.
6. For a stronger supply-chain guarantee, the next hardening step is a hash-locked dependency file, verified package hashes, signed release artifacts, and an independent review of the pinned third-party dependencies.

## Verification performed for this review

- Python source compiled with `compileall`.
- Security-focused tests and core/plugin regression subset: 58 passed in this environment.
- Source search for common dynamic execution, serialization, subprocess, and network APIs.
- ZIP integrity check passed; archive paths contained no absolute paths or `..` traversal entries.

Limitations: Pint, PySide6, pyqtgraph, and PyInstaller were unavailable in the review environment. The complete GUI/runtime test suite and Windows executable were not re-run here. The security assessment therefore applies to the inspected source and the narrow test subset only.


## Version 0.4.1 Builder and release notes

- `build.exe` is a Windows x64 GUI bootstrapper. On first use it downloads a pinned official Python 3.14.10 Windows x64 installer from python.org and checks its SHA-256 before executing it. Cached installers are checked again before reuse.
- The bootstrapper installs Python for the current user under `%LOCALAPPDATA%`; it does not request elevation or modify the system PATH.
- The graphical `build.py` installs Python packages into a private virtual environment. This first build requires internet access. PyPI dependencies are currently version-ranged in `pyproject.toml`; a complete hash-locked requirements set and package provenance verification remain future hardening tasks.
- Before PyInstaller packaging, Builder scans source text for selected API-token patterns and private-key-like files. This scan is intended to prevent common accidental leaks; it is not a complete secret scanner, static analyzer or malware detector.
- The desktop shortcut is created in the Windows Desktop Known Folder and is checked to ensure it targets the newly built executable.
- The Windows bootstrapper and application are not code-signed in this source release. Windows SmartScreen may show an unknown-publisher warning. Do not disable Defender or SmartScreen to run an untrusted build.
- The app itself does not implement telemetry or upload experiment data. The first-run Builder contacts python.org and pip contacts PyPI to obtain the runtime and dependencies.
