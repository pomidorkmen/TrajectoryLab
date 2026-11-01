from __future__ import annotations

import hashlib
import os
from pathlib import Path
import zipfile

from build import write_reproducible_archive


def test_reproducible_archive_ignores_source_mtime_and_permissions(tmp_path: Path) -> None:
    distribution = tmp_path / "TrajectoryLab-0.1.0-test"
    distribution.mkdir()
    payload = distribution / "TrajectoryLab"
    payload.write_bytes(b"deterministic-build-payload")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    os.utime(payload, (1_600_000_000, 1_600_000_000))
    write_reproducible_archive(distribution, first)
    os.utime(payload, (1_700_000_000, 1_700_000_000))
    payload.chmod(0o600)
    write_reproducible_archive(distribution, second)

    first_digest = hashlib.sha256(first.read_bytes()).hexdigest()
    second_digest = hashlib.sha256(second.read_bytes()).hexdigest()
    assert first_digest == second_digest

    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == ["TrajectoryLab-0.1.0-test/TrajectoryLab"]
        info = archive.getinfo(archive.namelist()[0])
        assert info.date_time == (2024, 1, 1, 0, 0, 0)
        assert (info.external_attr >> 16) & 0o777 == 0o755
        assert archive.read(info.filename) == b"deterministic-build-payload"


def test_reproducible_archive_supports_single_executable(tmp_path: Path) -> None:
    executable = tmp_path / "TrajectoryLab.exe"
    executable.write_bytes(b"sample executable")
    archive_path = tmp_path / "TrajectoryLab.zip"

    write_reproducible_archive(executable, archive_path)

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["TrajectoryLab.exe"]
        assert archive.read("TrajectoryLab.exe") == b"sample executable"
        info = archive.getinfo("TrajectoryLab.exe")
        assert (info.external_attr >> 16) & 0o777 == 0o755


def test_security_scan_flags_secret_files_and_token_patterns(tmp_path: Path, monkeypatch) -> None:
    import build

    (tmp_path / "credentials.json").write_text('{"token": "placeholder"}', encoding="utf-8")
    fake_token = "ghp_" + ("A" * 40)
    (tmp_path / "notes.py").write_text(f'TOKEN = "{fake_token}"', encoding="utf-8")
    monkeypatch.setattr(build, "ROOT", tmp_path)
    findings = build.security_scan()
    assert any("credentials.json" in item for item in findings)
    assert any("notes.py" in item for item in findings)


def test_security_scan_allows_template_env_file(tmp_path: Path, monkeypatch) -> None:
    import build

    (tmp_path / ".env.example").write_text("API_KEY=replace_me\n", encoding="utf-8")
    monkeypatch.setattr(build, "ROOT", tmp_path)
    assert build.security_scan() == []


def test_graphical_builder_hides_worker_consoles() -> None:
    source = Path(__file__).resolve().parents[1] / "build.py"
    builder = source.read_text(encoding="utf-8")
    assert "NO_WINDOW_FLAG" in builder
    assert "creationflags=NO_WINDOW_FLAG" in builder
