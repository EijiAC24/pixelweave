# Pipeline design

## Stages

1. Generate one locked-camera 640×640 MiniMax-H3 video.
2. Decode all native frames and verify frame 0 against the reference image.
3. Select an exact output count. `arc-length` preserves motion changes better than plain uniform sampling; `loop` searches for an internal seam.
4. Normalize the chroma-key background.
5. Find the union of all foreground boxes, then crop and fit every frame into one common canvas. This is the step that prevents the character from changing size or being clipped.
6. Run Pixel Snapper with one explicit pixel size and one palette.
7. Apply the reference palette again after snapping. This second lock is intentional: it removes small per-frame color drift introduced by quantization.
8. Remove the key background with softness and optional despill.
9. Pack frames with one cell size and an explicit anchor. Emit a JSON manifest.
10. Import the sheet into Aseprite as animation frames, preserving approximate source timing.

## Recommended defaults

| Parameter | Default | Reason |
| --- | ---: | --- |
| native size | 640×640 | enough room for H3 while keeping the subject readable |
| native frames | 39 | MiniMax-H3 cycle used by the sample workflow |
| source fps | 24 | H3 video output |
| reduced frames | 13 | useful sprite animation density |
| pixel size | 10 | coarse, readable pixel-art blocks |
| palette | 16 colors | avoids flicker without flattening the subject |
| sheet columns | output frame count | one horizontal action strip |

## Coordinate invariants

The pipeline treats these as contracts:

- frame 0 is the supplied reference pose;
- all frames share the same foreground box and canvas;
- the baseline and horizontal center are stable;
- no frame may crop the subject;
- the chroma key is not allowed to become a subject color;
- the final palette is shared by every frame.

## Stages on disk

`run_postprocess.ps1` writes named directories instead of hiding intermediate images:

```text
01_frames_raw/
02_frames_selected_13/
03_frames_green_normalized/
04_frames_fitted_640/
05_snapper_10px_16color/
06_frames_palette_locked/
07_frames_transparent/
sprite_sheet_transparent.png
sprite_sheet_transparent.json
```

Keeping these stages makes it easy to inspect whether a defect came from H3, frame selection, fitting, quantization, or chroma removal.
