"""Localized, auditable PDF experiment reports (ReportLab)."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from trajectory_lab import __version__
from trajectory_lab.core.simulation import Trajectory
from trajectory_lab.io.schemas import ExperimentSpec


_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "title": "TrajectoryLab — Scientific Experiment Report",
        "generated": "Generated",
        "parameters": "1. Experiment parameters",
        "parameter": "Parameter",
        "value": "Value",
        "drag": "2. Drag model and applicability",
        "field": "Field",
        "model": "Model",
        "model_id": "Model ID",
        "version": "Version",
        "author": "Author",
        "source": "Source",
        "geometry": "Geometry",
        "validity": "Validity range",
        "model_hash": "Model SHA-256",
        "source_hash": "Source file SHA-256",
        "method_results": "3. Numerical method and results",
        "result": "Result",
        "samples": "Samples",
        "elapsed": "Elapsed time",
        "range": "Horizontal displacement",
        "height": "Maximum height",
        "apogee_time": "Time of maximum height",
        "max_speed": "Maximum speed",
        "final_speed": "Final speed",
        "max_mach": "Maximum Mach",
        "max_re": "Maximum Reynolds",
        "energy": "Final kinetic energy",
        "impact": "Ground event time",
        "trajectory_hash": "Trajectory SHA-256",
        "provenance": "4. Reproducibility record",
        "plots": "5. Trajectory plots",
        "height_plot": "Height vs time",
        "speed_plot": "Speed vs time",
        "time": "Time (s)",
        "height_axis": "Height y (m)",
        "speed_axis": "Speed (m/s)",
        "warnings": "6. Model applicability warnings",
        "limitation": "Model limitation: spherical rigid particle, point-mass translation, specified atmosphere and wind. The report records model applicability metadata; users remain responsible for validating correlations against their experimental regime.",
        "footer": "TrajectoryLab · Reproducible scientific report",
        "not_reached": "not reached",
    },
    "ru": {
        "title": "TrajectoryLab — Научный отчёт об эксперименте",
        "generated": "Создано",
        "parameters": "1. Параметры эксперимента",
        "parameter": "Параметр",
        "value": "Значение",
        "drag": "2. Модель сопротивления и применимость",
        "field": "Поле",
        "model": "Модель",
        "model_id": "Идентификатор модели",
        "version": "Версия",
        "author": "Автор",
        "source": "Источник",
        "geometry": "Геометрия",
        "validity": "Диапазон применимости",
        "model_hash": "SHA-256 модели",
        "source_hash": "SHA-256 исходного файла",
        "method_results": "3. Численный метод и результаты",
        "result": "Результат",
        "samples": "Отсчёты",
        "elapsed": "Время расчёта",
        "range": "Горизонтальное смещение",
        "height": "Максимальная высота",
        "apogee_time": "Время достижения максимальной высоты",
        "max_speed": "Максимальная скорость",
        "final_speed": "Конечная скорость",
        "max_mach": "Максимальное число Маха",
        "max_re": "Максимальное число Рейнольдса",
        "energy": "Конечная кинетическая энергия",
        "impact": "Время события падения",
        "trajectory_hash": "SHA-256 траектории",
        "provenance": "4. Запись воспроизводимости",
        "plots": "5. Графики траектории",
        "height_plot": "Высота от времени",
        "speed_plot": "Скорость от времени",
        "time": "Время (с)",
        "height_axis": "Высота y (м)",
        "speed_axis": "Скорость (м/с)",
        "warnings": "6. Предупреждения о применимости модели",
        "limitation": "Ограничения модели: жёсткая сферическая частица, поступательное движение материальной точки, заданные атмосфера и ветер. В отчёте приводятся метаданные применимости; пользователь отвечает за проверку корреляций в своём экспериментальном режиме.",
        "footer": "TrajectoryLab · Воспроизводимый научный отчёт",
        "not_reached": "не достигнуто",
    },
}


_PARAMETER_LABELS = {
    "name": ("Название", "Name"),
    "mass": ("Масса", "Mass"),
    "diameter": ("Диаметр", "Diameter"),
    "initial_position": ("Начальное положение", "Initial position"),
    "initial_velocity": ("Начальная скорость", "Initial velocity"),
    "duration": ("Максимальное время симуляции", "Maximum simulation time"),
    "time_step": ("Шаг вывода", "Output step"),
    "stop_at_ground": ("Остановка при y=0", "Stop at y=0"),
    "gravity": ("Ускорение свободного падения", "Gravity"),
    "wind_velocity": ("Скорость ветра", "Wind velocity"),
    "atmosphere": ("Атмосфера", "Atmosphere"),
    "method": ("Интегратор", "Integrator"),
    "rtol": ("Относительный допуск", "Relative tolerance"),
    "atol": ("Абсолютный допуск", "Absolute tolerance"),
    "seed": ("Seed", "Seed"),
}


_FONT_NAMES: tuple[str, str, str] | None = None


def _font_candidates() -> tuple[list[Path], list[Path], list[Path]]:
    candidates: list[tuple[Path, Path, Path]] = []
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates.append((windir / "Fonts" / "segoeui.ttf", windir / "Fonts" / "segoeuib.ttf", windir / "Fonts" / "consola.ttf"))
    candidates.extend([
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")),
        (Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"), Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")),
        (Path("/System/Library/Fonts/Supplemental/Arial.ttf"), Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"), Path("/System/Library/Fonts/Menlo.ttc")),
    ])
    return ([x[0] for x in candidates], [x[1] for x in candidates], [x[2] for x in candidates])


def _register_fonts() -> tuple[str, str, str]:
    global _FONT_NAMES
    if _FONT_NAMES is not None:
        return _FONT_NAMES
    regulars, bolds, monos = _font_candidates()
    regular = next((path for path in regulars if path.is_file()), None)
    bold = next((path for path in bolds if path.is_file()), None)
    mono = next((path for path in monos if path.is_file()), None)
    if regular is None or bold is None:
        raise RuntimeError(
            "A Unicode font supporting Cyrillic is required for PDF reports. "
            "Install Segoe UI (Windows) or DejaVu Sans (Linux)."
        )
    pdfmetrics.registerFont(TTFont("TL-Regular", str(regular)))
    pdfmetrics.registerFont(TTFont("TL-Bold", str(bold)))
    mono_name = "Courier"
    if mono is not None and mono.suffix.lower() == ".ttf":
        pdfmetrics.registerFont(TTFont("TL-Mono", str(mono)))
        mono_name = "TL-Mono"
    _FONT_NAMES = ("TL-Regular", "TL-Bold", mono_name)
    return _FONT_NAMES


def _tr(language: str, key: str) -> str:
    if language == "both":
        return f"{_TRANSLATIONS['ru'][key]} / {_TRANSLATIONS['en'][key]}"
    return _TRANSLATIONS[language][key]


class XYPlot(Flowable):
    """Small vector line plot used in PDF reports without raster dependencies."""

    def __init__(self, x: Any, y: Any, title: str, x_label: str, y_label: str) -> None:
        super().__init__()
        self.x = [float(value) for value in x]
        self.y = [float(value) for value in y]
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.width = 170 * mm
        self.height = 66 * mm

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        self.width = min(self.width, available_width)
        return self.width, self.height

    def draw(self) -> None:
        regular, bold, _mono = _register_fonts()
        canvas = self.canv
        left, bottom = 16 * mm, 13 * mm
        plot_width = self.width - 24 * mm
        plot_height = self.height - 25 * mm
        canvas.saveState()
        canvas.setFont(bold, 9)
        canvas.setFillColor(colors.HexColor("#263238"))
        canvas.drawString(0, self.height - 7 * mm, self.title)
        canvas.setStrokeColor(colors.HexColor("#aab3b8"))
        canvas.setLineWidth(0.5)
        canvas.line(left, bottom, left + plot_width, bottom)
        canvas.line(left, bottom, left, bottom + plot_height)
        if self.x and self.y and len(self.x) == len(self.y):
            xmin, xmax = min(self.x), max(self.x)
            ymin, ymax = min(self.y), max(self.y)
            if xmax <= xmin:
                xmax = xmin + 1.0
            if ymax <= ymin:
                ymax = ymin + 1.0
            margin = (ymax - ymin) * 0.05
            ymin -= margin
            ymax += margin
            canvas.setStrokeColor(colors.HexColor("#b36f8b"))
            canvas.setLineWidth(1.3)
            points = []
            stride = max(1, len(self.x) // 1500)
            for index in range(0, len(self.x), stride):
                px = left + (self.x[index] - xmin) / (xmax - xmin) * plot_width
                py = bottom + (self.y[index] - ymin) / (ymax - ymin) * plot_height
                points.append((px, py))
            if len(points) >= 2:
                path = canvas.beginPath()
                path.moveTo(*points[0])
                for point in points[1:]:
                    path.lineTo(*point)
                canvas.drawPath(path, stroke=1, fill=0)
        canvas.setFont(regular, 7)
        canvas.setFillColor(colors.HexColor("#455a64"))
        canvas.drawCentredString(left + plot_width / 2, 3 * mm, self.x_label)
        canvas.saveState()
        canvas.translate(4 * mm, bottom + plot_height / 2)
        canvas.rotate(90)
        canvas.drawCentredString(0, 0, self.y_label)
        canvas.restoreState()
        canvas.restoreState()


def _format_quantity(value: Any) -> str:
    if isinstance(value, dict) and "value" in value and "unit" in value:
        return f"{value['value']:.10g} {value['unit']}"
    if isinstance(value, (list, tuple)):
        return ", ".join(_format_quantity(item) for item in value)
    return str(value)


def export_pdf_report(
    path: str | Path,
    experiment: ExperimentSpec,
    trajectory: Trajectory,
    *,
    language: str = "en",
) -> Path:
    """Write a localized audit report; language may be ``ru``, ``en`` or ``both``."""
    if language not in {"ru", "en", "both"}:
        raise ValueError("PDF language must be 'ru', 'en' or 'both'")
    regular, bold, mono = _register_fonts()
    target = Path(path)
    if target.suffix.lower() != ".pdf":
        target = target.with_suffix(".pdf")
    target.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], fontName=bold, alignment=TA_CENTER,
        textColor=colors.HexColor("#382d34"), fontSize=16, spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader", parent=styles["Heading2"], fontName=bold,
        textColor=colors.HexColor("#9b5875"), fontSize=10.5, spaceBefore=4 * mm, spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(name="ReportBody", parent=styles["BodyText"], fontName=regular, fontSize=8, leading=11))
    styles.add(ParagraphStyle(name="ReportItalic", parent=styles["Italic"], fontName=regular, fontSize=8, leading=11))
    styles.add(ParagraphStyle(name="ExperimentHeading", parent=styles["Heading3"], fontName=bold,
                              textColor=colors.HexColor("#52606a"), fontSize=9, leading=12))

    story: list[Any] = [
        Paragraph(_escape(_tr(language, "title")), styles["ReportTitle"]),
        Paragraph(f"{_escape(experiment.name)} · TrajectoryLab {__version__}", styles["ExperimentHeading"]),
        Paragraph(
            _escape(_tr(language, "generated") + ": " + datetime.now(timezone.utc).isoformat(timespec="seconds")),
            styles["ReportBody"],
        ),
        Spacer(1, 3 * mm),
    ]

    payload = experiment.model_dump(mode="json")
    parameter_rows = [[_tr(language, "parameter"), _tr(language, "value")]]
    for key in (
        "name", "mass", "diameter", "initial_position", "initial_velocity", "duration",
        "time_step", "stop_at_ground", "gravity", "wind_velocity", "atmosphere", "method", "rtol", "atol", "seed",
    ):
        value = payload.get(key)
        if isinstance(value, dict):
            value = json_safe_mapping(value)
        label = _PARAMETER_LABELS.get(key, (key.replace("_", " ").title(), key.replace("_", " ").title()))
        parameter_rows.append([label[0] if language == "ru" else label[1] if language == "en" else f"{label[0]} / {label[1]}", _format_quantity(value)])
    story.extend([
        Paragraph(_tr(language, "parameters"), styles["SectionHeader"]),
        _styled_table(parameter_rows, [48 * mm, 122 * mm], regular, bold, mono),
    ])

    provenance = trajectory.provenance
    model = provenance.get("drag_model", {})
    model_rows = [
        [_tr(language, "field"), _tr(language, "value")],
        [_tr(language, "model"), str(model.get("name", "unknown"))],
        [_tr(language, "model_id"), str(model.get("id", "unknown"))],
        [_tr(language, "version"), str(model.get("version", "unknown"))],
        [_tr(language, "author"), str(model.get("author", "unknown"))],
        [_tr(language, "source"), str(model.get("source", "unknown"))],
        [_tr(language, "geometry"), str(model.get("geometry", "sphere"))],
        [_tr(language, "validity"), str(model.get("validity", {}))],
        [_tr(language, "model_hash"), str(provenance.get("drag_model_sha256", "n/a"))],
    ]
    if model.get("file_sha256"):
        model_rows.append([_tr(language, "source_hash"), str(model["file_sha256"])])
    story.extend([
        Paragraph(_tr(language, "drag"), styles["SectionHeader"]),
        _styled_table(model_rows, [48 * mm, 122 * mm], regular, bold, mono),
    ])

    labels = {key: _tr(language, key) for key in (
        "result", "samples", "elapsed", "range", "height", "apogee_time", "max_speed", "final_speed",
        "max_mach", "max_re", "energy", "impact", "trajectory_hash",
    )}
    results = [
        [labels["result"], _tr(language, "value")],
        [labels["samples"], str(trajectory.time_s.size)],
        [labels["elapsed"], f"{trajectory.time_s[-1]:.9g} s"],
        [labels["range"], f"{trajectory.range_m:.9g} m"],
        [labels["height"], f"{trajectory.maximum_height_m:.9g} m"],
        [labels["apogee_time"], f"{trajectory.maximum_height_time_s:.9g} s"],
        [labels["max_speed"], f"{trajectory.speed_m_s.max():.9g} m/s"],
        [labels["final_speed"], f"{trajectory.speed_m_s[-1]:.9g} m/s"],
        [labels["max_mach"], f"{trajectory.mach.max():.9g}"],
        [labels["max_re"], f"{trajectory.reynolds.max():.9g}"],
        [labels["energy"], f"{trajectory.kinetic_energy_j[-1]:.9g} J"],
        [labels["impact"], _tr(language, "not_reached") if trajectory.impact_time_s is None else f"{trajectory.impact_time_s:.9g} s"],
        [labels["trajectory_hash"], trajectory.checksum_sha256],
    ]
    story.extend([
        Paragraph(_tr(language, "method_results"), styles["SectionHeader"]),
        _styled_table(results, [48 * mm, 122 * mm], regular, bold, mono),
    ])

    provenance_rows = [[_tr(language, "provenance"), _tr(language, "value")]]
    for key in (
        "trajectory_lab_version", "python_version", "numpy_version", "scipy_version",
        "pint_version", "platform", "method", "step_s", "rtol", "atol",
        "trajectory_checksum_quantization", "seed", "stop_at_ground", "termination_reason",
    ):
        provenance_rows.append([key.replace("_", " ").title(), str(provenance.get(key, "n/a"))])
    story.extend([
        Paragraph(_tr(language, "provenance"), styles["SectionHeader"]),
        _styled_table(provenance_rows, [48 * mm, 122 * mm], regular, bold, mono),
        Paragraph(_tr(language, "plots"), styles["SectionHeader"]),
        XYPlot(trajectory.time_s, trajectory.position_m[:, 1], _tr(language, "height_plot"), _tr(language, "time"), _tr(language, "height_axis")),
        Spacer(1, 3 * mm),
        XYPlot(trajectory.time_s, trajectory.speed_m_s, _tr(language, "speed_plot"), _tr(language, "time"), _tr(language, "speed_axis")),
    ])

    if trajectory.warnings:
        story.append(Paragraph(_tr(language, "warnings"), styles["SectionHeader"]))
        for warning in trajectory.warnings:
            story.append(Paragraph("• " + _escape(warning), styles["ReportBody"]))
    story.extend([
        Spacer(1, 4 * mm),
        Paragraph(_escape(_tr(language, "limitation")), styles["ReportItalic"]),
    ])

    document = SimpleDocTemplate(
        str(target), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm, title=f"TrajectoryLab — {experiment.name}",
        author="TrajectoryLab",
    )
    document.build(story, onFirstPage=lambda canvas, doc: _page_footer(canvas, doc, language),
                   onLaterPages=lambda canvas, doc: _page_footer(canvas, doc, language))
    return target


def json_safe_mapping(value: dict[str, Any]) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _styled_table(rows: list[list[str]], col_widths: list[float], regular: str, bold: str, mono: str) -> Table:
    cell_style = ParagraphStyle(
        name="ReportCell", fontName=regular, fontSize=7, leading=9,
        textColor=colors.HexColor("#263238"), splitLongWords=True,
    )
    header_style = ParagraphStyle(name="ReportCellHeader", parent=cell_style, fontName=bold)
    value_style = ParagraphStyle(name="ReportCellValue", parent=cell_style, fontName=mono)
    wrapped_rows = []
    for row_index, row in enumerate(rows):
        converted = []
        for col_index, cell in enumerate(row):
            style = header_style if row_index == 0 else (value_style if col_index == 1 else cell_style)
            converted.append(Paragraph(_escape(str(cell)), style))
        wrapped_rows.append(converted)
    table = Table(wrapped_rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0dce5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#382d34")),
        ("FONTNAME", (0, 0), (-1, 0), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("LEADING", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c7b7c0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _page_footer(canvas: Any, document: Any, language: str = "en") -> None:
    regular, _bold, _mono = _register_fonts()
    canvas.saveState()
    canvas.setFont(regular, 7)
    canvas.setFillColor(colors.HexColor("#607078"))
    canvas.drawString(18 * mm, 9 * mm, _tr(language, "footer"))
    canvas.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()
