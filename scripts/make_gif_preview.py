"""Create a looping animated GIF from numbered transparent PNG frames."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--duration-ms", type=int, default=125)
    parser.add_argument("--scale", type=int, default=1)
    args = parser.parse_args()

    if args.duration_ms < 20 or args.scale < 1:
        raise SystemExit("--duration-ms must be at least 20 and --scale at least 1")
    paths = sorted(args.frames_dir.glob("frame_*.png"))
    if not paths:
        raise SystemExit(f"no frame PNGs found in {args.frames_dir}")

    frames = []
    for path in paths:
        with Image.open(path) as source:
            frame = source.convert("RGBA")
        if args.scale > 1:
            frame = frame.resize(
                (frame.width * args.scale, frame.height * args.scale),
                Image.Resampling.NEAREST,
            )
        frames.append(frame)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=args.duration_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )
    print(f"frames={len(frames)} duration_ms={args.duration_ms} output={args.output}")


if __name__ == "__main__":
    main()
