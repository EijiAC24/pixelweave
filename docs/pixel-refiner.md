# PixelRefiner handoff

[PixelRefiner](https://github.com/HappyOnigiri/PixelRefiner) is a browser-based cleanup tool for AI-generated pixel art. Its documented feature set includes grid detection, transparent background cleanup, palette reduction and mapping, dithering, outline generation, auto-trim, forced resize, scaled export, and batch processing.

Pixelweave integrates it as an optional, frame-batch handoff rather than pretending that a browser UI is a local CLI. The upstream repository currently documents a Vite/pnpm web app and does not document a command-line or HTTP processing API.

## Recommended position in the pipeline

```text
H3 video → select frames → normalize background → common fit
         → PixelRefiner batch (optional visual cleanup)
         → Pixel Snapper → reference palette lock → transparency → QC → sheet
```

Create the handoff with:

```powershell
.\scripts\prepare_pixel_refiner_handoff.ps1 `
  -InputDir .\work\processed\04_frames_fitted `
  -OutputDir .\work\processed\pixelrefiner_handoff `
  -KeyColor 00ff00 `
  -PixelSize 10 `
  -Colors 16 `
  -PaletteFile .\work\processed\reference_palette.txt `
  -Open
```

Or pass `-WritePixelRefinerHandoff` to `run_postprocess.ps1`. The script copies all numbered frames, writes `pixel-refiner-preset.json`, copies the reference palette, and creates a short README with the return path.

## Settings for animation

- Import all frames as one batch and preserve filename order.
- Use Force or Hint grid detection with one shared pixel size. Do not let each frame choose a different grid.
- Use the exact corner key color and conservative tolerance for background cleanup. Fill interior holes only when the character has accidental holes.
- Use the reference palette or a custom fixed palette. Disable dithering for most game sprites; use ordered dithering only when it is an intentional style choice.
- Use a sharp 4-way outline only when necessary, and apply it consistently to every frame. Independent outline repair can create flicker.
- Keep auto-trim off until the common animation cell is locked. Trim once after the sequence has passed QC.
- Compare the original and refined contact sheets before returning frames to Pixelweave.
