"""Generate the ignored gateway credentials header, including the public CA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def cpp_string(value: str) -> str:
    return json.dumps(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wifi-ssid", required=True)
    parser.add_argument("--wifi-password", required=True)
    parser.add_argument("--mqtt-host", required=True)
    parser.add_argument("--mqtt-password-file", type=Path, required=True)
    parser.add_argument("--command-hmac-key-file", type=Path, required=True)
    parser.add_argument("--ca-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--command-output", type=Path, required=True)
    args = parser.parse_args()

    password = args.mqtt_password_file.read_text(encoding="utf-8").strip()
    command_hmac_key = args.command_hmac_key_file.read_text(encoding="utf-8").strip()
    if len(command_hmac_key) < 32:
        raise ValueError("command HMAC key must contain at least 32 characters")
    ca_pem = args.ca_file.read_text(encoding="utf-8").strip() + "\n"
    gateway_output = (
        "#pragma once\n\n"
        f"#define IRRIGATION_WIFI_SSID {cpp_string(args.wifi_ssid)}\n"
        f"#define IRRIGATION_WIFI_PASSWORD {cpp_string(args.wifi_password)}\n"
        f"#define IRRIGATION_MQTT_HOST {cpp_string(args.mqtt_host)}\n"
        "#define IRRIGATION_MQTT_PORT 8883\n"
        '#define IRRIGATION_MQTT_USERNAME "irrigation-gateway"\n'
        f"#define IRRIGATION_MQTT_PASSWORD {cpp_string(password)}\n"
        f"#define IRRIGATION_MQTT_CA_CERT {cpp_string(ca_pem)}\n"
    )
    command_output = (
        "#pragma once\n\n"
        f"#define IRRIGATION_COMMAND_HMAC_KEY {cpp_string(command_hmac_key)}\n"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(gateway_output, encoding="utf-8", newline="\n")
    args.command_output.parent.mkdir(parents=True, exist_ok=True)
    args.command_output.write_text(command_output, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
