"""
Publish MQTT gateway **stats** + **conn (ONLINE)** state so ChirpStack marks gateways online.

- Events: https://www.chirpstack.io/docs/chirpstack-gateway-bridge/payloads/events.html
- States: https://www.chirpstack.io/docs/chirpstack-gateway-bridge/payloads/states.html

Stats alone are often not enough: ChirpStack expects **ConnState** on
`eu868/gateway/{id}/state/conn` with JSON {"gatewayId":"...","state":"ONLINE"} .

You MUST still register gateways in the ChirpStack UI (same Gateway IDs as here).
"""
import json
import logging
import os
import time
from pathlib import Path

import paho.mqtt.client as mqtt

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


CONFIG = {
    "mqtt_host": os.environ.get("MQTT_HOST", os.environ.get("MOSQUITTO_HOST", "localhost")),
    "mqtt_port": _env_int("MQTT_PORT", _env_int("MOSQUITTO_PORT", 1884)),
    "gateways": [
        "aa00000000000001",  # Zone 1 — must match ChirpStack gateway record
        "aa00000000000002",  # Zone 2
    ],
}


def send_gateway_conn_online(client, gateway_eui: str):
    """
    ConnState ONLINE — required for UI / NS to treat gateway as connected.
    Topic: eu868/gateway/{id}/state/conn (see chirpstack.toml state_topic_template).
    """
    body = {"gatewayId": gateway_eui, "state": "ONLINE"}
    topic = f"eu868/gateway/{gateway_eui}/state/conn"
    payload = json.dumps(body, separators=(",", ":"))
    result = client.publish(topic, payload, qos=1, retain=True)
    log.info(
        "Gateway %s → state/conn ONLINE (%s)",
        gateway_eui,
        "ok" if result.rc == 0 else "FAIL",
    )


def send_gateway_stats(client, gateway_eui: str):
    """
    Minimal GatewayStats JSON (protobuf JSON mapping).
    Topic: eu868/gateway/{id}/event/stats
    """
    stats = {
        "gatewayId": gateway_eui,
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rxPacketsReceived": 10,
        "rxPacketsReceivedOk": 10,
        "txPacketsReceived": 0,
        "txPacketsEmitted": 0,
    }

    topic = f"eu868/gateway/{gateway_eui}/event/stats"
    payload = json.dumps(stats, separators=(",", ":"))
    result = client.publish(topic, payload, qos=1)
    log.info(
        "Gateway %s → event/stats (%s)",
        gateway_eui,
        "ok" if result.rc == 0 else "FAIL",
    )


def main():
    connected = [False]

    def on_connect(client, userdata, flags, rc, props=None):
        if rc == 0:
            connected[0] = True
            log.info("Connected to MQTT broker (ok)")

    client = mqtt.Client(
        client_id="gateway-activator",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.on_connect = on_connect
    client.connect(CONFIG["mqtt_host"], CONFIG["mqtt_port"], keepalive=60)
    client.loop_start()
    time.sleep(1)

    log.info(
        "Publishing state/conn ONLINE + event/stats every 30s for %s gateways...",
        len(CONFIG["gateways"]),
    )
    log.info(
        "MQTT broker %s:%s — must match ChirpStack's Mosquitto (Docker). "
        "On Windows, if another Mosquitto listens on 127.0.0.1:1883, set MQTT_PORT in .env "
        "to the host port mapped to the container (this repo uses 1884:1883 in compose).",
        CONFIG["mqtt_host"],
        CONFIG["mqtt_port"],
    )
    log.info("Register these Gateway IDs in ChirpStack UI (%s). Ctrl+C to stop.", ", ".join(CONFIG["gateways"]))

    while True:
        for gw_eui in CONFIG["gateways"]:
            send_gateway_conn_online(client, gw_eui)
            send_gateway_stats(client, gw_eui)
        time.sleep(30)


if __name__ == "__main__":
    main()
