# Palette and outline stability

## Why colors flicker

If every frame is quantized independently, a near-black fur pixel may become a
different dark color in each frame. The same happens to red collars, skin, and
black outlines. The result is temporal color flicker even when the geometry is
stable.

## The fixed-palette flow

1. Extract a palette from the original reference image, including the key color.
2. Pass that exact palette to Pixel Snapper.
3. Apply the same palette to every snapped frame.
4. Remove the key color only after palette locking.
5. Use despill to reduce green contamination around antialiased edges.

The reference palette should contain the outline color, the main fill, one or
two shadow colors, accessory colors, and the chroma key. If green is a real
subject color, use a magenta key instead and pass `-KeyColor ff00ff`.

## Outline repair

Post-processing can stabilize an outline when the damage is small: lock the
palette, remove near-key pixels, and optionally perform a one-pixel outline
repair in an editor. It cannot reliably reconstruct a missing ear, paw, or
collar. If the silhouette changes substantially, regenerate H3 with a stricter
frame-0 and fixed-bounding-box prompt.
