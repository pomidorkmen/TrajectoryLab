# Third-party software notices

TrajectoryLab uses third-party Python packages. The project dependency ranges
are declared in `pyproject.toml`; they are not a fully hash-locked build
manifest. The exact package versions and all transitive components in a
particular Windows build must be recorded from that build environment before
publishing a binary release.

| Component | Upstream license information | Notes |
|---|---|---|
| Python | Python Software Foundation License (PSF-2.0) | The Builder downloads the official Python installer from python.org and verifies a pinned SHA-256 before execution. |
| NumPy | BSD-3-Clause for NumPy source; wheels can bundle separately licensed libraries | PyPI wheels may include OpenBLAS and the GNU Fortran runtime, each with its own notices. Retain wheel-provided license files. |
| SciPy | BSD-3-Clause, with separately licensed bundled components | Retain the license notices included in the actual wheel. |
| Pint | BSD-3-Clause | Used for unit validation at application and IO boundaries. |
| Pydantic | MIT | Used for parameter/schema validation. |
| PySide6 / Qt 6 | LGPLv3, GPLv2/GPLv3 or commercial licensing, depending on modules and distribution terms | Review the Qt for Python and Qt licensing terms for the precise modules included in each binary. Do not assume every Qt module is LGPL. |
| PyQtGraph | MIT | Scientific plotting widgets. |
| PyOpenGL | BSD-style license | Used by the optional OpenGL visualization stack. Retain the upstream notices. |
| ReportLab | BSD license | PDF generation. |
| PyInstaller | GPL-2.0 with a bootloader exception; limited files under Apache-2.0 | The exception permits packaging applications, subject to the licenses of the bundled dependencies. |

## Primary license references

- Python: <https://docs.python.org/3/license.html>
- NumPy: <https://numpy.org/doc/stable/license.html>
- SciPy: <https://github.com/scipy/scipy/blob/main/LICENSE>
- Pint: <https://pint.readthedocs.io/en/stable/license.html>
- Pydantic: <https://github.com/pydantic/pydantic/blob/main/LICENSE>
- Qt for Python / PySide6: <https://doc.qt.io/qtforpython-6/licenses.html>
- Qt licensing: <https://doc.qt.io/qt-6/licensing.html>
- PyQtGraph: <https://github.com/pyqtgraph/pyqtgraph/blob/master/LICENSE.txt>
- PyOpenGL: <https://pypi.org/project/PyOpenGL/>
- ReportLab: <https://pypi.org/project/reportlab/>
- PyInstaller: <https://pyinstaller.org/en/stable/license.html>

This summary is informational and is not a substitute for reviewing the license
files delivered with the exact wheels and native DLLs used in a specific build.
In particular, Windows PyInstaller bundles must retain required Qt and other
third-party notices and comply with the applicable Qt LGPL/GPL or commercial
terms.
