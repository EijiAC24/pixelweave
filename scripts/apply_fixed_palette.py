"""Map every frame to one shared palette to prevent animation color flicker."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def parse_color(value: str) -> tuple[int, int, int]:
    value = value.strip().removeprefix("#")
    if len(value) != 6:
        raise argparse.ArgumentTypeError("color must be a 6-digit hex value")
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("color must be a 6-digit hex value") from exc


def parse_palette(value: str) -> list[tuple[int, int, int]]:
    colors = [parse_color(item) for item in value.split(",") if item.strip()]
    if not colors:
        raise argparse.ArgumentTypeError("palette must contain at least one color")
    if len(set(colors)) != len(colors):
        raise argparse.ArgumentTypeError("palette colors must be unique")
    return colors


def distance_sq(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum((left - right) ** 2 for left, right in zip(a, b))


def near_key(pixel: tuple[int, int, int], key: tuple[int, int, int], tolerance: int) -> bool:
    return distance_sq(pixel, key) <= tolerance**2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    palette_group = parser.add_mutually_exclusive_group(required=True)
    palette_group.add_argument("--palette", type=parse_palette)
    palette_group.add_argument("--palette-file", type=Path)
    parser.add_argument("--key-color", type=parse_color, default=(0, 255, 0))
    parser.add_argument("--tolerance", type=int, default=48)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

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

    if args.palette_file:
        args.palette = parse_palette(args.palette_file.read_text(encoding="utf-8"))
    palette = [color for color in args.palette if color != args.key_color]
    if not palette:
        raise SystemExit("palette must include at least one non-key color")

    for source in frames:
        image = Image.open(source).convert("RGBA")
        pixels = image.load()
        for y in range(image.height):
            for x in range(image.width):
                red, green, blue, alpha = pixels[x, y]
                if not alpha:
                    continue
                rgb = (red, green, blue)
                if near_key(rgb, args.key_color, args.tolerance):
                    pixels[x, y] = (*args.key_color, alpha)
                    continue
                mapped = min(palette, key=lambda color: distance_sq(rgb, color))
                pixels[x, y] = (*mapped, alpha)
        image.save(args.output_dir / source.name)

    print(
        f"frames={len(frames)} palette_colors={len(args.palette)} "
        f"output={args.output_dir}"
    )


if __name__ == "__main__":
    main()
