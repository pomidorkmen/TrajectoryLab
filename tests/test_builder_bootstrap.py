from __future__ import annotations

from pathlib import Path


def _source() -> str:
    return (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "builder"
        / "main_windows.go"
    ).read_text(encoding="utf-8")


def test_bootstrap_resolves_arrow_resource_to_real_cursor_handle() -> None:
    source = _source()
    # IDC_ARROW (32512) is a resource identifier, not an HCURSOR.
    assert 'pLoadCursor.Call(0, uintptr(32512))' in source
    assert 'Cursor: syscall.Handle(cursor)' in source
    assert 'Cursor: 32512' not in source


def test_get_stock_object_is_imported_from_gdi32() -> None:
    source = _source()
    assert 'gdi32              = syscall.NewLazyDLL("gdi32.dll")' in source
    assert 'pGetStockObject    = gdi32.NewProc("GetStockObject")' in source
    assert 'pGetStockObject  = user32.NewProc("GetStockObject")' not in source


def test_bootstrap_hands_off_after_main_builder_window_is_ready() -> None:
    source = _source()
    assert 'uiLaunched.Store(true)' in source
    assert 'cmd.Stdout = uiLog' in source
    assert 'cmd.Stderr = uiLog' in source
    assert 'builder-ui-ready' in source
    assert 'bootstrapHandedOff.Store(true)' in source
    assert 'pPostMessage.Call(uintptr(mainWindow), wmClose, 0, 0)' in source
    assert 'time.Sleep(700 * time.Millisecond)' not in source
    assert 'MessageBoxW' not in source
    assert 'wmAppStart' in source
    assert 'starting runtime preparation automatically' in source


def test_bootstrap_diagnostic_logs_redact_local_user_roots() -> None:
    source = _source()
    assert "func redactLocalPaths(text string) string" in source
    assert "text = redactLocalPaths(text)" in source
    assert 'os.Getenv("USERPROFILE")' in source
    assert 'os.Getenv("LOCALAPPDATA")' in source
