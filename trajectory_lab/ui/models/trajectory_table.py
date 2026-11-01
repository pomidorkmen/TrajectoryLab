"""Read-only table model for sampled trajectory data."""

from __future__ import annotations

from typing import Any

import numpy as np
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from trajectory_lab.core.simulation import Trajectory


class TrajectoryTableModel(QAbstractTableModel):
    """Displays trajectory samples with fixed-precision numeric columns."""

    HEADERS = (
        "table.time", "table.x", "table.y", "table.z", "table.vx", "table.vy",
        "table.vz", "table.speed", "table.mach", "table.energy", "table.re", "table.cd",
    )

    def __init__(self, translate: Any, parent: Any = None) -> None:
        super().__init__(parent)
        self._translate = translate
        self._columns = np.empty((0, len(self.HEADERS)), dtype=float)

    def set_trajectory(self, trajectory: Trajectory | None) -> None:
        self.beginResetModel()
        if trajectory is None:
            self._columns = np.empty((0, len(self.HEADERS)), dtype=float)
        else:
            self._columns = np.column_stack(
                (
                    trajectory.time_s,
                    trajectory.position_m,
                    trajectory.velocity_m_s,
                    trajectory.speed_m_s,
                    trajectory.mach,
                    trajectory.kinetic_energy_j,
                    trajectory.reynolds,
                    trajectory.cd,
                )
            )
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else int(self._columns.shape[0])

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None
        value = float(self._columns[index.row(), index.column()])
        if role == Qt.ItemDataRole.DisplayRole:
            return f"{value:.7e}"
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{value:.12e}"
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self.HEADERS):
            return self._translate(self.HEADERS[section])
        if orientation == Qt.Orientation.Vertical:
            return str(section + 1)
        return None

    def retranslate(self) -> None:
        self.headerDataChanged.emit(
            Qt.Orientation.Horizontal, 0, len(self.HEADERS) - 1
        )
