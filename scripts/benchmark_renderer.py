#!/usr/bin/env python3
"""Benchmark riproducibile del renderer QPainter di MagicScribe.

Non impone una soglia CI: produce misure osservazionali. I casi ``*_history``
misurano la rasterizzazione completa della cronologia (fatta solo quando la
cronologia cambia); ``live_frame_*`` misura un frame durante il disegno, che
compone il layer in cache e il solo tratto in corso.
"""

from __future__ import annotations

# The repository root must be inserted before importing project modules.
# ruff: noqa: E402

import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter

from config.settings import Settings
from core.app_controller import AppController
from core.models import Point, Stroke, ToolType
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.drawing_engine import DrawingEngine
from ui.quick.drawing_canvas import DrawingCanvas


def _make_strokes(
    tool_type: ToolType,
    stroke_count: int,
    points_per_stroke: int,
) -> list[Stroke]:
    strokes: list[Stroke] = []
    for stroke_index in range(stroke_count):
        points = [
            Point(
                x=float((point_index * 7 + stroke_index * 23) % 1920),
                y=float((point_index * 5 + stroke_index * 31) % 1080),
            )
            for point_index in range(points_per_stroke)
        ]
        strokes.append(
            Stroke(
                tool_type=tool_type,
                points=points,
                color="#ff6600",
                size=5.0,
            )
        )
    return strokes


def _measure_case(
    name: str,
    strokes: list[Stroke],
    repetitions: int,
) -> dict[str, float | int | str]:
    image = QImage(1920, 1080, QImage.Format.Format_ARGB32_Premultiplied)

    # Warm-up: inizializza i percorsi Qt prima delle misure registrate.
    image.fill(Qt.GlobalColor.transparent)
    warmup = QPainter(image)
    try:
        DrawingEngine.render_strokes(warmup, strokes)
    finally:
        warmup.end()

    timings_ms: list[float] = []
    for _ in range(repetitions):
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        start = time.perf_counter()
        try:
            DrawingEngine.render_strokes(painter, strokes)
        finally:
            painter.end()
        timings_ms.append((time.perf_counter() - start) * 1000.0)

    return {
        "name": name,
        "strokes": len(strokes),
        "points": sum(len(stroke.points) for stroke in strokes),
        "repetitions": repetitions,
        "mean_ms": round(statistics.fmean(timings_ms), 3),
        "median_ms": round(statistics.median(timings_ms), 3),
        "min_ms": round(min(timings_ms), 3),
        "max_ms": round(max(timings_ms), 3),
    }


def _measure_live_frame(
    name: str,
    history: list[Stroke],
    repetitions: int,
) -> dict[str, float | int | str]:
    """Costo di un frame mentre si disegna sopra una cronologia gia' in cache."""
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(path=Path(tmp) / "benchmark.json")
        controller = AppController(settings)
        for stroke in history:
            controller.finalize_stroke(stroke)
        adapter = DrawingAdapter(controller)
        canvas = DrawingCanvas(adapter)
        canvas.setWidth(1920)
        canvas.setHeight(1080)
        controller.toggle_drawing()

        image = QImage(1920, 1080, QImage.Format.Format_ARGB32_Premultiplied)
        canvas._begin_stroke(QPointF(100, 100))
        for index in range(200):
            canvas._extend_stroke(QPointF(100 + index * 3, 100 + (index % 40)))

        timings_ms: list[float] = []
        for frame in range(repetitions + 1):
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            start = time.perf_counter()
            try:
                canvas.paint(painter)
            finally:
                painter.end()
            if frame:  # il primo frame costruisce il layer in cache
                timings_ms.append((time.perf_counter() - start) * 1000.0)

        canvas.deleteLater()
        adapter.close()
        settings.close()

    return {
        "name": name,
        "strokes": len(history),
        "points": sum(len(stroke.points) for stroke in history),
        "repetitions": repetitions,
        "mean_ms": round(statistics.fmean(timings_ms), 3),
        "median_ms": round(statistics.median(timings_ms), 3),
        "min_ms": round(min(timings_ms), 3),
        "max_ms": round(max(timings_ms), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Esegue il workload breve usato come osservazione in CI.",
    )
    args = parser.parse_args()
    app = QGuiApplication.instance() or QGuiApplication([])

    if args.quick:
        repetitions = 3
        pen_strokes = _make_strokes(ToolType.PEN, 20, 250)
        smooth_strokes = _make_strokes(ToolType.SMOOTH, 10, 250)
    else:
        repetitions = 5
        pen_strokes = _make_strokes(ToolType.PEN, 50, 1000)
        smooth_strokes = _make_strokes(ToolType.SMOOTH, 25, 1000)

    results = [
        _measure_case("pen_history", pen_strokes, repetitions),
        _measure_case("smooth_history", smooth_strokes, repetitions),
        _measure_live_frame("live_frame_pen_history", pen_strokes, repetitions),
        _measure_live_frame("live_frame_smooth_history", smooth_strokes, repetitions),
    ]
    print(json.dumps({"renderer_benchmark": results}, sort_keys=True))
    app.processEvents()


if __name__ == "__main__":
    main()
