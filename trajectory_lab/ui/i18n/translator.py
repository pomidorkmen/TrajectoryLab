"""JSON-backed QTranslator; catalog files keep UI strings out of widgets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTranslator


class CatalogTranslator(QTranslator):
    """A small QTranslator implementation backed by a JSON message catalog."""

    def __init__(self, catalog_path: Path, parent: Any = None) -> None:
        super().__init__(parent)
        self._catalog: dict[str, str] = {}
        self.load_catalog(catalog_path)

    def load_catalog(self, catalog_path: Path) -> None:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        self._catalog = {str(key): str(value) for key, value in payload.items()}

    def translate(
        self,
        context: str,
        source_text: str,
        disambiguation: str | None = None,
        n: int = -1,
    ) -> str:
        del context, disambiguation, n
        return self._catalog.get(source_text, source_text)
