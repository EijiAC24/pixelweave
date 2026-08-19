# Labrador run sample

This sample uses one corrected side-view black Labrador pixel-art reference with
exactly four legs and a red collar on a flat green chroma-key background.

## Files

- `source_imagegen.png` — corrected generated source image used for this sample
- `reference_640_green.png` — fixed 640×640 H3 frame-0 reference
- `minimax_h3_workflow_api.json` — ComfyUI API prompt used for the retry
- `reference_palette.txt` — 16-color palette extracted from the reference
- `frames/` — 13 final transparent frames
- `artifacts/labrador_run_39frames_640.mp4` — 39 native frames at 24fps
- `artifacts/labrador_run_13frames_transparent_reference_palette.png` — final sheet
- `artifacts/quality_contact_sheet.png` — labeled frame-by-frame inspection sheet
- `artifacts/quality_gate.json` — numeric output-frame quality report
- `artifacts/labrador_run_13frames_reference_palette.aseprite` — editable timeline

The native video is 1.625 seconds long. The 13-frame sheet uses 125ms per frame
in Aseprite so the reduced animation keeps approximately the same duration.
