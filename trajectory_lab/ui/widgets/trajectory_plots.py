"""pyqtgraph trajectory and time-series visualizations."""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from trajectory_lab.core.simulation import Trajectory

try:
    import pyqtgraph.opengl as gl
    from PySide6.QtGui import QVector3D
except Exception:  # pragma: no cover - exercised only when the optional GL stack is missing
    gl = None  # type: ignore[assignment]
    QVector3D = None  # type: ignore[assignment,misc]


class Trajectory2DWidget(pg.PlotWidget):
    """Side-view x-y plot with a neutral scientific grid."""

    def __init__(self, translate: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.tr_key = translate
        self.showGrid(x=True, y=True, alpha=0.25)
        self.curve = self.plot([], [], pen=pg.mkPen("#347ba5", width=2))
        self.start_marker = pg.ScatterPlotItem(size=7, brush="#347ba5", pen="#245d7e")
        self.end_marker = pg.ScatterPlotItem(size=7, brush="#347ba5", pen="#245d7e")
        self.addItem(self.start_marker)
        self.addItem(self.end_marker)
        self.retranslate()

    def set_trajectory(self, trajectory: Trajectory | None) -> None:
        if trajectory is None:
            self.curve.setData([], [])
            self.start_marker.setData([])
            self.end_marker.setData([])
            return
        self.curve.setData(trajectory.position_m[:, 0], trajectory.position_m[:, 1])
        self.start_marker.setData([trajectory.position_m[0, 0]], [trajectory.position_m[0, 1]])
        self.end_marker.setData([trajectory.position_m[-1, 0]], [trajectory.position_m[-1, 1]])
        self.enableAutoRange()

    def set_accent(self, accent: str) -> None:
        self.curve.setPen(pg.mkPen(accent, width=2))
        self.start_marker.setBrush(pg.mkBrush(accent))
        self.start_marker.setPen(pg.mkPen(accent))
        self.end_marker.setBrush(pg.mkBrush(accent))
        self.end_marker.setPen(pg.mkPen(accent))

    def retranslate(self) -> None:
        self.setLabel("bottom", self.tr_key("plot.x"), units="m")
        self.setLabel("left", self.tr_key("plot.y"), units="m")


class TimeSeriesWidget(QWidget):
    """Three vertically stacked synchronized time-series plots."""

    def __init__(self, translate: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tr_key = translate
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.speed_plot = pg.PlotWidget()
        self.mach_plot = pg.PlotWidget()
        self.energy_plot = pg.PlotWidget()
        self.plots = (self.speed_plot, self.mach_plot, self.energy_plot)
        for plot in self.plots:
            plot.showGrid(x=True, y=True, alpha=0.2)
            plot.setMaximumHeight(220)
            layout.addWidget(plot, 1)
        self.speed_curve = self.speed_plot.plot([], [], pen=pg.mkPen("#347ba5", width=2))
        self.mach_curve = self.mach_plot.plot([], [], pen=pg.mkPen("#347ba5", width=2))
        self.energy_curve = self.energy_plot.plot([], [], pen=pg.mkPen("#347ba5", width=2))
        self.retranslate()

    def set_trajectory(self, trajectory: Trajectory | None) -> None:
        if trajectory is None:
            for curve in (self.speed_curve, self.mach_curve, self.energy_curve):
                curve.setData([], [])
            return
        time = trajectory.time_s
        self.speed_curve.setData(time, trajectory.speed_m_s)
        self.mach_curve.setData(time, trajectory.mach)
        self.energy_curve.setData(time, trajectory.kinetic_energy_j)
        for plot in self.plots:
            plot.enableAutoRange()

    def set_accent(self, accent: str) -> None:
        for curve in (self.speed_curve, self.mach_curve, self.energy_curve):
            curve.setPen(pg.mkPen(accent, width=2))

    def retranslate(self) -> None:
        for plot in self.plots:
            plot.setLabel("bottom", self.tr_key("plot.time"), units="s")
        self.speed_plot.setLabel("left", self.tr_key("plot.speed"), units="m/s")
        self.mach_plot.setLabel("left", self.tr_key("plot.mach"))
        self.energy_plot.setLabel("left", self.tr_key("plot.energy"), units="J")


class Trajectory3DWidget(QWidget):
    """OpenGL 3D path view with a Y-up to Z-up display-coordinate mapping."""

    def __init__(self, translate: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tr_key = translate
        self.view: Any = None
        self.path_item: Any = None
        self.message: QLabel | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if gl is None or os.environ.get("TRAJECTORYLAB_DISABLE_3D") == "1":
            self.message = QLabel(self.tr_key("message.opengl_missing"))
            self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.message)
        else:
            try:
                self.view = gl.GLViewWidget()
                self.view.setCameraPosition(distance=10, elevation=22, azimuth=35)
                self.view.opts["center"] = QVector3D(0, 0, 1)
                grid = gl.GLGridItem()
                grid.setSize(10, 10, 1)
                grid.setSpacing(1, 1, 1)
                self.view.addItem(grid)
                axes = gl.GLAxisItem()
                axes.setSize(1, 1, 1)
                self.view.addItem(axes)
                layout.addWidget(self.view)
            except Exception:
                # Ошибка инициализации OpenGL не должна блокировать остальные вкладки.
                self.view = None
                self.message = QLabel(self.tr_key("message.opengl_missing"))
                self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(self.message)

    @property
    def available(self) -> bool:
        return self.view is not None

    def set_trajectory(self, trajectory: Trajectory | None) -> None:
        if self.view is None:
            return
        if self.path_item is not None:
            self.view.removeItem(self.path_item)
            self.path_item = None
        if trajectory is None:
            return
        points = np.asarray(trajectory.position_m, dtype=float)
        # pyqtgraph's default OpenGL camera is Z-up; remap the physical Y-up
        # trajectory to display coordinates without changing stored data.
        view_points = points[:, (0, 2, 1)]
        self.path_item = gl.GLLinePlotItem(
            pos=view_points,
            color=(0.20, 0.49, 0.66, 1.0),
            width=2,
            antialias=False,
            mode="line_strip",
        )
        self.view.addItem(self.path_item)
        center = view_points.mean(axis=0)
        self.view.opts["center"] = QVector3D(*map(float, center))
        extent = float(np.max(np.ptp(view_points, axis=0)))
        self.view.setCameraPosition(distance=max(2.0, extent * 1.8 + 1.0))

    def set_theme(self, background: str, accent: str = "#347ba5") -> None:
        if self.view is not None:
            self.view.setBackgroundColor(background)
            if self.path_item is not None:
                self.path_item.setData(color=tuple(channel / 255.0 for channel in bytes.fromhex(accent.lstrip("#"))) + (1.0,))

    def retranslate(self) -> None:
        if self.message is not None:
            self.message.setText(self.tr_key("message.opengl_missing"))
