from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from make_qc_contact_sheet import main as make_qc_main  # noqa: E402
from make_gif_preview import main as make_gif_main  # noqa: E402
from make_sprite_sheet import main as make_sheet_main  # noqa: E402
from select_frames import choose_arc_length, choose_indices  # noqa: E402
from validate_sprite_sequence import main as validate_main  # noqa: E402


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


def test_qc_contact_sheet_is_labeled_and_nearest_neighbor(tmp_path: Path, monkeypatch) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    for index in range(3):
        image = Image.new("RGBA", (8, 8), (0, 255, 0, 255))
        image.putpixel((index + 1, index + 1), (255, 0, 0, 255))
        image.save(frames / f"frame_{index:04d}.png")

    output = tmp_path / "qc.png"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "make_qc_contact_sheet.py",
            str(frames),
            str(output),
            "--columns",
            "2",
            "--cell-size",
            "16",
            "--padding",
            "2",
            "--label-height",
            "10",
        ],
    )
    make_qc_main()

    with Image.open(output) as sheet:
        assert sheet.size == (2 * (16 + 4), 2 * (16 + 10 + 4))
        assert sheet.mode == "RGB"


def test_quality_gate_reports_common_canvas_and_frame_count(tmp_path: Path, monkeypatch) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    for index in range(3):
        image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for x in range(2, 6):
            for y in range(2, 7):
                image.putpixel((x, y), (255, 0, 0, 255))
        image.save(frames / f"frame_{index:04d}.png")

    output = tmp_path / "quality_gate.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_sprite_sequence.py",
            str(frames),
            "--output",
            str(output),
            "--expected-count",
            "3",
        ],
    )
    validate_main()

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["quality_gate"] is True
    assert report["gates"]["consistent_canvas"] is True


def test_gif_preview_contains_all_frames_and_loops(tmp_path: Path, monkeypatch) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    for index in range(4):
        image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        image.putpixel((index, index), (255, 0, 0, 255))
        image.save(frames / f"frame_{index:04d}.png")

    output = tmp_path / "preview.gif"
    monkeypatch.setattr(
        sys,
        "argv",
        ["make_gif_preview.py", str(frames), str(output), "--duration-ms", "125"],
    )
    make_gif_main()

    with Image.open(output) as gif:
        assert gif.n_frames == 4
        assert gif.info["loop"] == 0
