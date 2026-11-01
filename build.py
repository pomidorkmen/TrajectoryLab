#!/usr/bin/env python3
"""TrajectoryLab Builder 0.4.2 — compact RU/EN scientific build utility."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import queue
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
import venv
import zipfile

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError as exc:  # pragma: no cover - environment-specific bootstrap error
    raise SystemExit(
        "Tkinter is required for the graphical Builder. Use build.exe to install the bundled per-user Python runtime."
    ) from exc

ROOT = Path(__file__).resolve().parent
APP_VERSION = "0.4.2"
SOURCE_DATE_EPOCH = 1704067200
PYTHONHASHSEED = "0"
DATA_DIRECTORIES = (
    "examples", "models_examples", "docs",
    "trajectory_lab/ui/i18n", "trajectory_lab/ui/resources",
)
EXCLUDED_DIRS = {
    ".git", ".venv", ".builder-venv", "build", "dist", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov",
}
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
FORBIDDEN_SECRET_FILES = {".env", "id_rsa", "id_ed25519", "credentials.json", "secrets.json"}
TEXT_SUFFIXES = {".py", ".json", ".toml", ".ini", ".cfg", ".yaml", ".yml", ".txt", ".md", ".ps1", ".bat", ".go", ".svg", ".xml"}
NO_WINDOW_FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0



def write_reproducible_archive(source: Path, output: Path) -> None:
    """Create a reproducible ZIP for a file or directory (stable paths and metadata)."""
    source = Path(source)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromtimestamp(SOURCE_DATE_EPOCH, tz=timezone.utc).timetuple()[:6]
    if source.is_file():
        entries = [(source, Path(source.name))]
    elif source.is_dir():
        entries = []
        for path in source.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(source)
            if any(part in EXCLUDED_DIRS for part in relative.parts):
                continue
            if path.suffix.lower() in {".pyc", ".pyo", ".tmp"} or path.name in {".coverage", ".DS_Store", "Thumbs.db"}:
                continue
            entries.append((path, Path(source.name) / relative))
        entries.sort(key=lambda item: item[1].as_posix().lower())
    else:
        raise FileNotFoundError(source)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, archive_name in entries:
            info = zipfile.ZipInfo(archive_name.as_posix(), date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            mode = 0o755 if path.suffix.lower() == ".exe" or not path.suffix else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            with path.open("rb") as source_stream, archive.open(info, "w") as target_stream:
                shutil.copyfileobj(source_stream, target_stream)

def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / "TrajectoryLabBuilder" / APP_VERSION
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_version() -> str:
    import tomllib
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def redact_builder_paths(message: str) -> str:
    """Redact common per-user Windows roots from Builder journal messages."""
    roots = [str(Path.home())]
    for key in ("USERPROFILE", "LOCALAPPDATA", "APPDATA"):
        value = os.environ.get(key)
        if value:
            roots.append(value)
    result = message
    for root in sorted(set(value for value in roots if value and value not in {"/", "\\"}), key=len, reverse=True):
        variants = {root, root.replace("\\", "/"), root.replace("/", "\\")}
        for variant in sorted(variants, key=len, reverse=True):
            result = re.sub(re.escape(variant), "<USER_LOCAL_PATH>", result,
                            flags=re.IGNORECASE if os.name == "nt" else 0)
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _iter_project_files():
    for base, dirs, files in os.walk(ROOT, followlinks=False):
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
        for name in files:
            path = Path(base) / name
            if path.is_symlink():
                continue
            yield path


def security_scan() -> list[str]:
    """Perform a conservative local scan for accidental secrets and unsafe files."""
    findings: list[str] = []
    for path in _iter_project_files():
        name = path.name.lower()
        if name in FORBIDDEN_SECRET_FILES or (name.startswith(".env.") and name != ".env.example"):
            findings.append(f"Sensitive-looking file: {path.relative_to(ROOT)}")
            continue
        if path.suffix.lower() in {".pem", ".p12", ".pfx", ".key", ".ppk"}:
            findings.append(f"Private-key/certificate file: {path.relative_to(ROOT)}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(f"Possible credential pattern in {path.relative_to(ROOT)} ({pattern.pattern})")
    return findings


def create_windows_shortcut(executable: Path) -> Path:
    """Create and verify a shortcut in the actual Windows Known Folder Desktop."""
    if os.name != "nt":
        raise OSError("Windows desktop shortcuts can only be created on Windows")
    import ctypes
    import uuid
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    desktop_id = GUID.from_buffer_copy(uuid.UUID("B4BFCC3A-DB2C-424C-B029-7FE99A87C641").bytes_le)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    ole32 = ctypes.OleDLL("ole32")
    desktop_ptr = ctypes.c_wchar_p()
    shell32.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long
    result = shell32.SHGetKnownFolderPath(ctypes.byref(desktop_id), 0, None, ctypes.byref(desktop_ptr))
    if result != 0 or not desktop_ptr.value:
        raise OSError(f"SHGetKnownFolderPath failed: HRESULT 0x{result & 0xffffffff:08X}")
    try:
        desktop = Path(desktop_ptr.value)
    finally:
        ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        ole32.CoTaskMemFree(ctypes.cast(desktop_ptr, ctypes.c_void_p))
    if not desktop.is_dir():
        raise FileNotFoundError(f"Windows Desktop folder does not exist: {desktop}")

    # Windows Script Host is used only for the standard ShellLink COM object.
    # Resolve a robust, OS-managed shortcut through the ShellLink COM API.
    from ctypes import wintypes
    class GUID2(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]
    def guid(text: str) -> GUID2:
        value = uuid.UUID(text)
        return GUID2(value.fields[0], value.fields[1], value.fields[2], (ctypes.c_ubyte * 8).from_buffer_copy(value.bytes[8:]))
    def method(obj: ctypes.c_void_p, index: int, restype: object, argtypes: list[object], *args: object) -> int:
        table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        fn = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(table[index])
        return int(fn(obj, *args))
    ole32.CoInitialize.argtypes = [ctypes.c_void_p]
    ole32.CoInitialize.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = []
    ole32.CoCreateInstance.argtypes = [ctypes.POINTER(GUID2), ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(GUID2), ctypes.POINTER(ctypes.c_void_p)]
    ole32.CoCreateInstance.restype = ctypes.c_long
    shell_link = ctypes.c_void_p()
    persist = ctypes.c_void_p()
    initialized = False
    target = executable.resolve()
    shortcut = desktop / "TrajectoryLab.lnk"
    try:
        # Удаляем старую ссылку перед записью новой, чтобы повторная сборка была идемпотентной.
        try:
            shortcut.unlink()
        except FileNotFoundError:
            pass
        hr = int(ole32.CoInitialize(None))
        if hr < 0:
            raise OSError(f"COM initialization failed: 0x{hr & 0xffffffff:08X}")
        initialized = True
        hr = int(ole32.CoCreateInstance(ctypes.byref(guid("00021401-0000-0000-C000-000000000046")), None, 1,
                                        ctypes.byref(guid("000214F9-0000-0000-C000-000000000046")), ctypes.byref(shell_link)))
        if hr < 0 or not shell_link:
            raise OSError(f"ShellLink creation failed: 0x{hr & 0xffffffff:08X}")
        for index, value in ((20, str(target)), (9, str(target.parent)), (7, "TrajectoryLab scientific desktop application")):
            hr = method(shell_link, index, ctypes.c_long, [wintypes.LPCWSTR], value)
            if hr < 0:
                raise OSError(f"ShellLink property failed: 0x{hr & 0xffffffff:08X}")
        # Сам EXE содержит иконку, поэтому ярлык не зависит от папки исходников.
        method(shell_link, 17, ctypes.c_long, [wintypes.LPCWSTR, ctypes.c_int], f"{target},0", 0)
        method(shell_link, 15, ctypes.c_long, [ctypes.c_int], 1)
        iid_persist = guid("0000010b-0000-0000-C000-000000000046")
        table = ctypes.cast(shell_link, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        query = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(GUID2), ctypes.POINTER(ctypes.c_void_p))(table[0])
        hr = int(query(shell_link, ctypes.byref(iid_persist), ctypes.byref(persist)))
        if hr < 0 or not persist:
            raise OSError(f"IPersistFile query failed: 0x{hr & 0xffffffff:08X}")
        hr = method(persist, 6, ctypes.c_long, [wintypes.LPCWSTR, wintypes.BOOL], str(shortcut), True)
        if hr < 0 or not shortcut.is_file():
            raise OSError(f"Shortcut save failed: 0x{hr & 0xffffffff:08X}")
        # Проверяем назначение ярлыка через ShellLink GetPath.
        resolved = ctypes.create_unicode_buffer(32768)
        hr = method(shell_link, 3, ctypes.c_long, [wintypes.LPWSTR, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], resolved, len(resolved), None, 0)
        if hr < 0 or Path(resolved.value).resolve() != target:
            raise OSError("The created shortcut does not point to the expected executable")
        return shortcut
    finally:
        for obj in (persist, shell_link):
            if obj:
                try:
                    method(obj, 2, ctypes.c_ulong, [])
                except Exception:
                    pass
        if initialized:
            ole32.CoUninitialize()


class BuilderApp:
    """Single-window, compact Builder UI with Russian/English localization."""

    TEXT = {
        "en": {
            "title": "TrajectoryLab Builder",
            "subtitle": "Scientific desktop build utility",
            "language": "LANGUAGE",
            "config": "BUILD OPTIONS",
            "tests": "Run scientific test suite",
            "clean": "Clean previous build files",
            "onefile": "Build single-file executable (slower startup)",
            "shortcut": "Create and verify Desktop shortcut",
            "progress": "BUILD PROGRESS",
            "ready": "Ready to build",
            "journal": "BUILD JOURNAL",
            "idle": "Idle",
            "build": "BUILD TRAJECTORYLAB",
            "building": "BUILDING…",
            "retry": "RETRY BUILD",
            "theme": "APPLICATION THEME",
            "theme_hint": "Choose the initial theme for the installed application.",
            "light": "Light",
            "dark": "Dark",
            "pink": "Soft pink",
            "apply": "APPLY THEME",
            "apply_done": "THEME SAVED",
            "success": "Build completed successfully",
            "failed": "Build failed — see the journal",
            "no_source": "Project files were not found. Extract the complete archive first.",
            "theme_saved": "Application theme saved: {theme}",
            "shortcut_ok": "Desktop shortcut created and verified: {path}",
            "shortcut_error": "Desktop shortcut could not be created: {error}",
            "theme_error": "Theme could not be saved: {error}",
            "exe": "Executable: {path}",
            "stage": {
                "Checking Python runtime": "Checking Python runtime",
                "Installing application and build dependencies": "Installing application and build dependencies",
                "Checking installed dependency consistency": "Checking dependency consistency",
                "Scanning source tree for accidental secrets": "Scanning source tree for accidental secrets",
                "Running full scientific test suite": "Running scientific tests",
                "Removing previous build output": "Removing previous build output",
                "Packaging Qt, SciPy, Pint and scientific resources": "Packaging Qt, SciPy, Pint and scientific resources",
                "Running packaged application smoke test": "Running application smoke test",
                "Creating reproducible distribution ZIP": "Creating reproducible distribution ZIP",
                "Build package verified; choose the initial application theme": "Build verified — choose application theme",
            },
        },
        "ru": {
            "title": "TrajectoryLab Builder",
            "subtitle": "Сборка научного настольного приложения",
            "language": "ЯЗЫК",
            "config": "ПАРАМЕТРЫ СБОРКИ",
            "tests": "Запустить полный набор научных тестов",
            "clean": "Удалить предыдущие файлы сборки",
            "onefile": "Один EXE-файл (более медленный запуск)",
            "shortcut": "Создать и проверить ярлык на рабочем столе",
            "progress": "ХОД СБОРКИ",
            "ready": "Готово к сборке",
            "journal": "ЖУРНАЛ СБОРКИ",
            "idle": "Ожидание",
            "build": "СОБРАТЬ TRAJECTORYLAB",
            "building": "ВЫПОЛНЯЕТСЯ СБОРКА…",
            "retry": "ПОВТОРИТЬ СБОРКУ",
            "theme": "ТЕМА ПРИЛОЖЕНИЯ",
            "theme_hint": "Выберите начальную тему собранного приложения.",
            "light": "Светлая",
            "dark": "Тёмная",
            "pink": "Нежно-розовая",
            "apply": "ПРИМЕНИТЬ ТЕМУ",
            "apply_done": "ТЕМА СОХРАНЕНА",
            "success": "Сборка успешно завершена",
            "failed": "Ошибка сборки — подробности в журнале",
            "no_source": "Файлы проекта не найдены. Сначала распакуйте полный архив.",
            "theme_saved": "Тема приложения сохранена: {theme}",
            "shortcut_ok": "Ярлык создан и проверен: {path}",
            "shortcut_error": "Не удалось создать ярлык: {error}",
            "theme_error": "Не удалось сохранить тему: {error}",
            "exe": "Исполняемый файл: {path}",
            "stage": {
                "Checking Python runtime": "Проверка Python",
                "Installing application and build dependencies": "Установка зависимостей приложения и сборщика",
                "Checking installed dependency consistency": "Проверка согласованности зависимостей",
                "Scanning source tree for accidental secrets": "Проверка исходников на случайные секреты",
                "Running full scientific test suite": "Выполнение научных тестов",
                "Removing previous build output": "Удаление предыдущих результатов сборки",
                "Packaging Qt, SciPy, Pint and scientific resources": "Упаковка Qt, SciPy, Pint и научных ресурсов",
                "Running packaged application smoke test": "Проверка запуска собранного приложения",
                "Creating reproducible distribution ZIP": "Создание воспроизводимого ZIP-дистрибутива",
                "Build package verified; choose the initial application theme": "Сборка проверена — выберите тему приложения",
            },
        },
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("TrajectoryLab Builder")
        icon_path = ROOT / "trajectory_lab" / "ui" / "resources" / "trajectorylab.ico"
        if os.name == "nt" and icon_path.is_file():
            try:
                self.root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass
        self.root.geometry("760x600")
        self.root.minsize(700, 540)
        self.root.configure(bg="#e8ebee")
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.running = False
        self.built_executable: Path | None = None
        self.worker: threading.Thread | None = None
        self.language = "ru"
        self.current_stage = "Ready to build"
        self.options = {"run_tests": True, "clean": True, "onefile": False, "shortcut": True}
        self.labels: dict[str, object] = {}
        self.frames: dict[str, ttk.LabelFrame] = {}
        self.checks: dict[str, ttk.Checkbutton] = {}
        self.flag_canvases: dict[str, tk.Canvas] = {}
        self.theme_choice = tk.StringVar(value="light")
        self.theme_applied = False
        self._configure_styles()
        self._build_ui()
        self.set_language("ru")
        self.root.after(100, self._poll_events)
        self._log("Builder ready. Build operations run in a private per-user environment.")
        self._log("The builder does not require administrator privileges.")
        self.root.update_idletasks()
        self._signal_ready_to_bootstrap()

    def _signal_ready_to_bootstrap(self) -> None:
        """Tell the native bootstrapper that this single main window is ready."""
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            return
        marker = Path(base) / "TrajectoryLabBuilder" / "builder-ui-ready"
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="ascii")
        except OSError:
            pass  # The marker is optional; the Builder remains usable.

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        bg = "#e8ebee"
        header = "#dce1e6"
        fg = "#252b30"
        border = "#aeb7bf"
        accent = "#4b7898"
        style.configure("TLab.TFrame", background=bg)
        style.configure("TLab.Header.TFrame", background=header)
        style.configure("TLab.TLabel", background=bg, foreground=fg, font=("Segoe UI", 9))
        style.configure("TLab.Header.TLabel", background=header, foreground=fg, font=("Segoe UI", 13, "bold"))
        style.configure("TLab.Version.TLabel", background=header, foreground="#68737c", font=("Segoe UI", 8))
        style.configure("TLab.TButton", background="#e2e6e9", foreground=fg, bordercolor=border,
                        padding=(9, 4), font=("Segoe UI", 9))
        style.map("TLab.TButton", background=[("active", "#d7e3ec"), ("pressed", "#c9d8e3")])
        style.configure("TLab.Horizontal.TProgressbar", troughcolor="#f4f6f7", background=accent,
                        bordercolor=border, lightcolor=accent, darkcolor=accent)
        style.configure("TLab.TCheckbutton", background=bg, foreground=fg, font=("Segoe UI", 9))
        style.configure("TLab.TRadiobutton", background=bg, foreground=fg, font=("Segoe UI", 9))
        style.configure("TLab.TLabelframe", background=bg, bordercolor=border)
        style.configure("TLab.TLabelframe.Label", background=bg, foreground=fg, font=("Segoe UI", 9, "bold"))

    def _draw_flag(self, canvas: tk.Canvas, language: str, selected: bool) -> None:
        canvas.delete("all")
        border = "#4b7898" if selected else "#aeb7bf"
        canvas.create_rectangle(1, 1, 35, 23, fill="#ffffff", outline=border, width=2 if selected else 1)
        if language == "ru":
            canvas.create_rectangle(2, 2, 34, 9, fill="#ffffff", outline="")
            canvas.create_rectangle(2, 9, 34, 16, fill="#2455a4", outline="")
            canvas.create_rectangle(2, 16, 34, 22, fill="#d52b1e", outline="")
        else:
            # Simplified Union Jack, drawn from flat shapes for crisp small-size rendering.
            canvas.create_rectangle(2, 2, 34, 22, fill="#17336b", outline="")
            canvas.create_polygon(2, 2, 7, 2, 34, 17, 34, 22, 29, 22, 2, 7, fill="#ffffff", outline="")
            canvas.create_polygon(34, 2, 29, 2, 2, 17, 2, 22, 7, 22, 34, 7, fill="#ffffff", outline="")
            canvas.create_polygon(2, 2, 4, 2, 34, 19, 34, 22, 31, 22, 2, 5, fill="#c8102e", outline="")
            canvas.create_polygon(34, 2, 32, 2, 2, 19, 2, 22, 5, 22, 34, 5, fill="#c8102e", outline="")
            canvas.create_rectangle(13, 2, 23, 22, fill="#ffffff", outline="")
            canvas.create_rectangle(2, 8, 34, 16, fill="#ffffff", outline="")
            canvas.create_rectangle(16, 2, 20, 22, fill="#c8102e", outline="")
            canvas.create_rectangle(2, 10, 34, 14, fill="#c8102e", outline="")
            canvas.create_rectangle(1, 1, 35, 23, outline=border, width=2 if selected else 1)
        canvas.configure(cursor="hand2", highlightthickness=0)

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, style="TLab.Header.TFrame", padding=(16, 9))
        header.pack(fill="x")
        title_area = ttk.Frame(header, style="TLab.Header.TFrame")
        title_area.pack(side="left", fill="x", expand=True)
        self.labels["title"] = ttk.Label(title_area, text="TrajectoryLab Builder", style="TLab.Header.TLabel")
        self.labels["title"].pack(anchor="w")
        self.labels["subtitle"] = ttk.Label(title_area, text="Scientific desktop build utility", style="TLab.Version.TLabel")
        self.labels["subtitle"].pack(anchor="w", pady=(1, 0))
        right = ttk.Frame(header, style="TLab.Header.TFrame")
        right.pack(side="right", anchor="ne")
        self.labels["version"] = ttk.Label(right, text="v0.4.2", style="TLab.Version.TLabel")
        self.labels["version"].pack(anchor="e", pady=(0, 4))
        flags = ttk.Frame(right, style="TLab.Header.TFrame")
        flags.pack(anchor="e")
        self.flag_canvases["en"] = tk.Canvas(flags, width=36, height=24, bg="#dce1e6", relief="flat", bd=0)
        self.flag_canvases["en"].pack(side="left", padx=(0, 5))
        self.flag_canvases["en"].bind("<Button-1>", lambda _event: self.set_language("en"))
        self.flag_canvases["ru"] = tk.Canvas(flags, width=36, height=24, bg="#dce1e6", relief="flat", bd=0)
        self.flag_canvases["ru"].pack(side="left")
        self.flag_canvases["ru"].bind("<Button-1>", lambda _event: self.set_language("ru"))

        body = ttk.Frame(self.root, style="TLab.TFrame", padding=(14, 10))
        body.pack(fill="both", expand=True)
        options = ttk.LabelFrame(body, text="BUILD OPTIONS", style="TLab.TLabelframe", padding=(9, 7))
        options.pack(fill="x", pady=(0, 8))
        self.frames["config"] = options
        self.option_vars: dict[str, tk.BooleanVar] = {}
        for key, default in (("tests", True), ("clean", True), ("onefile", False), ("shortcut", True)):
            variable = tk.BooleanVar(value=default)
            self.option_vars[key] = variable
            check = ttk.Checkbutton(options, text="", variable=variable, style="TLab.TCheckbutton")
            check.pack(anchor="w", pady=1)
            self.checks[key] = check
        progress_box = ttk.LabelFrame(body, text="BUILD PROGRESS", style="TLab.TLabelframe", padding=(9, 7))
        progress_box.pack(fill="x", pady=(0, 8))
        self.frames["progress"] = progress_box
        self.stage_label = ttk.Label(progress_box, text="Ready to build", style="TLab.TLabel")
        self.stage_label.pack(anchor="w")
        self.progress = ttk.Progressbar(progress_box, style="TLab.Horizontal.TProgressbar", maximum=100, mode="determinate")
        self.progress.pack(fill="x", pady=(6, 3))
        self.percent_label = ttk.Label(progress_box, text="0%", style="TLab.TLabel")
        self.percent_label.pack(anchor="e")

        log_frame = ttk.LabelFrame(body, text="BUILD JOURNAL", style="TLab.TLabelframe", padding=(7, 6))
        log_frame.pack(fill="both", expand=True, pady=(0, 8))
        self.frames["journal"] = log_frame
        self.log_text = tk.Text(log_frame, height=9, wrap="word", bg="#f7f8f9", fg="#29323a",
                                insertbackground="#252b30", relief="solid", bd=1,
                                font=("Segoe UI", 8), padx=6, pady=5)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scroll.set, state="disabled")

        self.theme_frame = ttk.LabelFrame(body, text="APPLICATION THEME", style="TLab.TLabelframe", padding=(9, 6))
        self.frames["theme"] = self.theme_frame
        self.theme_frame.pack(fill="x", pady=(0, 7))
        self.labels["theme_hint"] = ttk.Label(self.theme_frame, text="Choose the initial theme for the installed application.", style="TLab.TLabel")
        self.labels["theme_hint"].pack(anchor="w")
        themes = ttk.Frame(self.theme_frame, style="TLab.TFrame")
        themes.pack(fill="x", pady=(4, 3))
        self.theme_buttons: dict[str, ttk.Radiobutton] = {}
        for key in ("light", "dark", "pink"):
            btn = ttk.Radiobutton(themes, text="", value=key, variable=self.theme_choice, style="TLab.TRadiobutton")
            btn.pack(side="left", padx=(0, 14))
            self.theme_buttons[key] = btn
        self.theme_frame.pack_forget()

        footer = ttk.Frame(body, style="TLab.TFrame")
        footer.pack(fill="x")
        self.status_label = ttk.Label(footer, text="Idle", style="TLab.TLabel")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.apply_button = ttk.Button(footer, text="APPLY THEME", style="TLab.TButton", command=self.apply_theme, state="disabled")
        self.start_button = ttk.Button(footer, text="BUILD TRAJECTORYLAB", style="TLab.TButton", command=self.start_build)
        self.start_button.pack(side="right")

    def set_language(self, language: str) -> None:
        self.language = language if language in self.TEXT else "en"
        t = self.TEXT[self.language]
        self.root.title(t["title"])
        self.labels["title"].configure(text=t["title"])
        self.labels["subtitle"].configure(text=t["subtitle"])
        for key, flag in self.flag_canvases.items():
            self._draw_flag(flag, key, key == self.language)
        self.checks["tests"].configure(text=t["tests"])
        self.checks["clean"].configure(text=t["clean"])
        self.checks["onefile"].configure(text=t["onefile"])
        self.checks["shortcut"].configure(text=t["shortcut"])
        if self.running:
            stage_text = t["stage"].get(self.current_stage, t["building"])
            self.stage_label.configure(text=stage_text)
            self.status_label.configure(text=stage_text)
        elif self.built_executable is None:
            self.stage_label.configure(text=t["ready"])
            self.status_label.configure(text=t["idle"])
        elif self.theme_applied:
            self.stage_label.configure(text=t["success"])
            self.status_label.configure(text=t["success"])
        else:
            self.stage_label.configure(text=t["success"])
            self.status_label.configure(text=t["success"])
        if self.theme_applied:
            self.apply_button.configure(text=t["apply_done"], state="disabled")
        else:
            self.apply_button.configure(text=t["apply"], state="normal" if self.built_executable else "disabled")
        if self.running:
            self.start_button.configure(text=t["building"])
        else:
            self.start_button.configure(text=t["build"] if self.built_executable is None else t["retry"])
        self.frames["config"].configure(text=t["config"])
        self.frames["progress"].configure(text=t["progress"])
        self.frames["journal"].configure(text=t["journal"])
        self.frames["theme"].configure(text=t["theme"])
        self.labels["theme_hint"].configure(text=t["theme_hint"])
        for key, btn in self.theme_buttons.items():
            btn.configure(text=t[key])

    def _log(self, message: str) -> None:
        # Keep user-specific local roots out of copyable/sharable Builder logs.
        message = redact_builder_paths(message)
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{datetime.now().strftime('%H:%M:%S')}  {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _emit(self, kind: str, payload: object) -> None:
        self.events.put((kind, payload))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self._log(str(payload))
                elif kind == "progress":
                    percent, stage = payload  # type: ignore[misc]
                    self.progress["value"] = percent
                    self.current_stage = str(stage)
                    stage_text = self.TEXT[self.language]["stage"].get(self.current_stage, self.current_stage)
                    self.stage_label.configure(text=stage_text)
                    self.percent_label.configure(text=f"{percent}%")
                    self.status_label.configure(text=stage_text)
                elif kind == "done":
                    self.running = False
                    self.current_stage = "Build completed"
                    self.built_executable = Path(str(payload))
                    self.theme_applied = False
                    t = self.TEXT[self.language]
                    self.progress["value"] = 96
                    self.percent_label.configure(text="96%")
                    self.stage_label.configure(text=t["success"])
                    self.status_label.configure(text=t["success"])
                    self.start_button.configure(state="normal", text=t["retry"])
                    self.theme_frame.pack(fill="x", pady=(0, 7), before=self.status_label.master)
                    self.apply_button.configure(state="normal", text=t["apply"])
                    self.apply_button.pack(side="right", padx=(6, 0))
                    self._log(t["exe"].format(path=self.built_executable))
                    if self.options.get("shortcut") and os.name == "nt":
                        try:
                            shortcut = create_windows_shortcut(self.built_executable)
                            self._log(t["shortcut_ok"].format(path=shortcut))
                        except Exception as exc:
                            self._log(t["shortcut_error"].format(error=exc))
                    self.progress["value"] = 100
                    self.percent_label.configure(text="100%")
                elif kind == "error":
                    self.running = False
                    self.current_stage = "Build failed"
                    t = self.TEXT[self.language]
                    self.start_button.configure(state="normal", text=t["retry"])
                    self.status_label.configure(text=t["failed"])
                    self.stage_label.configure(text=t["failed"])
                    self._log("ERROR: " + str(payload))
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def start_build(self) -> None:
        if self.running:
            return
        if not (ROOT / "pyproject.toml").is_file() or not (ROOT / "trajectory_lab").is_dir():
            self.status_label.configure(text=self.TEXT[self.language]["no_source"])
            self._log(self.TEXT[self.language]["no_source"])
            return
        self.running = True
        self.current_stage = "Checking Python runtime"
        self.built_executable = None
        self.theme_applied = False
        self.theme_frame.pack_forget()
        self.apply_button.pack_forget()
        self.apply_button.configure(state="disabled")
        self.options = {
            "run_tests": self.option_vars["tests"].get(),
            "clean": self.option_vars["clean"].get(),
            "onefile": self.option_vars["onefile"].get(),
            "shortcut": self.option_vars["shortcut"].get(),
        }
        self.progress["value"] = 0
        t = self.TEXT[self.language]
        self.start_button.configure(state="disabled", text=t["building"])
        self.status_label.configure(text=t["building"])
        self.worker = threading.Thread(target=self._build_worker, daemon=True)
        self.worker.start()

    def _build_worker(self) -> None:
        try:
            executable = self._perform_build()
            self._emit("done", str(executable))
        except Exception as exc:
            self._emit("error", str(exc))

    def _progress(self, value: int, stage: str) -> None:
        self._emit("progress", (value, stage))

    def _run_stream(self, command: list[str], env: dict[str, str], stage: str) -> None:
        self._emit("log", "Running: " + subprocess.list2cmdline(command))
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace", bufsize=1,
                                   creationflags=NO_WINDOW_FLAG)
        assert process.stdout is not None
        for line in process.stdout:
            self._emit("log", line.rstrip())
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"{stage} failed with exit code {return_code}. See the build journal.")

    def _perform_build(self) -> Path:
        if sys.version_info < (3, 11):
            raise RuntimeError(f"Python 3.11 or newer is required; found {sys.version.split()[0]}.")
        self._progress(3, "Checking Python runtime")
        env = os.environ.copy()
        env["SOURCE_DATE_EPOCH"] = str(SOURCE_DATE_EPOCH)
        env["PYTHONHASHSEED"] = PYTHONHASHSEED
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env["PIP_REQUIRE_VIRTUALENV"] = "1"
        env["PYTHONNOUSERSITE"] = "1"

        build_env = app_data_dir() / "venvs" / f"py{sys.version_info.major}{sys.version_info.minor}"
        build_env.parent.mkdir(parents=True, exist_ok=True)
        build_python = build_env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not build_python.exists():
            self._emit("log", f"Creating private build environment: {build_env}")
            venv.EnvBuilder(with_pip=True, clear=False, symlinks=(os.name != "nt")).create(build_env)
        self._progress(10, "Installing application and build dependencies")
        self._run_stream([str(build_python), "-m", "pip", "install", "--disable-pip-version-check", "-e", ".[build]"], env, "Dependency installation")
        self._progress(22, "Checking installed dependency consistency")
        self._run_stream([str(build_python), "-m", "pip", "check"], env, "pip check")
        self._progress(28, "Scanning source tree for accidental secrets")
        findings = security_scan()
        if findings:
            raise RuntimeError("Security scan found potentially sensitive files or values:\n" + "\n".join(findings))
        self._emit("log", "Security scan: no known high-confidence secret patterns or private-key files found.")
        if self.options["run_tests"]:
            self._progress(35, "Running full scientific test suite")
            self._run_stream([str(build_python), "-m", "pytest", "-q", "--cov=trajectory_lab/core", "--cov-report=term-missing"], env, "pytest")
        else:
            self._emit("log", "Pytest was skipped by user selection.")
        if self.options["clean"]:
            self._progress(48, "Removing previous build output")
            shutil.rmtree(ROOT / "build", ignore_errors=True)
            shutil.rmtree(ROOT / "dist", ignore_errors=True)
        version = project_version()
        tag = f"windows-{platform.machine().lower()}" if os.name == "nt" else f"{platform.system().lower()}-{platform.machine().lower()}"
        dist_root = ROOT / "dist"
        build_root = ROOT / "build"
        staging = build_root / "stage"
        staging.mkdir(parents=True, exist_ok=True)
        self._progress(55, "Packaging Qt, SciPy, Pint and scientific resources")
        command = [
            str(build_python), "-m", "PyInstaller", "--noconfirm",
            "--onefile" if self.options["onefile"] else "--onedir", "--windowed", "--noupx",
            "--name", "TrajectoryLab", "--paths", str(ROOT), "--distpath", str(staging),
            "--workpath", str(build_root / "pyinstaller"), "--specpath", str(build_root / "spec"),
            "--collect-all", "pint", "--collect-all", "scipy", "--collect-all", "reportlab",
            "--collect-all", "PySide6.QtSvg", "--collect-all", "PySide6.QtOpenGL",
            "--collect-all", "PySide6.QtOpenGLWidgets", "--collect-all", "pyqtgraph",
            "--collect-all", "OpenGL", "--hidden-import", "pyqtgraph.opengl",
        ]
        icon = ROOT / "trajectory_lab/ui/resources/trajectorylab.ico"
        if os.name == "nt" and icon.is_file():
            command.extend(["--icon", str(icon)])
        distributions = ("trajectory-lab", "numpy", "scipy", "pydantic", "pint", "PySide6", "pyqtgraph", "PyOpenGL", "reportlab")
        for package in distributions:
            command.extend(["--copy-metadata", package])
        for directory in DATA_DIRECTORIES:
            src = ROOT / directory
            if src.is_dir():
                command.extend(["--add-data", f"{src}{os.pathsep}{directory}"])
        command.append(str(ROOT / "trajectory_lab" / "desktop_entry.py"))
        self._run_stream(command, env, "PyInstaller packaging")
        artifact_name = "TrajectoryLab" if self.options["onefile"] else f"TrajectoryLab-{version}-{tag}"
        staged = staging / "TrajectoryLab.exe" if os.name == "nt" else staging / "TrajectoryLab"
        dist_root.mkdir(exist_ok=True)
        if self.options["onefile"]:
            target_dir = dist_root / artifact_name
            target_dir.mkdir(exist_ok=True)
            target = target_dir / staged.name
            shutil.copy2(staged, target)
        else:
            target_dir = dist_root / artifact_name
            shutil.rmtree(target_dir, ignore_errors=True)
            shutil.move(str(staging / "TrajectoryLab"), str(target_dir))
            target = target_dir / staged.name
        if not target.is_file():
            raise RuntimeError(f"Expected executable was not created: {target}")
        self._progress(80, "Running packaged application smoke test")
        smoke_env = env.copy()
        smoke_env["QT_QPA_PLATFORM"] = "offscreen"
        smoke_env["QT_OPENGL"] = "software"
        smoke_env["TRAJECTORYLAB_DISABLE_3D"] = "1"
        self._run_stream([str(target), "--ui-smoke-test"], smoke_env, "Qt UI smoke test")
        manifest = {
            "application": "TrajectoryLab", "version": version, "platform": platform.platform(),
            "architecture": platform.machine(), "python": platform.python_version(),
            "source_date_epoch": SOURCE_DATE_EPOCH, "executable": target.name,
            "executable_sha256": sha256_file(target),
            "build_mode": "onefile" if self.options["onefile"] else "onedir",
            "dependencies": self._dependency_versions(build_python),
            "security_scan": "passed", "tests": "passed" if self.options["run_tests"] else "skipped",
        }
        (target_dir / "build-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._progress(88, "Creating reproducible distribution ZIP")
        archive_path = dist_root / f"TrajectoryLab-{version}-{tag}.zip"
        self._write_reproducible_zip(target_dir, archive_path)
        self._emit("log", f"Distribution archive: {archive_path}")
        self._progress(94, "Build package verified; choose the initial application theme")
        self.built_executable = target
        return target

    def _dependency_versions(self, python: Path) -> dict[str, str]:
        code = "import importlib.metadata as m,json; names=['numpy','scipy','pint','pydantic','PySide6','pyqtgraph','PyOpenGL','reportlab','pyinstaller']; print(json.dumps({n:m.version(n) for n in names}))"
        result = subprocess.run([str(python), "-c", code], cwd=ROOT, text=True, capture_output=True, check=True,
                                creationflags=NO_WINDOW_FLAG)
        return json.loads(result.stdout.strip())

    def _write_reproducible_zip(self, artifact_dir: Path, output: Path) -> None:
        write_reproducible_archive(artifact_dir, output)

    def apply_theme(self) -> None:
        if self.built_executable is None:
            return
        selected = self.theme_choice.get()
        try:
            build_env = app_data_dir() / "venvs" / f"py{sys.version_info.major}{sys.version_info.minor}"
            python = build_env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            code = (
                "from PySide6.QtCore import QSettings; "
                "s=QSettings('TrajectoryLab','TrajectoryLab'); "
                f"s.setValue('theme','{selected}'); s.sync()"
            )
            subprocess.run([str(python), "-c", code], cwd=ROOT, check=True, timeout=30,
                           creationflags=NO_WINDOW_FLAG, capture_output=True, text=True)
            self.theme_applied = True
            self._log(self.TEXT[self.language]["theme_saved"].format(theme=self.TEXT[self.language][selected]))
            self.status_label.configure(text=self.TEXT[self.language]["success"])
            self.apply_button.configure(text=self.TEXT[self.language]["apply_done"], state="disabled")
        except Exception as exc:
            self._log(self.TEXT[self.language]["theme_error"].format(error=exc))
            self.status_label.configure(text=self.TEXT[self.language]["failed"])


def main() -> int:
    parser = argparse.ArgumentParser(description="TrajectoryLab graphical build utility")
    parser.add_argument("--version", action="version", version="TrajectoryLab Builder 0.4.2")
    parser.parse_args()
    root = tk.Tk()
    BuilderApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
