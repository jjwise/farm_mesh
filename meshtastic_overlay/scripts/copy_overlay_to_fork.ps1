param(
    [Parameter(Mandatory = $true)]
    [string]$MeshtasticForkPath
)

$overlayRoot = Split-Path -Parent $PSScriptRoot
$sourceOverlayModules = Join-Path $overlayRoot "src\modules"
$sourceModules = Join-Path $overlayRoot "src\modules\irrigation"
$targetOverlayModules = Join-Path $MeshtasticForkPath "src\modules"
$targetModules = Join-Path $MeshtasticForkPath "src\modules\irrigation"

if (-not (Test-Path $MeshtasticForkPath)) {
    throw "Meshtastic fork path not found: $MeshtasticForkPath"
}

if (-not (Test-Path $sourceModules)) {
    throw "Overlay source not found: $sourceModules"
}

New-Item -Path $targetModules -ItemType Directory -Force | Out-Null
Copy-Item -Path (Join-Path $sourceModules "*") -Destination $targetModules -Recurse -Force
Copy-Item -Path (Join-Path $sourceOverlayModules "IrrigationOverlayModule.h") -Destination $targetOverlayModules -Force
Copy-Item -Path (Join-Path $sourceOverlayModules "IrrigationOverlayModule.cpp") -Destination $targetOverlayModules -Force

Write-Host "Overlay copied to: $targetModules"
Write-Host "Next step: apply hooks listed in meshtastic_overlay/docs/IRRIGATION_PATCHSET.md"
