# Security and privacy policy

TrajectoryLab is designed as a local scientific desktop application. This document describes the first-party application behaviour and the security boundaries of user extensions.

## Data handling

- Experiment input and result files are read from and written to locations chosen by the user.
- Application settings, logs and user drag models are stored under the current user's `.trajectory_lab` directory (typically `%USERPROFILE%\\.trajectory_lab` on Windows).
- The first-party desktop runtime has no telemetry uploader or built-in HTTP client for sending experiments to a server.
- The Builder makes network requests during initial setup: it downloads a pinned Python installer from `python.org` and installs packages from PyPI using `pip`. The installer is checked against a pinned SHA-256 before execution. Network providers can still observe ordinary connection metadata such as IP address and request headers.
- Python plugins run as ordinary Python code with the current user's permissions. They can read or modify accessible files, start child processes and use the network. The application does not sandbox them.
- JSON/CSV drag tables are parsed as data and are preferred when a model can be represented declaratively.

## Local data and sharing

Do not publish `%USERPROFILE%\\.trajectory_lab` wholesale. It may contain private experiment files, user models and logs. Before sharing a PDF, JSON, CSV or log, inspect it for personal paths, project names, instrument identifiers and confidential measurements. The log filter redacts known local path roots, but it is not a universal PII scrubber.

## Safe use

1. Keep Windows Defender and SmartScreen enabled.
2. Run TrajectoryLab as a standard user, not as Administrator.
3. Load Python plugins only after reviewing the complete source and trusting its author.
4. Prefer JSON/CSV models when possible.
5. Verify release SHA-256 values and obtain releases from the intended project page.
6. Do not bypass a malware detection. An unknown-publisher SmartScreen warning and a malware detection are different events; investigate each warning before proceeding.

## Reporting

For a security concern, prepare a minimal reproduction and redact any personal paths, private experiment data and credentials. Do not attach the entire user data directory. Report issues through the project maintainer's published contact channel once one has been established.

## Scope and limitations

This is a project security policy, not a certification or a claim that the application is free of vulnerabilities. The dependency tree, PyInstaller output, Windows bootstrapper and operating system are separate attack surfaces. Dependencies are installed from PyPI; a complete hash-locked dependency file, signed binaries and an independent third-party security audit remain separate release-hardening tasks.
