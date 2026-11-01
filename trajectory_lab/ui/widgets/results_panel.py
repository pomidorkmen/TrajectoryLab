"""Compact key-result inspector."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

from trajectory_lab.core.simulation import Trajectory


class ResultsPanel(QWidget):
    """Display derived quantities in a compact monospace form."""

    RESULT_KEYS = (
        "result.range", "result.duration", "result.impact", "result.apogee", "result.apogee_time",
        "result.max_speed", "result.final_speed", "result.max_mach", "result.max_re",
        "result.final_energy", "result.checksum",
    )

    def __init__(self, translate: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tr_key = translate
        self.layout = QFormLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setVerticalSpacing(4)
        self.values: dict[str, QLabel] = {}
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        for key in self.RESULT_KEYS:
            label = QLabel("—")
            label.setFont(fixed_font)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.values[key] = label
            self.layout.addRow(self.tr_key(key), label)
        self.clear()

    def clear(self) -> None:
        for value in self.values.values():
            value.setText("—")

    def update_trajectory(self, trajectory: Trajectory) -> None:
        impact = (
            f"{trajectory.impact_time_s:.6f} s"
            if trajectory.impact_time_s is not None
            else self.tr_key("message.impact_missing")
        )
        result_values = {
            "result.range": f"{trajectory.range_m:.6f} m",
            "result.duration": f"{trajectory.time_s[-1]:.6f} s",
            "result.impact": impact,
            "result.apogee": f"{trajectory.maximum_height_m:.6f} m",
            "result.apogee_time": f"{trajectory.maximum_height_time_s:.6f} s",
            "result.max_speed": f"{float(trajectory.speed_m_s.max()):.6f} m/s",
            "result.final_speed": f"{float(trajectory.speed_m_s[-1]):.6f} m/s",
            "result.max_mach": f"{float(trajectory.mach.max()):.6f}",
            "result.max_re": f"{float(trajectory.reynolds.max()):.6g}",
            "result.final_energy": f"{float(trajectory.kinetic_energy_j[-1]):.6e} J",
            "result.checksum": trajectory.checksum_sha256,
        }
        for key, text in result_values.items():
            self.values[key].setText(text)

    def retranslate(self) -> None:
        for key in self.RESULT_KEYS:
            label = self.layout.labelForField(self.values[key])
            if label is not None:
                label.setText(self.tr_key(key))
