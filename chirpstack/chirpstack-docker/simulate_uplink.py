"""
Push synthetic LoRaWAN uplinks into ChirpStack via the MQTT gateway-backend path.

ChirpStack v4 (+ chirpstack-rest-api) does **not** implement REST helpers like
``POST /api/devices/{devEui}/uplink`` or ``/simulate-uplink`` — those URLs
always return **404**.

This script publishes valid ABP MIC + FRMPayload frames to::

    eu868/gateway/<gateway_eui>/event/up

matching ``node_simulator.py`` so ChirpStack accepts payloads the same way as
physical gateway bridge traffic.

MQTT host/port load from `.env` (``MQTT_HOST`` / ``MQTT_PORT``) like the node
simulators — use the **same** Mosquitto instance ChirpStack uses.

Device keys and gateways come from ``config/devices.json`` (aligned with UI).
"""

from __future__ import annotations

import json
import os
import random
import struct
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from node_simulator import build_gateway_message, build_lorawan_phy

UPLINK_TOPIC = "eu868/gateway/{gateway_id}/event/up"

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "devices.json"


@dataclass
class DeviceEntry:
    deveui: str
    devaddr: str
    nwk_skey: str
    app_skey: str
    gateway_eui: str


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return int(raw)


def mqtt_host_port() -> tuple[str, int]:
    return (
        os.environ.get("MQTT_HOST", os.environ.get("MOSQUITTO_HOST", "localhost")),
        _env_int("MQTT_PORT", _env_int("MOSQUITTO_PORT", 1884)),
    )


def load_devices(cfg_path: Path) -> list[DeviceEntry]:
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    out: list[DeviceEntry] = []
    gw1 = os.environ.get("SIM_ZONE1_GATEWAY_EUI", "aa00000000000001").lower()
    gw2 = os.environ.get("SIM_ZONE2_GATEWAY_EUI", "aa00000000000002").lower()
    for zone_key, gw in (("Zone1", gw1), ("Zone2", gw2)):
        for row in data.get(zone_key, []):
            out.append(
                DeviceEntry(
                    deveui=str(row["deveui"]).lower(),
                    devaddr=str(row["devaddr"]).lower(),
                    nwk_skey=str(row["nwk_skey"]).lower(),
                    app_skey=str(row["app_skey"]).lower(),
                    gateway_eui=gw,
                )
            )
    return out


def payload_for(deveui: str, ticks: int) -> bytes:
    """Same binary framing as legacy ``simulate_uplink`` / ``node_simulator``."""

    temp = random.uniform(22, 28)
    hum = random.uniform(45, 55)
    leaf = random.randint(0, 10)
    rain = 0.0

    if deveui == "0000000000000001":
        hum = min(95, 60 + (ticks * 2))
        leaf = min(255, ticks * 20)
    elif deveui == "0000000000000006":
        if ticks % 5 == 0:
            rain = 15.5
            hum = 90

    return struct.pack(
        ">hBBH",
        int(temp * 100),
        int(hum),
        int(leaf),
        int(rain * 10),
    )


def mqtt_client() -> mqtt.Client:
    connected = [False]

    def on_connect(client, _u, flags, rc, props=None):
        if rc == 0:
            connected[0] = True

    cli = mqtt.Client(
        client_id="simulate-uplink-batch",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    cli.on_connect = on_connect
    host, port = mqtt_host_port()
    cli.connect(host, port, keepalive=60)
    cli.loop_start()
    for _ in range(50):
        if connected[0]:
            break
        time.sleep(0.05)
    if not connected[0]:
        cli.loop_stop()
        cli.disconnect()
        raise SystemExit(f"MQTT not connected ({host}:{port}). Check Docker Mosquitto and MQTT_PORT.")
    return cli


def main() -> None:
    seed = _env_int("SIM_RNG_SEED", 453)
    rng_gateway = random.Random(seed + 997)
    interval = _env_int("SIM_TELEMETRY_INTERVAL", 300)

    devices = load_devices(CONFIG_PATH)
    if not devices:
        raise SystemExit(f"No devices in {CONFIG_PATH}")

    print("Starting MQTT uplink simulation (ChirpStack v4 REST has no simulate endpoint).")
    print(f"Loaded {len(devices)} devices from {CONFIG_PATH.name}; interval {interval}s")
    cli = mqtt_client()
    host, port = mqtt_host_port()
    print(f"MQTT {host}:{port} -> eu868/gateway/.../event/up")

    fcnt: dict[str, int] = {d.deveui: 0 for d in devices}
    ticks = 0
    try:
        while True:
            ticks += 1
            for d in devices:
                n = fcnt[d.deveui]
                raw = payload_for(d.deveui, ticks)
                phy = build_lorawan_phy(d.devaddr, d.nwk_skey, d.app_skey, n, raw)
                gw_msg = build_gateway_message(phy, d.gateway_eui, rng_gateway, n)
                topic = UPLINK_TOPIC.format(gateway_id=d.gateway_eui)
                r = cli.publish(topic, json.dumps(gw_msg, separators=(",", ":")), qos=1)
                ok = r.rc == 0
                st = datetime.now().strftime("%H:%M:%S")
                tag = "OK " if ok else "FAIL"
                print(f"[{st}] {tag}: {d.deveui}")
                if ok:
                    fcnt[d.deveui] += 1
                else:
                    print(f"           mqtt publish rc={r.rc}")

            print("-" * 50)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        cli.loop_stop()
        cli.disconnect()


if __name__ == "__main__":
    main()
