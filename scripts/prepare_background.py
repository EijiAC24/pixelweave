"""Normalize or remove a flat chroma-key background from PNG frames."""

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


def normalize_green(im: Image.Image, key: tuple[int, int, int], tolerance: int) -> Image.Image:
    rgb = im.convert("RGB")
    pixels = list(rgb.getdata())
    output = []
    for pixel in pixels:
        near_green = (
            distance(pixel, key) <= tolerance
            and pixel[1] > pixel[0] + 30
            and pixel[1] > pixel[2] + 30
        )
        output.append(key if near_green else pixel)
    rgb.putdata(output)
    return rgb


def normalize_key(im: Image.Image, key: tuple[int, int, int], tolerance: int) -> Image.Image:
    rgb = im.convert("RGB")
    pixels = list(rgb.getdata())
    output = [key if distance(pixel, key) <= tolerance else pixel for pixel in pixels]
    rgb.putdata(output)
    return rgb


def remove_chroma(
    im: Image.Image,
    key: tuple[int, int, int],
    tolerance: int,
    softness: int,
    despill: bool,
) -> Image.Image:
    rgba = im.convert("RGBA")
    pixels = list(rgba.getdata())
    output = []
    soft_end = tolerance + max(softness, 0)
    for red, green, blue, alpha in pixels:
        d = distance((red, green, blue), key)
        if d <= tolerance:
            new_alpha = 0
        elif softness and d < soft_end:
            new_alpha = round(alpha * (d - tolerance) / softness)
        else:
            new_alpha = alpha
        if despill and new_alpha:
            green = min(green, max(red, blue) + 20)
        output.append((red, green, blue, new_alpha))
    rgba.putdata(output)
    return rgba


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--mode",
        choices=("normalize-green", "normalize-key", "remove-green", "remove-key"),
        required=True,
    )
    parser.add_argument("--key-color", type=parse_color, default=(0, 255, 0))
    parser.add_argument("--tolerance", type=int, default=48)
    parser.add_argument("--softness", type=int, default=16)
    parser.add_argument("--despill", action="store_true")
    args = parser.parse_args()

    frames = sorted(args.input_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit(f"no frame PNGs found in {args.input_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for source in frames:
        image = Image.open(source)
        if args.mode == "normalize-green":
            result = normalize_green(image, args.key_color, args.tolerance)
        elif args.mode == "normalize-key":
            result = normalize_key(image, args.key_color, args.tolerance)
        else:
            result = remove_chroma(
                image,
                args.key_color,
                args.tolerance,
                args.softness,
                args.despill,
            )
        result.save(args.output_dir / source.name)
    print(f"processed_frames={len(frames)} mode={args.mode} output={args.output_dir}")


if __name__ == "__main__":
    main()
