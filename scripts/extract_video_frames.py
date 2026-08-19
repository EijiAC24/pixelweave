"""Extract every video frame as a numbered PNG sequence."""

from __future__ import annotations

import argparse
from pathlib import Path

import av


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_video", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.input_video.is_file():
        raise SystemExit(f"input video not found: {args.input_video}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(args.output_dir.glob("frame_*.png"))
    if existing and not args.overwrite:
        raise SystemExit(
            f"output directory already contains {len(existing)} frames; "
            "use a new directory or pass --overwrite"
        )
    if args.overwrite:
        for path in existing:
            path.unlink()

    with av.open(str(args.input_video)) as container:
        stream = next((item for item in container.streams if item.type == "video"), None)
        if stream is None:
            raise SystemExit("video stream not found")
        width = stream.codec_context.width
        height = stream.codec_context.height
        fps = float(stream.average_rate) if stream.average_rate else None
        count = 0
        for frame in container.decode(video=stream.index):
            frame.to_image().convert("RGB").save(
                args.output_dir / f"frame_{count:04d}.png"
            )
            count += 1

    if args.expected_count is not None and count != args.expected_count:
        raise SystemExit(
            f"frame count mismatch: expected {args.expected_count}, got {count}"
        )
    duration = count / fps if fps else None
    print(
        f"frames={count} size={width}x{height} fps={fps or 'unknown'} "
        f"duration_sec={duration or 'unknown'} output={args.output_dir}"
    )


if __name__ == "__main__":
    main()
