"""Measure sprite-frame stability and write a compact numeric QC report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def parse_color(value: str) -> tuple[int, int, int]:
    value = value.strip().removeprefix("#")
    if len(value) != 6:
        raise argparse.ArgumentTypeError("color must be a 6-digit hex value")
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("color must be a 6-digit hex value") from exc


def distance_sq(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum((left - right) ** 2 for left, right in zip(a, b))


def is_key(
    pixel: tuple[int, int, int], key: tuple[int, int, int], tolerance: int
) -> bool:
    return distance_sq(pixel, key) <= tolerance**2


def frame_stats(
    image: Image.Image,
    key: tuple[int, int, int],
    tolerance: int,
) -> dict[str, float | int | list[int]]:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    points: list[tuple[int, int]] = []
    key_pixels = 0
    transparent_pixels = 0
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = pixels[x, y]
            if not alpha:
                transparent_pixels += 1
                continue
            if is_key((red, green, blue), key, tolerance):
                key_pixels += 1
                continue
            points.append((x, y))

    total = rgba.width * rgba.height
    if not points:
        raise SystemExit(f"no foreground found in {image}")
    left = min(x for x, _ in points)
    top = min(y for _, y in points)
    right = max(x for x, _ in points) + 1
    bottom = max(y for _, y in points) + 1
    foreground = len(points)
    return {
        "bbox": [left, top, right, bottom],
        "baseline": bottom - 1,
        "top": top,
        "cx": round(sum(x for x, _ in points) / foreground, 2),
        "height": bottom - top,
        "width": right - left,
        "coverage": round(foreground / total, 6),
        "key_fraction": round(key_pixels / total, 6),
        "transparent_fraction": round(transparent_pixels / total, 6),
    }


def preview(
    image: Image.Image, key: tuple[int, int, int], tolerance: int
) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = []
    for red, green, blue, alpha in rgba.getdata():
        if not alpha or is_key((red, green, blue), key, tolerance):
            pixels.append((0, 0, 0))
        else:
            pixels.append((red, green, blue))
    flattened = Image.new("RGB", rgba.size)
    flattened.putdata(pixels)
    return flattened.resize((64, 64), Image.Resampling.BILINEAR)


def frame_difference(left: Image.Image, right: Image.Image) -> float:
    return sum(ImageStat.Stat(ImageChops.difference(left, right)).mean) / 3


def find_loop_seam(
    previews: list[Image.Image],
) -> dict[str, float | int] | None:
    total = len(previews)
    if total < 4:
        return None
    low = max(0, int(total * 0.2))
    high = min(total - 1, max(low + 1, int(total * 0.85)))
    min_gap = max(2, total // 12)
    max_gap = max(min_gap + 1, total // 2)
    best: tuple[float, int, int] | None = None
    for first in range(low, high):
        for last in range(first + min_gap, min(high, first + max_gap) + 1):
            difference = frame_difference(previews[first], previews[last])
            if best is None or difference < best[0]:
                best = (difference, first, last)
    if best is None:
        return None
    difference, first, last = best
    return {
        "start_index": first,
        "end_index": last,
        "difference": round(difference, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames_dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--key-color", type=parse_color, default=(0, 255, 0))
    parser.add_argument("--tolerance", type=int, default=48)
    args = parser.parse_args()

    frames = sorted(args.frames_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit(f"no frame PNGs found in {args.frames_dir}")
    images = [Image.open(path) for path in frames]
    metrics = [frame_stats(image, args.key_color, args.tolerance) for image in images]
    previews = [preview(image, args.key_color, args.tolerance) for image in images]
    baselines = [metric["baseline"] for metric in metrics]
    centers = [metric["cx"] for metric in metrics]
    heights = [metric["height"] for metric in metrics]
    summary = {
        "frame_count": len(frames),
        "baseline_drift_px": max(baselines) - min(baselines),
        "centroid_drift_px": round(max(centers) - min(centers), 2),
        "height_variance_px": max(heights) - min(heights),
        "first_vs_last_baseline_px": abs(baselines[0] - baselines[-1]),
        "first_last_difference": round(frame_difference(previews[0], previews[-1]), 3),
        "best_loop_seam": find_loop_seam(previews),
    }
    report = {
        "frames_dir": str(args.frames_dir),
        "key_color": "#%02x%02x%02x" % args.key_color,
        "tolerance": args.tolerance,
        "summary": summary,
        "frames": [
            {"file": path.name, **metric} for path, metric in zip(frames, metrics)
        ],
    }
    output = args.output or args.frames_dir / "sequence_qc.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"report={output}")


if __name__ == "__main__":
    main()
