"""Fit a frame sequence's common foreground box tightly inside a fixed canvas."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def parse_color(value: str) -> tuple[int, int, int]:
    value = value.removeprefix("#")
    if len(value) != 6:
        raise argparse.ArgumentTypeError("color must be a 6-digit hex value")
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("color must be a 6-digit hex value") from exc


def distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((left - right) ** 2 for left, right in zip(a, b)) ** 0.5


def foreground_box(
    image: Image.Image,
    key: tuple[int, int, int],
    tolerance: int,
) -> tuple[int, int, int, int] | None:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    points: list[tuple[int, int]] = []
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = pixels[x, y]
            is_key = distance((red, green, blue), key) <= tolerance
            if alpha and not is_key:
                points.append((x, y))
    if not points:
        return None
    left = min(x for x, _ in points)
    top = min(y for _, y in points)
    right = max(x for x, _ in points) + 1
    bottom = max(y for _, y in points) + 1
    return left, top, right, bottom


def expand_box(
    box: tuple[int, int, int, int],
    margin: int,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    return (
        max(0, left - margin),
        max(0, top - margin),
        min(width, right + margin),
        min(height, bottom + margin),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--canvas-size", type=int, default=640)
    parser.add_argument(
        "--margin",
        type=int,
        default=8,
        help="output pixels reserved around the common foreground box",
    )
    parser.add_argument("--key-color", type=parse_color, default=(0, 255, 0))
    parser.add_argument("--tolerance", type=int, default=48)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.canvas_size <= 0:
        raise SystemExit("--canvas-size must be positive")
    if args.margin < 0 or args.margin * 2 >= args.canvas_size:
        raise SystemExit("--margin must be non-negative and leave usable canvas space")

    frames = sorted(args.input_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit(f"no frame PNGs found in {args.input_dir}")
    if args.output_dir.exists() and not args.overwrite:
        existing = next(args.output_dir.glob("frame_*.png"), None)
        if existing:
            raise SystemExit(
                f"output directory is not empty: {args.output_dir}; use --overwrite to rerun"
            )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    images = [Image.open(path).convert("RGBA") for path in frames]
    boxes = [foreground_box(image, args.key_color, args.tolerance) for image in images]
    if any(box is None for box in boxes):
        missing = frames[next(index for index, box in enumerate(boxes) if box is None)]
        raise SystemExit(f"no foreground found in {missing}")

    left = min(box[0] for box in boxes if box is not None)
    top = min(box[1] for box in boxes if box is not None)
    right = max(box[2] for box in boxes if box is not None)
    bottom = max(box[3] for box in boxes if box is not None)
    source_box = expand_box(
        (left, top, right, bottom), args.margin, images[0].width, images[0].height
    )
    crop_width = source_box[2] - source_box[0]
    crop_height = source_box[3] - source_box[1]
    target_extent = args.canvas_size - args.margin * 2
    scale = min(target_extent / crop_width, target_extent / crop_height)
    resized_size = (
        max(1, round(crop_width * scale)),
        max(1, round(crop_height * scale)),
    )

    for source, image in zip(frames, images):
        crop = image.crop(source_box)
        resized = crop.resize(resized_size, Image.Resampling.NEAREST)
        canvas = Image.new("RGBA", (args.canvas_size, args.canvas_size), (*args.key_color, 255))
        position = (
            (args.canvas_size - resized.width) // 2,
            (args.canvas_size - resized.height) // 2,
        )
        canvas.alpha_composite(resized, position)
        canvas.convert("RGB").save(args.output_dir / source.name)

    print(
        f"frames={len(frames)} source_box={source_box} "
        f"scale={scale:.3f} fitted_canvas={args.canvas_size}x{args.canvas_size} "
        f"output={args.output_dir}"
    )


if __name__ == "__main__":
    main()
