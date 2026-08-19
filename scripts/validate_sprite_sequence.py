"""Run non-destructive quality gates over the actual output frames."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops

from analyze_sprite_sequence import frame_stats, is_key, parse_color


def exact_equal(left: Image.Image, right: Image.Image) -> bool:
    if left.size != right.size or left.mode != right.mode:
        return False
    return ImageChops.difference(left.convert("RGB"), right.convert("RGB")).getbbox() is None


def opaque_color_count(
    image: Image.Image, key: tuple[int, int, int], tolerance: int
) -> int:
    colors: set[tuple[int, int, int]] = set()
    for red, green, blue, alpha in image.convert("RGBA").getdata():
        if alpha and not is_key((red, green, blue), key, tolerance):
            colors.add((red, green, blue))
    return len(colors)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames_dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--key-color", type=parse_color, default=(0, 255, 0))
    parser.add_argument("--tolerance", type=int, default=48)
    parser.add_argument("--max-baseline-drift", type=int, default=24)
    parser.add_argument("--max-bbox-drift", type=int, default=16)
    parser.add_argument(
        "--allow-variable-canvas",
        action="store_true",
        help="allow snapped frames to have different source sizes; the sheet still normalizes cells",
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    frames = sorted(args.frames_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit(f"no frame PNGs found in {args.frames_dir}")

    images: list[Image.Image] = []
    metrics = []
    errors: list[str] = []
    color_counts: list[int] = []
    for path in frames:
        image = Image.open(path).convert("RGBA")
        images.append(image)
        try:
            metrics.append(frame_stats(image, args.key_color, args.tolerance))
        except SystemExit:
            errors.append(f"empty foreground: {path.name}")
        color_counts.append(opaque_color_count(image, args.key_color, args.tolerance))

    sizes = sorted({tuple(image.size) for image in images})
    adjacent_duplicates = [
        index
        for index, (left, right) in enumerate(zip(images, images[1:]))
        if exact_equal(left, right)
    ]
    widths = [metric["width"] for metric in metrics]
    heights = [metric["height"] for metric in metrics]
    baselines = [metric["baseline"] for metric in metrics]
    bbox_drift = max(
        max(widths) - min(widths) if widths else 0,
        max(heights) - min(heights) if heights else 0,
    )
    baseline_drift = max(baselines) - min(baselines) if baselines else 0
    canvas_gate = len(sizes) == 1 or args.allow_variable_canvas
    gates = {
        "expected_frame_count": (
            args.expected_count is None or len(frames) == args.expected_count
        ),
        "consistent_canvas": canvas_gate,
        "non_empty_foreground": not errors,
        "bbox_drift_within_limit": bbox_drift <= args.max_bbox_drift,
        "baseline_drift_within_limit": baseline_drift <= args.max_baseline_drift,
    }
    warnings = []
    if len(sizes) > 1 and args.allow_variable_canvas:
        warnings.append("variable snapped canvas sizes allowed; verify the sheet cell manifest")
    if adjacent_duplicates:
        warnings.append(f"adjacent duplicate frames at indices {adjacent_duplicates}")
    if color_counts and min(color_counts) != max(color_counts):
        warnings.append(
            f"opaque color counts vary from {min(color_counts)} to {max(color_counts)}"
        )
    warnings.extend(errors)
    report = {
        "frames_dir": str(args.frames_dir),
        "frame_count": len(frames),
        "expected_count": args.expected_count,
        "canvas_sizes": [list(size) for size in sizes],
        "adjacent_duplicate_indices": adjacent_duplicates,
        "opaque_color_count": {
            "min": min(color_counts) if color_counts else 0,
            "max": max(color_counts) if color_counts else 0,
        },
        "bbox_drift_px": bbox_drift,
        "baseline_drift_px": baseline_drift,
        "gates": gates,
        "quality_gate": all(gates.values()),
        "warnings": warnings,
        "frames": [
            {"file": path.name, **metric, "opaque_color_count": color_count}
            for path, metric, color_count in zip(frames, metrics, color_counts)
        ],
    }
    output = args.output or args.frames_dir / "quality_gate.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {key: report[key] for key in ("quality_gate", "gates", "warnings")},
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"report={output}")
    if args.strict and not report["quality_gate"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
