param(
    [Parameter(Mandatory = $true)]
    [string]$MeshtasticForkPath
)

$targetFile = Join-Path $MeshtasticForkPath "variants\esp32s3\heltec_wireless_tracker\platformio.ini"

if (-not (Test-Path $targetFile)) {
    throw "Target file not found: $targetFile"
}

$content = Get-Content $targetFile -Raw

$content = $content -replace "(?m)^\s+-D ARDUINO_USB_MODE=1\r?\n", ""
$content = $content -replace "(?m)^\s+-D ARDUINO_USB_CDC_ON_BOOT=1\r?\n", ""

$content = $content -replace '-D IRRIGATION_MQTT_HOST=\\"https://test\.mosquitto\.org/\\"', '-D IRRIGATION_MQTT_HOST=\"test.mosquitto.org\"'
$content = $content -replace '-D IRRIGATION_MQTT_PORT=1883', '-D IRRIGATION_MQTT_PORT=8883'

Set-Content -Path $targetFile -Value $content -NoNewline

Write-Host "Patched: $targetFile"
