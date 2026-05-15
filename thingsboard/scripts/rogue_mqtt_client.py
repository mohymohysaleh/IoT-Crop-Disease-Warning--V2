#!/usr/bin/env python3
"""Demonstrate unauthorized MQTT CONNECT to ThingsBoard (bonus attack simulation)."""

from pathlib import Path

try:
    from dotenv import load_dotenv

    _here = Path(__file__).resolve()
    for candidate in (
        _here.parent / ".env",
        _here.parents[2] / "chirpstack" / "chirpstack-docker" / ".env",
    ):
        if candidate.is_file():
            load_dotenv(candidate)
            break
except ImportError:
    pass

import argparse
import os

import paho.mqtt.client as mqtt


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mqtt-host", default=os.environ.get("THINGSBOARD_MQTT_HOST", "localhost"))
    p.add_argument("--mqtt-port", type=int, default=int(os.environ.get("THINGSBOARD_MQTT_PORT", "11883")))
    p.add_argument("--token", default="invalid-token-demo")
    args = p.parse_args()

    def on_connect(_c, _u, flags, rc, props=None):  # noqa: ANN001
        code = getattr(rc, "value", rc)
        try:
            why = mqtt.connack_string(code)
        except Exception:  # noqa: BLE001
            why = "unknown"
        print(f"CONNECT callback rc={code} ({why})")

    cli = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="rogue-demo",
    )
    cli.username_pw_set(args.token)
    cli.on_connect = on_connect

    rc = cli.connect(args.mqtt_host, args.mqtt_port, keepalive=20)
    print("TCP connect RC", rc)

    cli.loop_start()
    import time

    time.sleep(2)

    cli.loop_stop()
    print("Inspect ThingsBoard MQTT transport / syslog for auth failure lines.")


if __name__ == "__main__":
    main()
