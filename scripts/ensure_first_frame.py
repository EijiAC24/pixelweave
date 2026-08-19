"""Verify frame 0 against the source image and optionally restore it exactly."""

from __future__ import annotations

import argparse
import shutil
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


def foreground_mae(
    reference: Image.Image,
    candidate: Image.Image,
    key: tuple[int, int, int],
    tolerance: int,
) -> tuple[float, int]:
    reference_rgb = reference.convert("RGB")
    candidate_rgb = candidate.convert("RGB")
    if reference_rgb.size != candidate_rgb.size:
        raise ValueError(
            f"size mismatch: reference={reference_rgb.size} candidate={candidate_rgb.size}"
        )

    total = 0
    count = 0
    for source, actual in zip(reference_rgb.getdata(), candidate_rgb.getdata()):
        if is_key(source, key, tolerance):
            continue
        total += sum(abs(left - right) for left, right in zip(source, actual)) / 3
        count += 1
    return (total / count if count else 0.0, count)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("frames_dir", type=Path)
    parser.add_argument("--frame-name", default="frame_0000.png")
    parser.add_argument("--threshold", type=float, default=12.0, help="foreground MAE threshold")
    parser.add_argument("--key-color", type=parse_color, default=(0, 255, 0))
    parser.add_argument("--tolerance", type=int, default=48)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument(
        "--pin-last",
        action="store_true",
        help="also verify the last frame and optionally restore it to the reference",
    )
    args = parser.parse_args()

    if not args.reference.is_file():
        raise SystemExit(f"reference not found: {args.reference}")
    frame_zero = args.frames_dir / args.frame_name
    if not frame_zero.is_file():
        raise SystemExit(f"frame 0 not found: {frame_zero}")

    frames = [frame_zero]
    if args.pin_last:
        all_frames = sorted(args.frames_dir.glob("frame_*.png"))
        if not all_frames:
            raise SystemExit(f"no frames found in {args.frames_dir}")
        if all_frames[-1] != frame_zero:
            frames.append(all_frames[-1])

    reference_image = Image.open(args.reference)
    for frame in frames:
        label = "frame 0" if frame == frame_zero else "last frame"
        try:
            mae, pixels = foreground_mae(
                reference_image,
                Image.open(frame),
                args.key_color,
                args.tolerance,
            )
        except ValueError as exc:
            if not args.replace:
                raise SystemExit(str(exc)) from exc
            mae, pixels = float("inf"), 0

        replaced = False
        if mae > args.threshold or not pixels:
            if args.replace:
                shutil.copyfile(args.reference, frame)
                replaced = True
            else:
                raise SystemExit(
                    f"{label} differs too much: mae={mae:.2f} "
                    f"threshold={args.threshold:.2f}"
                )

        print(
            f"{label}={frame} mae={mae:.2f} threshold={args.threshold:.2f} "
            f"foreground_pixels={pixels} replaced={replaced}"
        )


if __name__ == "__main__":
    main()
