"""Select an exact number of frames using uniform or motion-aware sampling."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

FRAME_NAME = re.compile(r"^frame_(\d+)\.png$")


def find_frames(input_dir: Path) -> list[Path]:
    numbered_frames = []
    for path in input_dir.glob("frame_*.png"):
        match = FRAME_NAME.match(path.name)
        if not match:
            raise SystemExit(f"frame filename must match frame_NNNN.png: {path.name}")
        numbered_frames.append((int(match.group(1)), path))
    numbered_frames.sort()
    indices = [index for index, _ in numbered_frames]
    expected = list(range(len(numbered_frames)))
    if indices != expected:
        raise SystemExit(
            f"frame numbers must be contiguous from frame_0000.png; found {indices}"
        )
    frames = [path for _, path in numbered_frames]
    if not frames:
        raise SystemExit(f"no frame PNGs found in {input_dir}")
    return frames


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
    return distance_sq(pixel, key) <= tolerance**2


def validate_target(total: int, target: int) -> None:
    if target < 1:
        raise SystemExit("--target-count must be at least 1")
    if target > total:
        raise SystemExit(
            f"--target-count cannot exceed the native frame count ({total}); "
            "use interpolation in a separate post-process if more frames are needed"
        )


def choose_indices(total: int, target: int) -> list[int]:
    validate_target(total, target)
    if target == total:
        return list(range(total))
    if target == 1:
        return [0]
    return [round(index * (total - 1) / (target - 1)) for index in range(target)]


def make_preview(
    path: Path,
    key: tuple[int, int, int],
    tolerance: int,
    size: tuple[int, int] = (64, 64),
) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    pixels = []
    for red, green, blue, alpha in image.getdata():
        if not alpha or is_key((red, green, blue), key, tolerance):
            pixels.append((0, 0, 0))
        else:
            pixels.append((red, green, blue))
    preview = Image.new("RGB", image.size)
    preview.putdata(pixels)
    return preview.resize(size, Image.Resampling.BILINEAR)


def frame_difference(left: Image.Image, right: Image.Image) -> float:
    return sum(ImageStat.Stat(ImageChops.difference(left, right)).mean) / 3


def motion_energies(
    frames: list[Path], key: tuple[int, int, int], tolerance: int
) -> tuple[list[Image.Image], list[float]]:
    previews = [make_preview(path, key, tolerance) for path in frames]
    energies = [0.0]
    energies.extend(
        frame_difference(previous, current)
        for previous, current in zip(previews, previews[1:])
    )
    return previews, energies


def choose_arc_length(energies: list[float], target: int) -> list[int]:
    total = len(energies)
    if target >= total:
        return list(range(total))
    if target == 1:
        return [0]

    cumulative = []
    running = 0.0
    for energy in energies:
        running += energy
        cumulative.append(running)

    selected = {0, total - 1}
    for step in range(1, target - 1):
        desired = cumulative[-1] * step / (target - 1)
        candidates = sorted(
            range(1, total - 1),
            key=lambda index: abs(cumulative[index] - desired),
        )
        selected.add(next(index for index in candidates if index not in selected))
    return sorted(selected)


def choose_loop_indices(
    previews: list[Image.Image], target: int
) -> tuple[list[int], dict[str, float | int] | None]:
    total = len(previews)
    if target >= total:
        return list(range(total)), None

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
        return choose_indices(total, target), None

    difference, first, last = best
    selected = {
        first + round(step * (last - first) / target) for step in range(target)
    }
    for index in choose_indices(total, target):
        if len(selected) >= target:
            break
        selected.add(index)
    selected_indices = sorted(selected)[:target]
    return selected_indices, {
        "start_index": first,
        "end_index": last,
        "difference": round(difference, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--target-count", type=int, required=True)
    parser.add_argument(
        "--strategy",
        choices=("uniform", "arc-length", "loop"),
        default="uniform",
        help="uniform endpoints, cumulative motion arc-length, or best internal loop seam",
    )
    parser.add_argument("--key-color", type=parse_color, default=(0, 255, 0))
    parser.add_argument("--tolerance", type=int, default=48)
    parser.add_argument("--metadata", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        raise SystemExit(f"input directory not found: {args.input_dir}")
    frames = find_frames(args.input_dir)
    validate_target(len(frames), args.target_count)
    loop_seam = None
    if args.strategy == "uniform":
        selected_indices = choose_indices(len(frames), args.target_count)
    else:
        previews, energies = motion_energies(frames, args.key_color, args.tolerance)
        if args.strategy == "arc-length":
            selected_indices = choose_arc_length(energies, args.target_count)
        else:
            selected_indices, loop_seam = choose_loop_indices(previews, args.target_count)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    existing = list(args.output_dir.glob("frame_*.png"))
    if existing and not args.overwrite:
        raise SystemExit(
            f"output directory already contains frame PNGs: {args.output_dir}; "
            "pass --overwrite to replace them"
        )
    if args.overwrite:
        for path in existing:
            path.unlink()
        manifest = args.output_dir / "frame_selection.json"
        if manifest.exists():
            manifest.unlink()

    selected = []
    for output_index, source_index in enumerate(selected_indices):
        source = frames[source_index]
        destination = args.output_dir / f"frame_{output_index:04d}.png"
        shutil.copy2(source, destination)
        selected.append(
            {
                "output_file": destination.name,
                "source_file": source.name,
                "source_index": source_index,
            }
        )

    if args.metadata:
        manifest = args.output_dir / "frame_selection.json"
        manifest.write_text(
            json.dumps(
                {
                    "native_frames": len(frames),
                    "selected_frames": len(selected),
                    "strategy": args.strategy,
                    "loop_seam": loop_seam,
                    "frames": selected,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print(
        f"native_frames={len(frames)} selected_frames={len(selected)} "
        f"strategy={args.strategy} output={args.output_dir} indices={selected_indices}"
    )
    if loop_seam:
        print(f"loop_seam={loop_seam}")


if __name__ == "__main__":
    main()
