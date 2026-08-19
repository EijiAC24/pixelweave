[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InputDir,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [string]$SnapperPath,
    [int]$PixelSize = 10,
    [int]$Colors = 16,
    [string]$Palette = '00ff00,0f0f1b,3a2a37,1f3b8a,3b82f6,60a5fa,9b5a4a,f2b28f,6b4518,9b5a2c,d68b35,f9a825,cbd5e1,f7f0d0,ffffff,fff7dc',
    [string]$PaletteFile
)

$ErrorActionPreference = 'Stop'

if (-not $SnapperPath) {
    $candidates = @(
        (Join-Path $env:USERPROFILE 'Documents\MiniMax\spritefusion-pixel-snapper\target\release\spritefusion-pixel-snapper.exe'),
        (Join-Path $env:USERPROFILE 'Tools\spritefusion-pixel-snapper\target\release\spritefusion-pixel-snapper.exe'),
        (Join-Path $env:USERPROFILE 'scoop\apps\spritefusion-pixel-snapper\current\spritefusion-pixel-snapper.exe')
    )
    $SnapperPath = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

if (-not $SnapperPath -or -not (Test-Path -LiteralPath $SnapperPath)) {
    throw 'spritefusion-pixel-snapper.exe not found; pass -SnapperPath explicitly'
}
if (-not (Test-Path -LiteralPath $InputDir)) {
    throw "input directory not found: $InputDir"
}
if ($PaletteFile) {
    if (-not (Test-Path -LiteralPath $PaletteFile)) {
        throw "palette file not found: $PaletteFile"
    }
    $Palette = (Get-Content -LiteralPath $PaletteFile -Raw).Trim()
}
if (-not $Palette) {
    throw 'palette must be provided as -Palette or -PaletteFile'
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$arguments = @($InputDir, $OutputDir, $Colors, '--pixel-size', $PixelSize)
if ($Palette) { $arguments += @('--palette', $Palette) }
& $SnapperPath @arguments
if ($LASTEXITCODE -ne 0) { throw "Pixel Snapper failed with exit code $LASTEXITCODE" }
Write-Output "snapper_output=$OutputDir"
