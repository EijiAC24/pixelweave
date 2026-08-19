"""Create a labeled, nearest-neighbor contact sheet for frame-by-frame QC."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def parse_color(value: str) -> tuple[int, int, int]:
    value = value.strip().removeprefix("#")
    if len(value) != 6:
        raise argparse.ArgumentTypeError("color must be a 6-digit hex value")
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("color must be a 6-digit hex value") from exc


def distance_sq(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return sum((a - b) ** 2 for a, b in zip(left, right))


def remove_key(
    image: Image.Image, key: tuple[int, int, int], tolerance: int
) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = pixels[x, y]
            if not alpha or distance_sq((red, green, blue), key) <= tolerance**2:
                pixels[x, y] = (0, 0, 0, 0)
    return rgba


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--cell-size", type=int, default=192)
    parser.add_argument("--padding", type=int, default=8)
    parser.add_argument("--label-height", type=int, default=18)
    parser.add_argument("--background", type=parse_color, default=(22, 27, 30))
    parser.add_argument("--key-color", type=parse_color, default=(0, 255, 0))
    parser.add_argument("--tolerance", type=int, default=48)
    args = parser.parse_args()

    if args.columns < 1 or args.cell_size < 1:
        raise SystemExit("--columns and --cell-size must be at least 1")
    frames = sorted(args.frames_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit(f"no frame PNGs found in {args.frames_dir}")

    tile_width = args.cell_size + args.padding * 2
    tile_height = args.cell_size + args.label_height + args.padding * 2
    rows = (len(frames) + args.columns - 1) // args.columns
    sheet = Image.new(
        "RGB", (args.columns * tile_width, rows * tile_height), args.background
    )
    draw = ImageDraw.Draw(sheet)

    for index, path in enumerate(frames):
        with Image.open(path) as source:
            image = remove_key(source, args.key_color, args.tolerance)
        scale = min(args.cell_size / image.width, args.cell_size / image.height)
        display_size = (
            max(1, round(image.width * scale)),
            max(1, round(image.height * scale)),
        )
        image = image.resize(display_size, Image.Resampling.NEAREST)
        tile_x = (index % args.columns) * tile_width
        tile_y = (index // args.columns) * tile_height
        draw.text(
            (tile_x + args.padding, tile_y + args.padding),
            path.stem,
            fill=(246, 240, 224),
        )
        image_x = tile_x + args.padding + (args.cell_size - image.width) // 2
        image_y = tile_y + args.padding + args.label_height + (args.cell_size - image.height) // 2
        sheet.paste(image, (image_x, image_y), image)
        draw.rectangle(
            (
                tile_x + args.padding - 1,
                tile_y + args.padding + args.label_height - 1,
                tile_x + args.padding + args.cell_size,
                tile_y + args.padding + args.label_height + args.cell_size,
            ),
            outline=(80, 91, 96),
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(f"frames={len(frames)} grid={args.columns}x{rows} output={args.output}")


if __name__ == "__main__":
    main()
