# MiniMax-H3 prompting and action profiles

The H3 prompt needs to describe invariants before motion. A useful template is:

```text
The provided image is frame 0 and must match the input image exactly.
Use it as the exact pixel-art reference. Do not redesign, restyle, resize,
reposition, or crop the subject. Preserve the same silhouette, proportions,
colors, outline, accessories, and flat #00ff00 chroma-key background.

Keep the camera locked and keep the subject inside one fixed safe rectangle.
The opaque subject bounding box must keep the same width and height in every
frame. Animate only: <describe one readable action>.

Keep all important parts visible at all times. Return to the exact frame-0 pose
at the end for a seamless loop. One continuous 39-frame cycle, static camera,
no pan, no tilt, no zoom, no cuts, no scenery, no shadow, no text, no logo, and
no watermark.
```

For the Labrador sample, `<describe one readable action>` is:

```text
one readable running cycle: alternating front and rear leg strides, gentle tail
swing, a small floppy-ear bounce, and a tiny controlled body bob
```

Avoid vague prompts such as “make it lively.” They allow the model to redesign
the character, move the camera, or change its bounding box. Avoid asking H3 to
make a final sprite sheet; H3 should only produce the motion source video.

## Strict loop versus expressive action

Use `strict_loop` for run, idle, swim, water, fire, grass, and other assets where
identity, shared scale, and a clean loop matter more than dramatic posing. Keep
the first and last pose exact and permit only small controlled motion.

Use `expressive_action` for a dodge roll, ledge climb, sword swing, jump, or
similar action. Add anticipation, a clear extreme, follow-through, and settle,
but keep the camera, common cell, palette families, and complete silhouette
inside the same safe rectangle. Expressiveness is allowed inside the cell, not
through independent per-frame resizing or cropping.

Reusable profiles and challenge prompts live in
[`prompts/animation_profiles.json`](../prompts/animation_profiles.json). The
benchmark actions are deliberately difficult cases suggested by the local H3
workflow discussion: running, dodge rolls, ledge climbs, sword swings, and
environmental loops.

## Frame inspection

Do not judge a generated sequence only by playing its GIF. Extract every native
frame, inspect a contact sheet, and inspect the final transparent sheet. Motion
blur, streaks, missing outlines, duplicated frames, and a bad loop seam can be
hidden at playback speed. Pixelweave writes `quality_gate.json` and
`quality_contact_sheet.png` during post-processing for this reason.
