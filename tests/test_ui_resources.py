"""Source-level checks for packaged UI catalogs and stylesheets."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "trajectory_lab" / "ui" / "i18n"
THEMES = ROOT / "trajectory_lab" / "ui" / "resources" / "themes"


def test_translation_catalogs_have_identical_keys() -> None:
    english = json.loads((I18N / "en.json").read_text(encoding="utf-8"))
    russian = json.loads((I18N / "ru.json").read_text(encoding="utf-8"))
    assert english
    assert english.keys() == russian.keys()
    assert all(value.strip() for value in english.values())
    assert all(value.strip() for value in russian.values())


def test_theme_stylesheets_are_packaged_and_nonempty() -> None:
    for theme in ("light.qss", "dark.qss", "pink.qss"):
        content = (THEMES / theme).read_text(encoding="utf-8")
        assert "QMainWindow" in content
        assert "QDockWidget" in content
        assert "QTableView" in content


def test_packaged_examples_match_source_examples() -> None:
    source_dir = ROOT / "examples"
    package_dir = ROOT / "trajectory_lab" / "examples"
    for source in source_dir.glob("*.json"):
        assert (package_dir / source.name).read_bytes() == source.read_bytes()


def test_pyproject_declares_desktop_dependencies() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"PySide6>=' in pyproject
    assert '"pyqtgraph>=' in pyproject
    assert '"PyOpenGL>=' in pyproject
    assert '"reportlab>=' in pyproject


def test_build_script_collects_qt_plot_and_resource_assets() -> None:
    builder = (ROOT / "build.py").read_text(encoding="utf-8")
    assert '"--collect-all", "PySide6.QtSvg"' in builder
    assert '"--collect-all", "pyqtgraph"' in builder
    assert '"--collect-all", "reportlab"' in builder
    assert '"trajectory_lab/ui/i18n"' in builder
    assert '"trajectory_lab/ui/resources"' in builder
    assert '"--ui-smoke-test"' in builder
    assert '"--icon"' in builder
    assert "create_windows_shortcut" in builder
    assert "CoCreateInstance" in builder
    assert "SHGetKnownFolderPath" in builder
    assert "--windowed" in builder
    assert "TrajectoryLab Builder" in builder
    assert (ROOT / "trajectory_lab" / "ui" / "resources" / "trajectorylab.ico").is_file()
    assert (ROOT / "trajectory_lab" / "ui" / "resources" / "trajectorylab.png").is_file()
    assert "PyOpenGL" in builder
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "ui/resources/manuals/*.pdf" in pyproject


def test_translation_catalogs_cover_static_ui_keys_and_qt_about_newlines() -> None:
    import ast

    english = json.loads((I18N / "en.json").read_text(encoding="utf-8"))
    russian = json.loads((I18N / "ru.json").read_text(encoding="utf-8"))
    for catalog in (english, russian):
        assert "\\n" not in catalog["message.about"]
        assert len(catalog["message.about"].splitlines()) == 3

    referenced: set[str] = set()
    ui_root = ROOT / "trajectory_lab" / "ui"
    for source in ui_root.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "tr_key" or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                referenced.add(first.value)

    assert referenced
    assert referenced <= english.keys()
    assert referenced <= russian.keys()
    for prefix, values in {
        "atmosphere.": ("isa", "constant", "exponential"),
        "drag.": ("none", "stokes", "schiller_naumann", "cgw_composite", "quadratic", "tabular"),
        "interpolation.": ("linear", "log-log", "cubic-log-log"),
        "extrapolation.": ("error", "clamp", "extrapolate"),
        "integrator.": ("rk4", "dop853"),
    }.items():
        for value in values:
            assert prefix + value in english
            assert prefix + value in russian


def test_main_window_and_parameter_panel_keep_qt_i18n_and_baseline_reset() -> None:
    main_window = (ROOT / "trajectory_lab" / "ui" / "main_window.py").read_text(encoding="utf-8")
    parameter_panel = (
        ROOT / "trajectory_lab" / "ui" / "widgets" / "parameter_panel.py"
    ).read_text(encoding="utf-8")
    assert "CatalogTranslator" in main_window
    assert "installTranslator" in main_window
    assert "def set_language" in main_window
    assert "baseline_spec" in main_window
    assert "def reset_parameters" in main_window
    assert "self.experiment_edited.emit()" in parameter_panel


def test_plot_and_table_sources_use_neutral_single_accent_and_fixed_precision() -> None:
    plots = (ROOT / "trajectory_lab" / "ui" / "widgets" / "trajectory_plots.py").read_text(encoding="utf-8")
    table = (ROOT / "trajectory_lab" / "ui" / "models" / "trajectory_table.py").read_text(encoding="utf-8")
    assert 'pg.mkPen("#347ba5", width=2)' in plots
    assert 'brush="#347ba5"' in plots
    assert 'f"{value:.7e}"' in table


def test_opengl_widget_creation_has_a_fallback_path() -> None:
    plots = (ROOT / "trajectory_lab" / "ui" / "widgets" / "trajectory_plots.py").read_text(encoding="utf-8")
    assert "except Exception:" in plots
    assert 'self.message = QLabel(self.tr_key("message.opengl_missing"))' in plots


def test_about_and_manual_assets_are_bundled() -> None:
    resources = ROOT / "trajectory_lab" / "ui" / "resources"
    assert (resources / "cow.png").is_file()
    assert (resources / "manuals" / "TrajectoryLab_Manual_RU.pdf").read_bytes().startswith(b"%PDF-")
    assert (resources / "manuals" / "TrajectoryLab_Manual_EN.pdf").read_bytes().startswith(b"%PDF-")
    main_window = (ROOT / "trajectory_lab" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'self.action_theme_pink = QAction' in main_window
    assert 'self.tr_key("about.signature")' in main_window
    assert 'self.tr_key("action.manual_ru")' in main_window


def test_builder_bootstrap_has_pinned_official_python_runtime() -> None:
    bootstrap = (ROOT / "tools" / "builder" / "main_windows.go").read_text(encoding="utf-8")
    assert "python.org/ftp/python/3.14.10" in bootstrap
    assert "installerSHA256" in bootstrap
    assert "SHA-256 mismatch" in bootstrap
    assert "InstallAllUsers=0" in bootstrap
    assert "TargetDir=" in bootstrap


def test_iteration4_release_resources_and_metadata() -> None:
    resources = ROOT / "trajectory_lab" / "ui" / "resources"
    cow = (resources / "cow.png").read_bytes()
    assert cow.startswith(b"\x89PNG\r\n\x1a\n")
    manuals = resources / "manuals"
    assert (manuals / "TrajectoryLab_Manual_RU.pdf").read_bytes().startswith(b"%PDF-")
    assert (manuals / "TrajectoryLab_Manual_EN.pdf").read_bytes().startswith(b"%PDF-")
    bootstrapper = ROOT / "build.exe"
    if bootstrapper.exists():  # present only in the full Windows Release package
        assert bootstrapper.read_bytes().startswith(b"MZ")
    assert (ROOT / "tools" / "builder" / "main_windows.go").is_file()
    assert "0.4.2" in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert (ROOT / "docs" / "iteration4.md").is_file()


def test_builder_bootstrap_download_is_sha256_pinned() -> None:
    bootstrap = (ROOT / "tools" / "builder" / "main_windows.go").read_text(encoding="utf-8")
    assert '"sync/atomic"' in bootstrap
    assert "bootstrapping.Load()" in bootstrap
    assert "bootstrapping.Store(false)" in bootstrap
    assert "python-3.14.10-amd64.exe" in bootstrap
    assert "92480239264744fe0386a1bd8275786fefa126e3129e56a68e22b52c73329965" in bootstrap


def test_about_describes_scope_privacy_and_security_in_both_languages() -> None:
    import json

    root = Path(__file__).resolve().parents[1] / "trajectory_lab" / "ui" / "i18n"
    ru = json.loads((root / "ru.json").read_text(encoding="utf-8"))
    en = json.loads((root / "en.json").read_text(encoding="utf-8"))
    for catalog, headings in (
        (ru, ("ФИЗИЧЕСКАЯ МОДЕЛЬ", "ТЕХНОЛОГИИ", "ЛОКАЛЬНЫЕ ДАННЫЕ", "СЕТЕВОЕ ПОВЕДЕНИЕ")),
        (en, ("PHYSICAL MODEL", "TECHNOLOGY", "LOCAL DATA", "NETWORK AND SECURITY")),
    ):
        details = catalog["about.details"]
        for heading in headings:
            assert heading in details
        assert "pomidorkmen" in catalog["about.project_line"]
