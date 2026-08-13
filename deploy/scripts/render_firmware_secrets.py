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
    parser.add_argument("--ca-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    password = args.mqtt_password_file.read_text(encoding="utf-8").strip()
    ca_pem = args.ca_file.read_text(encoding="utf-8").strip() + "\n"
    output = (
        "#pragma once\n\n"
        f"#define IRRIGATION_WIFI_SSID {cpp_string(args.wifi_ssid)}\n"
        f"#define IRRIGATION_WIFI_PASSWORD {cpp_string(args.wifi_password)}\n"
        f"#define IRRIGATION_MQTT_HOST {cpp_string(args.mqtt_host)}\n"
        "#define IRRIGATION_MQTT_PORT 8883\n"
        '#define IRRIGATION_MQTT_USERNAME "irrigation-gateway"\n'
        f"#define IRRIGATION_MQTT_PASSWORD {cpp_string(password)}\n"
        '#define IRRIGATION_MQTT_CA_CERT R"IRRIGATION_CA(\n'
        f"{ca_pem}"
        ')IRRIGATION_CA"\n'
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
