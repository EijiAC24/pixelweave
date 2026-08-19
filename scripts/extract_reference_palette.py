"""Extract one shared foreground palette from a reference image."""

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


def distance_sq(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum((left - right) ** 2 for left, right in zip(a, b))


def is_key(pixel: tuple[int, int, int], key: tuple[int, int, int], tolerance: int) -> bool:
    dominant = max(range(3), key=lambda index: key[index])
    other_channels = [index for index in range(3) if index != dominant]
    chroma_like = (
        key[dominant] > max(key[index] for index in other_channels) + 30
        and pixel[dominant] >= 48
        and pixel[dominant] > max(pixel[index] for index in other_channels) + 20
    )
    return distance_sq(pixel, key) <= tolerance**2 or chroma_like


def coarse_color(value: int, step: int) -> int:
    return min(255, round(value / step) * step)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--colors", type=int, default=16, help="total palette size including key color")
    parser.add_argument("--key-color", type=parse_color, default=(0, 255, 0))
    parser.add_argument("--tolerance", type=int, default=48)
    parser.add_argument("--max-samples", type=int, default=100_000)
    parser.add_argument("--quantize-step", type=int, default=16)
    args = parser.parse_args()

    if args.colors < 2:
        raise SystemExit("--colors must be at least 2")
    if args.max_samples < 1:
        raise SystemExit("--max-samples must be positive")
    if args.quantize_step < 1:
        raise SystemExit("--quantize-step must be positive")

    image = Image.open(args.reference).convert("RGBA")
    samples = [
        (red, green, blue)
        for red, green, blue, alpha in image.getdata()
        if alpha and not is_key((red, green, blue), args.key_color, args.tolerance)
    ]
    if not samples:
        raise SystemExit(f"no foreground pixels found in {args.reference}")
    if len(samples) > args.max_samples:
        stride = max(1, len(samples) // args.max_samples)
        samples = samples[::stride][: args.max_samples]

    coarse_samples = [
        tuple(coarse_color(channel, args.quantize_step) for channel in pixel)
        for pixel in samples
    ]
    sample_image = Image.new("RGB", (len(coarse_samples), 1))
    sample_image.putdata(coarse_samples)
    quantized = sample_image.quantize(
        colors=args.colors - 1,
        method=Image.Quantize.MAXCOVERAGE,
        dither=Image.Dither.NONE,
    )
    palette = quantized.getpalette()
    color_counts = quantized.getcolors(maxcolors=args.colors - 1)
    if not color_counts:
        raise SystemExit("could not extract a palette")

    extracted: list[tuple[int, int, int]] = []
    for _, index in sorted(color_counts, reverse=True):
        color = tuple(palette[index * 3 : index * 3 + 3])
        if color not in extracted and color != args.key_color:
            extracted.append(color)  # type: ignore[arg-type]

    colors = [args.key_color, *extracted]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(",".join(f"{red:02x}{green:02x}{blue:02x}" for red, green, blue in colors) + "\n", encoding="utf-8")
    print(
        f"reference={args.reference} foreground_samples={len(samples)} "
        f"palette_colors={len(colors)} output={args.output}"
    )


if __name__ == "__main__":
    main()
