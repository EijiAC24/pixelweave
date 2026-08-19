[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Sheet,
    [Parameter(Mandatory = $true)][string]$Output,
    [Parameter(Mandatory = $true)][ValidateRange(1, 4096)][int]$Columns,
    [Parameter(Mandatory = $true)][ValidateRange(1, 4096)][int]$FrameWidth,
    [Parameter(Mandatory = $true)][ValidateRange(1, 4096)][int]$FrameHeight,
    [Parameter(Mandatory = $true)][ValidateRange(1, 10000)][int]$FrameDurationMs,
    [string]$AsepritePath = 'C:\Program Files\Aseprite\aseprite.exe'
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Sheet -PathType Leaf)) {
    throw "sprite sheet not found: $Sheet"
}
if (-not (Test-Path -LiteralPath $AsepritePath -PathType Leaf)) {
    throw "Aseprite not found: $AsepritePath"
}

$outputPath = [IO.Path]::GetFullPath($Output)
New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($outputPath)) | Out-Null
$scriptPath = Join-Path $PSScriptRoot 'import_aseprite_animation.lua'

& $AsepritePath --batch `
    --script-param ("input=$([IO.Path]::GetFullPath($Sheet))") `
    --script-param "output=$outputPath" `
    --script-param "frame_width=$FrameWidth" `
    --script-param "frame_height=$FrameHeight" `
    --script-param "columns=$Columns" `
    --script-param "frame_duration_ms=$FrameDurationMs" `
    --script $scriptPath

$deadline = (Get-Date).AddSeconds(30)
while (-not (Test-Path -LiteralPath $outputPath -PathType Leaf) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 250
}
if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
    throw "Aseprite did not create the output: $outputPath"
}
Get-Item -LiteralPath $outputPath | Select-Object FullName, Length, LastWriteTime
