"""Generate a cosine-similarity -> criterion-1 points graph.

This is a standalone script with no third-party dependencies.
It writes:
- CSV data points for the curve
- A self-contained HTML file with an SVG line chart

Usage:
    python scripts/plot_cosine_points_curve.py
    python scripts/plot_cosine_points_curve.py --min-useful 0.556 --max-useful 0.871 --power 0.645
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Iterable, List, Tuple


# Keep in sync with server/app/utils/calculate.py criterion-1 calibration.
DEFAULT_MIN_USEFUL = 0.556
DEFAULT_MAX_USEFUL = 0.871
DEFAULT_POWER = 0.645


def custom_round(value: float) -> int:
    decimal = value - int(value)
    if decimal >= 0.5:
        return int(value) + 1
    return int(value)


def similarity_to_points(
    similarity: float,
    min_useful: float,
    max_useful: float,
    power: float,
) -> Tuple[int, float, float]:
    normalized = (similarity - min_useful) / (max_useful - min_useful)
    normalized = max(0.0, min(1.0, normalized))
    transformed = normalized**power
    points = custom_round(transformed * 25)
    return max(0, min(25, points)), normalized, transformed


def generate_curve_rows(
    min_useful: float,
    max_useful: float,
    power: float,
    step: float,
) -> List[Tuple[float, int, float, float]]:
    rows: List[Tuple[float, int, float, float]] = []
    x = 0.0
    # Include 1.0 exactly by tolerance.
    while x <= 1.0000001:
        similarity = round(x, 4)
        points, normalized, transformed = similarity_to_points(
            similarity, min_useful, max_useful, power
        )
        rows.append((similarity, points, normalized, transformed))
        x += step
    return rows


def write_csv(output_path: Path, rows: Iterable[Tuple[float, int, float, float]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cosine_similarity", "points", "normalized", "transformed"])
        for similarity, points, normalized, transformed in rows:
            writer.writerow([f"{similarity:.4f}", points, f"{normalized:.6f}", f"{transformed:.6f}"])


def build_svg_polyline_points(rows: List[Tuple[float, int, float, float]]) -> str:
    width = 960
    height = 520
    left = 70
    right = 30
    top = 35
    bottom = 60
    plot_w = width - left - right
    plot_h = height - top - bottom

    def x_px(similarity: float) -> float:
        return left + similarity * plot_w

    def y_px(points: float) -> float:
        return top + (25 - points) / 25 * plot_h

    points_attr = " ".join(
        f"{x_px(similarity):.2f},{y_px(points):.2f}"
        for similarity, points, _, _ in rows
    )
    return points_attr


def build_html(
    rows: List[Tuple[float, int, float, float]],
    min_useful: float,
    max_useful: float,
    power: float,
) -> str:
    width = 960
    height = 520
    left = 70
    right = 30
    top = 35
    bottom = 60
    plot_w = width - left - right
    plot_h = height - top - bottom

    polyline_points = build_svg_polyline_points(rows)

    y_ticks = "\n".join(
        f'<line x1="{left}" y1="{top + (25 - y) / 25 * plot_h:.2f}" '
        f'x2="{width - right}" y2="{top + (25 - y) / 25 * plot_h:.2f}" '
        f'stroke="#e5e7eb" stroke-width="1" />\n'
        f'<text x="{left - 10}" y="{top + (25 - y) / 25 * plot_h + 4:.2f}" text-anchor="end" '
        f'font-size="12" fill="#374151">{y}</text>'
        for y in [0, 5, 10, 15, 20, 25]
    )

    x_ticks = "\n".join(
        f'<line x1="{left + x * plot_w:.2f}" y1="{top}" '
        f'x2="{left + x * plot_w:.2f}" y2="{height - bottom}" '
        f'stroke="#f3f4f6" stroke-width="1" />\n'
        f'<text x="{left + x * plot_w:.2f}" y="{height - bottom + 20}" text-anchor="middle" '
        f'font-size="12" fill="#374151">{x:.1f}</text>'
        for x in [i / 10 for i in range(11)]
    )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Cosine to Points Curve</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 24px; color: #111827; background: #f9fafb; }}
    .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; box-shadow: 0 6px 18px rgba(0,0,0,0.06); }}
    h1 {{ margin: 0 0 8px; font-size: 20px; }}
    p {{ margin: 0 0 14px; color: #374151; }}
    .meta {{ font-family: Consolas, monospace; font-size: 13px; background: #f3f4f6; padding: 10px; border-radius: 8px; }}
    svg {{ width: 100%; max-width: {width}px; height: auto; display: block; margin-top: 10px; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>Criterion-1: Cosine Similarity -> Points</h1>
    <p>Current calibration curve used for course plan relevance scoring.</p>
    <div class=\"meta\">min_useful={min_useful}, max_useful={max_useful}, power={power}</div>
    <svg viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"Cosine similarity to points curve\">
      <rect x=\"0\" y=\"0\" width=\"{width}\" height=\"{height}\" fill=\"white\" />
      {y_ticks}
      {x_ticks}
      <line x1=\"{left}\" y1=\"{height - bottom}\" x2=\"{width - right}\" y2=\"{height - bottom}\" stroke=\"#9ca3af\" stroke-width=\"1.5\" />
      <line x1=\"{left}\" y1=\"{top}\" x2=\"{left}\" y2=\"{height - bottom}\" stroke=\"#9ca3af\" stroke-width=\"1.5\" />
      <polyline points=\"{polyline_points}\" fill=\"none\" stroke=\"#2563eb\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" />
      <text x=\"{left + plot_w / 2:.2f}\" y=\"{height - 14}\" text-anchor=\"middle\" font-size=\"13\" fill=\"#111827\">Cosine Similarity</text>
      <text x=\"18\" y=\"{top + plot_h / 2:.2f}\" text-anchor=\"middle\" font-size=\"13\" fill=\"#111827\" transform=\"rotate(-90, 18, {top + plot_h / 2:.2f})\">Points (0-25)</text>
    </svg>
  </div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot cosine-similarity to points curve.")
    parser.add_argument("--min-useful", type=float, default=DEFAULT_MIN_USEFUL)
    parser.add_argument("--max-useful", type=float, default=DEFAULT_MAX_USEFUL)
    parser.add_argument("--power", type=float, default=DEFAULT_POWER)
    parser.add_argument("--step", type=float, default=0.001)
    parser.add_argument(
        "--output-dir",
        default="cache/plots",
        help="Directory (relative to server/) to write output files.",
    )
    args = parser.parse_args()

    if not (0 < args.min_useful < args.max_useful <= 1):
        raise ValueError("Expected 0 < min-useful < max-useful <= 1")
    if args.power <= 0:
        raise ValueError("Expected power > 0")
    if args.step <= 0 or args.step > 1:
        raise ValueError("Expected step in (0, 1]")

    base_dir = Path(__file__).resolve().parents[1]  # server/
    output_dir = base_dir / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = generate_curve_rows(args.min_useful, args.max_useful, args.power, args.step)

    csv_path = output_dir / "cosine_points_curve.csv"
    html_path = output_dir / "cosine_points_curve.html"

    write_csv(csv_path, rows)
    html = build_html(rows, args.min_useful, args.max_useful, args.power)
    html_path.write_text(html, encoding="utf-8")

    print(f"Wrote CSV: {csv_path}")
    print(f"Wrote HTML: {html_path}")


if __name__ == "__main__":
    main()
