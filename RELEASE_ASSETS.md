# Prepared release assets — TrajectoryLab 0.4.2 Public Preview

The GitHub repository contains source code and documentation. Attach the
following files to the GitHub Release tagged `v0.4.2-preview`:

- `TrajectoryLab_Windows_Builder_Package.zip` — complete Windows x64 package,
  including the GUI bootstrapper and project files.
- `TrajectoryLab_RELEASE_SHA256SUMS.txt` — SHA-256 checksums for the source
  archive and the Windows Builder package.

The builder executable is not committed to the source repository. The source
for it is `tools/builder/main_windows.go`.

The source code is licensed under MIT; artwork and third-party dependencies remain separately licensed. This is a public preview, not a stable 1.0.0 release. A clean Windows 10/11
acceptance run and the Pint-dependent tests remain outstanding.
