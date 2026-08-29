"""Tests for separated firmware secret headers."""

import subprocess
import sys
from pathlib import Path


def test_renderer_separates_gateway_and_command_secrets(tmp_path: Path) -> None:
    script = Path(__file__).parents[2] / "deploy" / "scripts" / "render_firmware_secrets.py"
    mqtt_password_file = tmp_path / "mqtt.txt"
    hmac_key_file = tmp_path / "hmac.txt"
    ca_file = tmp_path / "ca.crt"
    gateway_output = tmp_path / "gateway.h"
    command_output = tmp_path / "command.h"
    mqtt_password_file.write_text("mqtt-secret\n", encoding="utf-8")
    hmac_key_file.write_text("0123456789abcdef0123456789abcdef\n", encoding="utf-8")
    ca_file.write_text("TEST CA\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--wifi-ssid",
            "test-wifi",
            "--wifi-password",
            "wifi-secret",
            "--mqtt-host",
            "mqtt.example.test",
            "--mqtt-password-file",
            str(mqtt_password_file),
            "--command-hmac-key-file",
            str(hmac_key_file),
            "--ca-file",
            str(ca_file),
            "--output",
            str(gateway_output),
            "--command-output",
            str(command_output),
        ],
        check=True,
    )

    gateway_header = gateway_output.read_text(encoding="utf-8")
    command_header = command_output.read_text(encoding="utf-8")
    assert "IRRIGATION_WIFI_SSID" in gateway_header
    assert "IRRIGATION_MQTT_PASSWORD" in gateway_header
    assert "IRRIGATION_COMMAND_HMAC_KEY" not in gateway_header
    assert "IRRIGATION_COMMAND_HMAC_KEY" in command_header
    assert "IRRIGATION_WIFI_SSID" not in command_header
    assert "IRRIGATION_MQTT_PASSWORD" not in command_header
