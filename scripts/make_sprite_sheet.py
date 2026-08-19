"""Pack numbered frame PNGs into a uniformly anchored sprite sheet."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_sheet", type=Path)
    parser.add_argument("--columns", type=int, default=13)
    parser.add_argument("--background", choices=("first", "green", "transparent"), default="first")
    parser.add_argument("--anchor", choices=("bottom-center", "center"), default="bottom-center")
    parser.add_argument("--preview-scale", type=int, default=4)
    parser.add_argument("--metadata", action="store_true")
    args = parser.parse_args()

    if args.columns < 1:
        raise SystemExit("--columns must be at least 1")
    frames = sorted(args.input_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit(f"no frame PNGs found in {args.input_dir}")
    images = [Image.open(path).convert("RGBA") for path in frames]
    cell_width = max(image.width for image in images)
    cell_height = max(image.height for image in images)
    rows = math.ceil(len(images) / args.columns)

    if args.background == "green":
        background = (0, 255, 0, 255)
    elif args.background == "transparent":
        background = (0, 0, 0, 0)
    else:
        background = images[0].getpixel((0, 0))
    sheet = Image.new("RGBA", (args.columns * cell_width, rows * cell_height), background)

    for index, image in enumerate(images):
        if args.anchor == "bottom-center":
            x = (index % args.columns) * cell_width + (cell_width - image.width) // 2
            y = (index // args.columns) * cell_height + cell_height - image.height
        else:
            x = (index % args.columns) * cell_width + (cell_width - image.width) // 2
            y = (index // args.columns) * cell_height + (cell_height - image.height) // 2
        sheet.alpha_composite(image, (x, y))

    args.output_sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output_sheet)
    if args.preview_scale > 1:
        preview = args.output_sheet.with_name(args.output_sheet.stem + "_preview.png")
        sheet.resize(
            (sheet.width * args.preview_scale, sheet.height * args.preview_scale),
            Image.Resampling.NEAREST,
        ).save(preview)

    if args.metadata:
        manifest = args.output_sheet.with_suffix(".json")
        manifest.write_text(
            json.dumps(
                {
                    "frames": len(images),
                    "columns": args.columns,
                    "rows": rows,
                    "cell_size": [cell_width, cell_height],
                    "sheet_size": list(sheet.size),
                    "background": args.background,
                    "anchor": args.anchor,
                    "frame_files": [path.name for path in frames],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(
        f"frames={len(images)} cell={cell_width}x{cell_height} "
        f"grid={args.columns}x{rows} sheet={args.output_sheet}"
    )


if __name__ == "__main__":
    main()
