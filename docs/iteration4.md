# TrajectoryLab 0.4.1 — release notes

## Included

- Soft Pink QSS theme, using pastel pink as a restrained accent while retaining the compact scientific UI layout.
- About dialog with the `pomidorkmen` signature; the original cow is revealed after nine clicks.
- PDF report language selection: Russian, English or bilingual.
- Bundled Russian and English user manuals under Help.
- Graphical Tk Builder (`build.py`) with progress, build journal, test selection, clean/onefile options and post-build theme selection.
- Standalone Windows x64 `build.exe` bootstrapper. It downloads the official Python 3.14.10 installer from python.org, verifies its pinned SHA-256, performs a per-user installation under `%LOCALAPPDATA%`, and opens the graphical Builder without requiring an existing Python installation or administrator privileges.
- Desktop shortcut creation through the Windows Known Folder API and ShellLink COM, with target verification.
- Source-tree secret-pattern scan before packaging.
- Reproducible ZIP distribution metadata.

## Style decisions

The application remains a strict scientific desktop utility in the visual tradition of late-2000s / early-2010s engineering software: dense panels, gray neutral surfaces, thin borders, fixed-precision monospaced values and no gradients, shadows, decorative cards or animations. The Soft Pink theme only changes selected accents and surface tones.

## Security notes

- The first-run bootstrapper downloads only from the official python.org URL compiled into the bootstrapper. It verifies the installer against the published SHA-256 before execution and verifies cached installers again.
- Python is installed only into the current user's local application-data directory. No system PATH modification or administrator privileges are requested.
- The Builder uses pip from the private virtual environment to install project dependencies. This requires an internet connection on first build.
- The source scan detects several high-confidence token formats and private-key-like files. It is a safeguard against accidental commits, not a complete secret scanner or malware scanner.
- Python drag plugins remain arbitrary executable code and are not sandboxed. The CLI does not load them by default; the UI requires explicit confirmation.
- No telemetry or application-managed data upload is implemented.

## Builder bootstrap hotfix

The initial Windows bootstrapper passed the IDC_ARROW resource identifier (32512)
directly as an HCURSOR in WNDCLASSEX. Windows requires a real cursor handle.
The bootstrapper now resolves IDC_ARROW using LoadCursorW and passes the returned
HCURSOR to RegisterClassExW. A source regression test guards against reintroducing
the invalid resource-ID-as-handle assignment. The Go source cross-compiles for
Windows x64 and passes `go vet`; the actual window registration must still be
smoke-tested on Windows 10/11.

## Verification boundaries

The release source was syntax-compiled; the Windows x64 bootstrapper was cross-compiled as a GUI PE executable; the two bundled PDFs were generated and inspected for text content; resource names and package-data declarations were checked. The current build environment is Linux and lacks Pint, PySide6 and PyInstaller, so a real Windows installer execution, PyInstaller build, Qt GUI smoke test and Windows Shell shortcut creation still require the user's Windows validation. Do not treat those Windows-only steps as completed until `build.exe` and the Builder run successfully on Windows 10/11.
