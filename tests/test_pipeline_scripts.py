from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from make_sprite_sheet import main as make_sheet_main  # noqa: E402
from select_frames import choose_arc_length, choose_indices  # noqa: E402


def test_frame_selection_keeps_endpoints() -> None:
    assert choose_indices(39, 13) == [0, 3, 6, 10, 13, 16, 19, 22, 25, 28, 32, 35, 38]
    selected = choose_arc_length([0.0] + [float(index) for index in range(1, 39)], 13)
    assert len(selected) == 13
    assert selected[0] == 0
    assert selected[-1] == 38


def test_sheet_manifest_uses_uniform_cells(tmp_path: Path, monkeypatch) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    for index, size in enumerate(((3, 5), (5, 4), (4, 6))):
        image = Image.new("RGBA", size, (0, 255, 0, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((1, 1, size[0] - 1, size[1] - 1), fill=(255, 0, 0, 255))
        image.save(frames / f"frame_{index:04d}.png")

    output = tmp_path / "sheet.png"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "make_sprite_sheet.py",
            str(frames),
            str(output),
            "--columns",
            "3",
            "--background",
            "transparent",
            "--metadata",
        ],
    )
    make_sheet_main()

    with Image.open(output) as sheet:
        assert sheet.size == (15, 6)
        assert sheet.mode == "RGBA"
    assert output.with_suffix(".json").exists()
