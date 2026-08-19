# Sprite quality gates

The pipeline now checks the frames that will actually ship, not only the preview video.

## Reports

`analyze_sprite_sequence.py` measures baseline drift, centroid drift, height variation, first/last difference, and a candidate loop seam. `validate_sprite_sequence.py` adds production-oriented gates:

- requested frame count;
- one common canvas size where the stage requires it;
- no empty foreground frame;
- common foreground width/height drift;
- baseline drift;
- exact adjacent duplicate frames;
- opaque color-count variation.

The validator writes `quality_gate.json`. It reports warnings without stopping the normal pipeline. Use `--strict` in CI when a failed gate should return exit code 2.

`make_qc_contact_sheet.py` writes `quality_contact_sheet.png`. It removes the configured chroma key for inspection, labels every frame, uses nearest-neighbor scaling (including enlargement of small snapped frames), and puts all frames in one visual grid. Inspect the first, middle, action extreme, and last frame individually when the contact sheet shows a problem.

The common-fit stage must have one shared canvas. Pixel Snapper may then emit tightly cropped frame PNGs with different source sizes; the sheet packer pads those into one common cell and records that cell in its JSON manifest. The normal post-process command passes `--allow-variable-canvas` for this expected final-stage behavior and emits a warning so the manifest still gets checked.

## Interpreting failures

- Large bbox drift usually means H3 changed the apparent character scale. Regenerate with a stricter safe rectangle or reduce motion amplitude; do not crop each frame independently.
- Baseline drift means the feet or ground contact move. Use a common bottom anchor and check the action prompt.
- Adjacent duplicates are a warning, not always a failure. A held pose can be intentional, but too many duplicates waste gameplay frames.
- Opaque color-count variation is a signal to inspect palette locking. For animation, map every frame to the same reference palette rather than quantizing each frame independently.
- A good GIF is not proof of clean frames. Always inspect the contact sheet and the transparent sprite sheet.
