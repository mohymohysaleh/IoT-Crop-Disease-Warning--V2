"""One-shot: publish one valid ABP uplink to Docker Mosquitto; check ChirpStack logs."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from node_simulator import build_gateway_message, build_lorawan_phy  # noqa: E402


def main() -> None:
    import random

    gw = "aa00000000000001"
    devaddr = "00000001"
    nwk = "00000000000000000000000000000001"
    app = "00000000000000000000000000000000"  # matches Postgres seed device_keys.app_key for node 1
    port = int(__import__("os").environ.get("MQTT_PORT", "1884"))

    rng = random.Random(42)
    payload = __import__("struct").pack(">hBBH", 2350, 55, 2, 0)
    phy = build_lorawan_phy(devaddr, nwk, app, 0, payload)
    msg = build_gateway_message(phy, gw, rng, 0)

    assert "crcStatus" in msg["rxInfo"]
    assert msg["rxInfo"]["crcStatus"] == "CRC_OK"
    assert msg["rxInfo"]["snr"], "float snr"
    assert isinstance(msg["rxInfo"]["snr"], float)

    topic = f"eu868/gateway/{gw}/event/up"
    cli = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    connected = []

    def on_connect(c, *_):
        connected.append(True)

    cli.on_connect = on_connect
    cli.connect("localhost", port, keepalive=20)
    cli.loop_start()
    for _ in range(60):
        if connected:
            break
        time.sleep(0.05)
    ra = cli.publish(topic, json.dumps(msg, separators=(",", ":")), qos=1)
    ra.wait_for_publish(timeout=10)
    print("publish_rc", ra.rc)
    cli.loop_stop()
    cli.disconnect()


if __name__ == "__main__":
    main()
