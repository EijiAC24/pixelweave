[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InputDir,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [ValidatePattern('^[0-9a-fA-F]{6}$')][string]$KeyColor = '00ff00',
    [ValidateRange(0, 255)][int]$Tolerance = 48,
    [ValidateRange(1, 256)][int]$Colors = 16,
    [ValidateRange(1, 100)][int]$PixelSize = 10,
    [string]$PaletteFile,
    [string]$PixelRefinerUrl = 'https://pixel-refiner.app',
    [switch]$Open,
    [switch]$Overwrite
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $InputDir -PathType Container)) {
    throw "input directory not found: $InputDir"
}
$frames = @(Get-ChildItem -LiteralPath $InputDir -Filter 'frame_*.png' -File | Sort-Object Name)
if ($frames.Count -eq 0) {
    throw "no frame PNGs found in $InputDir"
}
if ($PaletteFile -and -not (Test-Path -LiteralPath $PaletteFile -PathType Leaf)) {
    throw "palette file not found: $PaletteFile"
}

$output = [IO.Path]::GetFullPath($OutputDir)
if (Test-Path -LiteralPath $output) {
    $existing = Get-ChildItem -LiteralPath $output -Force -ErrorAction SilentlyContinue
    if ($existing -and -not $Overwrite) {
        throw "output directory is not empty: $output; pass -Overwrite to rerun"
    }
    if ($Overwrite) {
        Remove-Item -LiteralPath $output -Recurse -Force
    }
}
$stagedFrames = Join-Path $output '01_input_frames'
New-Item -ItemType Directory -Force -Path $stagedFrames | Out-Null
foreach ($frame in $frames) {
    Copy-Item -LiteralPath $frame.FullName -Destination (Join-Path $stagedFrames $frame.Name)
}

if ($PaletteFile) {
    Copy-Item -LiteralPath $PaletteFile -Destination (Join-Path $output 'reference_palette.txt') -Force
}

$preset = [ordered]@{
    tool = 'PixelRefiner'
    source = 'https://github.com/HappyOnigiri/PixelRefiner'
    note = 'Human-entered preset: PixelRefiner currently has no documented CLI/API.'
    frame_count = $frames.Count
    input_frames = '01_input_frames'
    recommended = [ordered]@{
        grid = [ordered]@{ mode = 'Force or Hint'; pixel_size = $PixelSize; keep_shared_across_frames = $true }
        background = [ordered]@{ mode = 'corner color / chroma key'; color = "#$KeyColor"; tolerance = $Tolerance; fill_interior_holes = $false; cleanup_noise = $true }
        colors = [ordered]@{ mode = 'custom palette'; color_count = $Colors; palette_file = if ($PaletteFile) { 'reference_palette.txt' } else { $null }; dithering = 'none' }
        outline = [ordered]@{ mode = 'Sharp 4-way only when needed'; apply_consistently_to_all_frames = $true }
        crop = [ordered]@{ auto_trim = $false; reason = 'lock the common animation cell before trimming' }
        export = [ordered]@{ preserve_order = $true; transparent_png = $true }
    }
}
$preset | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'pixel-refiner-preset.json') -Encoding UTF8

$readme = @"
# PixelRefiner handoff

This directory contains $($frames.Count) numbered frames copied from:
`$InputDir`

1. Open `$PixelRefinerUrl` (or run the local PixelRefiner checkout).
2. Import every file in `01_input_frames` as one batch, preserving filename order.
3. Apply the settings in `pixel-refiner-preset.json` to every frame.
4. Export numbered transparent PNGs into a new directory.
5. Feed those PNGs into Pixelweave's Pixel Snapper / fixed-palette / sheet stages.

The preset is a checklist for the web app; PixelRefiner does not currently expose a
documented command-line interface or API, so this handoff does not pretend to be
machine-applied.
"@
$readme | Set-Content -LiteralPath (Join-Path $output 'README.md') -Encoding UTF8

if ($Open) {
    Start-Process $PixelRefinerUrl
}
Write-Output "pixel_refiner_handoff=$output"
Write-Output "frames=$($frames.Count)"
