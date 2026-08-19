[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Video,
    [Parameter(Mandatory = $true)][string]$Reference,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [ValidateRange(1, 1000)][int]$TargetFrames = 13,
    [ValidateSet('uniform', 'arc-length', 'loop')][string]$Strategy = 'arc-length',
    [ValidatePattern('^[0-9a-fA-F]{6}$')][string]$KeyColor = '00ff00',
    [ValidateRange(0, 255)][int]$Tolerance = 48,
    [ValidateRange(0, 255)][int]$Softness = 16,
    [int]$PixelSize = 10,
    [ValidateRange(2, 256)][int]$Colors = 16,
    [ValidateRange(1, 4096)][int]$CanvasSize = 640,
    [ValidateRange(0, 2047)][int]$Margin = 8,
    [ValidateRange(0, 1000)][int]$Columns = 0,
    [string]$Palette,
    [string]$PaletteFile,
    [string]$SnapperPath,
    [string]$Python = 'python',
    [switch]$Despill,
    [switch]$Overwrite
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot

function Assert-File([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label not found: $Path"
    }
}

function Invoke-PythonScript([string]$Name, [string[]]$Arguments) {
    $script = Join-Path $scriptRoot $Name
    & $Python $script @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Assert-File $Video 'video'
Assert-File $Reference 'reference image'
$video = [IO.Path]::GetFullPath($Video)
$reference = [IO.Path]::GetFullPath($Reference)
$output = [IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $output | Out-Null

$existing = Get-ChildItem -LiteralPath $output -Force -ErrorAction SilentlyContinue
if ($existing -and -not $Overwrite) {
    throw "output directory is not empty: $output; pass -Overwrite to rerun"
}

$stageNames = @(
    '01_frames_raw',
    '02_frames_selected',
    '03_frames_green_normalized',
    '04_frames_fitted',
    '05_snapper',
    '06_frames_palette_locked',
    '07_frames_transparent'
)
if ($Overwrite) {
    foreach ($stageName in $stageNames) {
        $stagePath = Join-Path $output $stageName
        if (Test-Path -LiteralPath $stagePath) {
            Remove-Item -LiteralPath $stagePath -Recurse -Force
        }
    }
    Get-ChildItem -LiteralPath $output -Filter 'sprite_sheet_transparent*' -File -ErrorAction SilentlyContinue |
        Remove-Item -Force
    foreach ($name in @('reference_640.png', 'reference_palette.txt', 'sequence_qc.json')) {
        $path = Join-Path $output $name
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    }
}

$raw = Join-Path $output '01_frames_raw'
$selected = Join-Path $output '02_frames_selected'
$normalized = Join-Path $output '03_frames_green_normalized'
$fitted = Join-Path $output '04_frames_fitted'
$snapped = Join-Path $output '05_snapper'
$locked = Join-Path $output '06_frames_palette_locked'
$transparent = Join-Path $output '07_frames_transparent'
$referenceCopy = Join-Path $output 'reference_640.png'
$palettePath = Join-Path $output 'reference_palette.txt'
$sheet = Join-Path $output 'sprite_sheet_transparent.png'

Copy-Item -LiteralPath $reference -Destination $referenceCopy -Force
Invoke-PythonScript 'extract_video_frames.py' @($video, $raw, '--overwrite')
Invoke-PythonScript 'ensure_first_frame.py' @($referenceCopy, $raw, '--key-color', $KeyColor, '--tolerance', "$Tolerance", '--replace')
Invoke-PythonScript 'select_frames.py' @($raw, $selected, '--target-count', "$TargetFrames", '--strategy', $Strategy, '--key-color', $KeyColor, '--tolerance', "$Tolerance", '--metadata', '--overwrite')

$normalizeMode = 'normalize-key'
if ($KeyColor.ToLowerInvariant() -eq '00ff00') { $normalizeMode = 'normalize-green' }
Invoke-PythonScript 'prepare_background.py' @($selected, $normalized, '--mode', $normalizeMode, '--key-color', $KeyColor, '--tolerance', "$Tolerance")
Invoke-PythonScript 'fit_frames_to_canvas.py' @($normalized, $fitted, '--canvas-size', "$CanvasSize", '--margin', "$Margin", '--key-color', $KeyColor, '--tolerance', "$Tolerance", '--overwrite')

if (-not $Palette -and -not $PaletteFile) {
    Invoke-PythonScript 'extract_reference_palette.py' @($referenceCopy, $palettePath, '--colors', "$Colors", '--key-color', $KeyColor, '--tolerance', "$Tolerance")
    $PaletteFile = $palettePath
}

$snapperArguments = @{
    InputDir = $fitted
    OutputDir = $snapped
    SnapperPath = $SnapperPath
    PixelSize = $PixelSize
    Colors = $Colors
}
if ($PaletteFile) { $snapperArguments.PaletteFile = $PaletteFile }
elseif ($Palette) { $snapperArguments.Palette = $Palette }
& (Join-Path $scriptRoot 'run_pixel_snapper.ps1') @snapperArguments
if ($LASTEXITCODE -ne 0) { throw "run_pixel_snapper.ps1 failed with exit code $LASTEXITCODE" }

$paletteArguments = @($snapped, $locked, '--key-color', $KeyColor, '--tolerance', "$Tolerance", '--overwrite')
if ($PaletteFile) { $paletteArguments += @('--palette-file', $PaletteFile) }
else { $paletteArguments += @('--palette', $Palette) }
Invoke-PythonScript 'apply_fixed_palette.py' $paletteArguments

$removeMode = 'remove-key'
if ($KeyColor.ToLowerInvariant() -eq '00ff00') { $removeMode = 'remove-green' }
$removeArguments = @($locked, $transparent, '--mode', $removeMode, '--key-color', $KeyColor, '--tolerance', "$Tolerance", '--softness', "$Softness")
if ($Despill) { $removeArguments += '--despill' }
Invoke-PythonScript 'prepare_background.py' $removeArguments

Invoke-PythonScript 'analyze_sprite_sequence.py' @($locked, '--output', (Join-Path $output 'sequence_qc.json'), '--key-color', $KeyColor, '--tolerance', "$Tolerance")
$sheetColumns = $Columns
if ($sheetColumns -eq 0) { $sheetColumns = $TargetFrames }
$qualityGate = Join-Path $output 'quality_gate.json'
Invoke-PythonScript 'validate_sprite_sequence.py' @($transparent, '--output', $qualityGate, '--expected-count', "$TargetFrames", '--key-color', $KeyColor, '--tolerance', "$Tolerance", '--allow-variable-canvas')
$contactSheet = Join-Path $output 'quality_contact_sheet.png'
$contactColumns = [Math]::Min($sheetColumns, 8)
Invoke-PythonScript 'make_qc_contact_sheet.py' @($transparent, $contactSheet, '--columns', "$contactColumns", '--key-color', $KeyColor, '--tolerance', "$Tolerance")
Invoke-PythonScript 'make_sprite_sheet.py' @($transparent, $sheet, '--columns', "$sheetColumns", '--background', 'transparent', '--anchor', 'bottom-center', '--preview-scale', '4', '--metadata')

Write-Output "postprocess_complete=$output"
Write-Output "sprite_sheet=$sheet"
Write-Output "selected_frames=$selected"
