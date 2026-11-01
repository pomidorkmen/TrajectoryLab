"""Local privacy helpers for log records; never transmit or persist user-home paths."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re


def redact_local_paths(text: str, roots: tuple[str, ...] | None = None) -> str:
    """Replace user-specific local roots with stable placeholders.

    This is a defensive convenience for log sharing, not a complete PII scrubber.
    """
    if roots is None:
        candidates = [str(Path.home())]
        for key in ("USERPROFILE", "LOCALAPPDATA", "APPDATA"):
            value = os.environ.get(key)
            if value:
                candidates.append(value)
        roots = tuple(dict.fromkeys(item for item in candidates if item and item not in {"/", "\\"}))
    result = text
    for root in sorted(roots, key=len, reverse=True):
        variants = {root, root.replace("\\", "/"), root.replace("/", "\\")}
        for variant in sorted(variants, key=len, reverse=True):
            if not variant:
                continue
            result = re.sub(re.escape(variant), "<USER_LOCAL_PATH>", result, flags=re.IGNORECASE if os.name == "nt" else 0)
    return result


class LocalPathRedactionFilter(logging.Filter):
    """Redact home/AppData paths from messages and formatted exception traces."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redact_local_paths(record.getMessage())
            record.args = ()
            if record.exc_info:
                formatted = logging.Formatter().formatException(record.exc_info)
                record.exc_text = redact_local_paths(formatted)
                record.exc_info = None
            elif record.exc_text:
                record.exc_text = redact_local_paths(record.exc_text)
        except Exception:
            # A privacy filter must never break application logging.
            record.msg = "Log record omitted by privacy filter"
            record.args = ()
            record.exc_info = None
        return True
