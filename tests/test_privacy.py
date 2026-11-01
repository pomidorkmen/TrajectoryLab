from __future__ import annotations

import ast
import logging
from pathlib import Path

from trajectory_lab.privacy import LocalPathRedactionFilter, redact_local_paths

ROOT = Path(__file__).resolve().parents[1]


def test_redaction_removes_explicit_user_root_from_windows_path() -> None:
    value = r"Loaded file C:\Users\Example Person\Documents\trial.json"
    assert redact_local_paths(value, (r"C:\Users\Example Person",)) == (
        "Loaded file <USER_LOCAL_PATH>\\Documents\\trial.json"
    )


def test_redaction_removes_home_directory_from_log_record() -> None:
    home = str(Path.home())
    record = logging.LogRecord(
        "test", logging.ERROR, __file__, 10, f"Failed under {home}/private/data.json", (), None
    )
    assert LocalPathRedactionFilter().filter(record)
    assert home not in record.getMessage()
    assert "<USER_LOCAL_PATH>" in record.getMessage()


def test_runtime_package_has_no_first_party_network_client_imports() -> None:
    forbidden = {"requests", "httpx", "urllib3", "socket", "smtplib", "aiohttp"}
    for source in (ROOT / "trajectory_lab").rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = {node.module.split(".", 1)[0]}
            else:
                continue
            assert not (imported & forbidden), f"Network client import in {source}: {imported & forbidden}"


def test_builder_journal_redacts_user_profile_paths(monkeypatch) -> None:
    import build

    monkeypatch.setenv("USERPROFILE", r"C:\Users\Researcher")
    message = r"Running Python from C:\Users\Researcher\AppData\Local\TrajectoryLab\python.exe"
    redacted = build.redact_builder_paths(message)
    assert r"C:\Users\Researcher" not in redacted
    assert "<USER_LOCAL_PATH>" in redacted
