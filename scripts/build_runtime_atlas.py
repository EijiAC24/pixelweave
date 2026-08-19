"""Build a multi-move atlas with one global scale and foot anchors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def find_frames(move_dir: Path) -> list[Path]:
    frames = sorted(move_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit(f"no frame PNGs found in {move_dir}")
    return frames


def sprite_stats(
    image: Image.Image, ankle_ratio: float
) -> tuple[tuple[int, int, int, int], int, float]:
    alpha = image.convert("RGBA")
    points = [
        (x, y)
        for y in range(alpha.height)
        for x in range(alpha.width)
        if alpha.getpixel((x, y))[3] > 0
    ]
    if not points:
        raise SystemExit("a runtime-atlas frame has no opaque pixels")
    left = min(x for x, _ in points)
    top = min(y for _, y in points)
    right = max(x for x, _ in points) + 1
    bottom = max(y for _, y in points) + 1
    ankle_top = bottom - max(1, round((bottom - top) * ankle_ratio))
    ankle_points = [x for x, y in points if y >= ankle_top]
    ankle_x = sum(ankle_points) / len(ankle_points)
    return (left, top, right, bottom), bottom - 1, ankle_x


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sprites_root", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument(
        "--moves", required=True, help="comma-separated move directory names"
    )
    parser.add_argument(
        "--ref", help="reference move for global scale; defaults to the first move"
    )
    parser.add_argument(
        "--height", type=int, default=64, help="reference pose height in output pixels"
    )
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--ankle-ratio", type=float, default=0.22)
    parser.add_argument("--frames-output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    moves = [name.strip() for name in args.moves.split(",") if name.strip()]
    if not moves:
        raise SystemExit("--moves must contain at least one move")
    if args.height <= 0 or args.ankle_ratio <= 0 or args.ankle_ratio > 1:
        raise SystemExit(
            "--height must be positive and --ankle-ratio must be in (0, 1]"
        )
    if args.fps <= 0:
        raise SystemExit("--fps must be positive")

    move_frames = {move: find_frames(args.sprites_root / move) for move in moves}
    reference_move = args.ref or moves[0]
    if reference_move not in move_frames:
        raise SystemExit(f"reference move not listed in --moves: {reference_move}")

    reference_image = Image.open(move_frames[reference_move][0]).convert("RGBA")
    reference_bbox, reference_baseline, reference_ankle = sprite_stats(
        reference_image, args.ankle_ratio
    )
    reference_height = reference_bbox[3] - reference_bbox[1]
    scale = args.height / reference_height
    frames_output = (
        args.frames_output
        or args.output_json.parent / f"{args.output_json.stem}_frames"
    )
    if frames_output.exists() and not args.overwrite:
        raise SystemExit(
            f"frames output already exists: {frames_output}; pass --overwrite to replace it"
        )
    frames_output.mkdir(parents=True, exist_ok=True)
    duration_ms = args.duration_ms or round(1000 / args.fps)

    atlas_moves = {}
    for move, paths in move_frames.items():
        move_output = frames_output / move
        move_output.mkdir(parents=True, exist_ok=True)
        atlas_frames = []
        for index, source_path in enumerate(paths):
            image = Image.open(source_path).convert("RGBA")
            bbox, baseline, ankle = sprite_stats(image, args.ankle_ratio)
            crop = image.crop(bbox)
            size = (
                max(1, round(crop.width * scale)),
                max(1, round(crop.height * scale)),
            )
            resized = crop.resize(size, Image.Resampling.NEAREST)
            output_path = move_output / f"frame_{index:04d}.png"
            resized.save(output_path)
            atlas_frames.append(
                {
                    "file": output_path.relative_to(args.output_json.parent).as_posix(),
                    "source_file": source_path.name,
                    "w": resized.width,
                    "h": resized.height,
                    "footOffset": round((baseline - reference_baseline) * scale),
                    "anchorOffset": round((ankle - bbox[0]) * scale),
                    "driftX": round((ankle - reference_ankle) * scale),
                    "durationMs": duration_ms,
                }
            )
        atlas_moves[move] = atlas_frames
        heights = [frame["h"] for frame in atlas_frames]
        print(
            f"{move}: frames={len(atlas_frames)} height={min(heights)}-{max(heights)}px"
        )

    atlas = {
        "version": 1,
        "reference_move": reference_move,
        "reference_height_px": reference_height,
        "target_height_px": args.height,
        "global_scale": round(scale, 6),
        "fps": args.fps,
        "frame_duration_ms": duration_ms,
        "anchor": "ankle-region-centroid",
        "moves": atlas_moves,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(atlas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"atlas={args.output_json} scale={scale:.4f} reference={reference_move}")


if __name__ == "__main__":
    main()
