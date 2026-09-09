#!/usr/bin/env python3
"""Benchmark riproducibile del renderer QPainter di MagicScribe.

Non impone una soglia CI: produce misure osservazionali utili a decidere se
introdurre una cache dei tratti committed, evitando ottimizzazioni speculative.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import time

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

from core.models import Point, Stroke, ToolType
from ui.drawing_engine import DrawingEngine


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Esegue il workload breve usato come osservazione in CI.",
    )
    args = parser.parse_args()

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
    ]
    print(json.dumps({"renderer_benchmark": results}, sort_keys=True))


if __name__ == "__main__":
    main()
