from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_builder_is_one_light_window_with_no_modal_popups() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")
    assert "class BuilderApp" in source
    assert "tk.Toplevel" not in source
    assert "messagebox" not in source
    assert "showerror(" not in source
    assert "showinfo(" not in source
    assert "theme_frame = ttk.LabelFrame" in source
    assert "self.apply_button.pack_forget()" in source
    assert "def apply_theme(self)" in source
    assert 'self.root.configure(bg="#e8ebee")' in source
    assert 'font=("Segoe UI", 9)' in source


def test_builder_has_live_russian_and_english_flag_controls() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")
    assert 'self.flag_canvases["en"]' in source
    assert 'self.flag_canvases["ru"]' in source
    assert 'lambda _event: self.set_language("en")' in source
    assert 'lambda _event: self.set_language("ru")' in source
    assert '"en": {' in source and '"ru": {' in source
    assert '"v0.4.2"' in source


def test_builder_theme_defaults_to_light_and_keeps_app_theme_picker_in_same_window() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")
    assert 'tk.StringVar(value="light")' in source
    assert 'for key in ("light", "dark", "pink")' in source
    assert 'self.theme_frame.pack_forget()' in source
    assert 'self.theme_frame.pack(fill="x"' in source
    assert 'ttk.Toplevel' not in source


def test_builder_signals_ready_after_main_window_is_constructed() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")
    assert "self.root.update_idletasks()" in source
    assert '"builder-ui-ready"' in source


def test_about_cow_is_revealed_after_nine_signature_clicks() -> None:
    source = (ROOT / "trajectory_lab/ui/main_window.py").read_text(encoding="utf-8")
    assert 'click_state = {"count": 0, "revealed": False}' in source
    assert 'click_state["count"] < 9' in source
    assert 'signature.clicked.connect(reveal_cow)' in source
    assert 'image.hide()' in source
    assert 'image.show()' in source


def test_builder_translation_catalogs_are_complete() -> None:
    import build

    assert set(build.BuilderApp.TEXT["ru"]) == set(build.BuilderApp.TEXT["en"])
    assert set(build.BuilderApp.TEXT["ru"]["stage"]) == set(build.BuilderApp.TEXT["en"]["stage"])
