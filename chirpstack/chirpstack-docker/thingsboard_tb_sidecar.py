"""
ThingsBoard MQTT device client: publishes server-side zone metadata and receives OTA fw_* shared attrs.
Runs alongside node_simulator for devices that subscribe to FW updates via ThingsBoard MQTT.
"""
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

import argparse
import json
import logging
import os
import sys
import threading
import time

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
LOG = logging.getLogger("tb_sidecar")


def telemetry_topic():
    return "v1/devices/me/telemetry"


def attributes_topic_publish():
    return "v1/devices/me/attributes"


def attributes_topic_subscribe():
    return "v1/devices/me/attributes"


class OtaFsm(threading.Thread):
    def __init__(self, client: mqtt.Client, payload: dict, label: str):
        super().__init__(daemon=True)
        self.client = client
        self.payload = payload
        self.label = label

    def publish_ts(self, body: dict):
        self.client.publish(telemetry_topic(), json.dumps(body), qos=1)

    def sleep(self, s):
        time.sleep(s)

    def run(self):
        fwv = self.payload.get("fw_version") or self.payload.get("shared", {}).get("fw_version")
        title = self.payload.get("fw_title") or self.payload.get("shared", {}).get("fw_title")
        LOG.info("[%s] OTA simulate package %s@%s", self.label, title, fwv)

        fail_env = (
            os.environ.get("TB_OTA_SIMULATE_FAIL", "").strip().lower() in ("1", "true", "yes")
        )
        if fail_env:
            self.publish_ts({"fw_state": "FAILED", "fw_title": title, "fw_version": fwv, "failure_reason": "TB_OTA_SIMULATE_FAIL"})
            return

        seq = ["DOWNLOADING", "DOWNLOADED", "VERIFIED", "UPDATING", "UPDATED"]
        for st in seq:
            try:
                self.publish_ts({"fw_state": st, "fw_title": title, "fw_version": fwv})
            except Exception as exc:  # noqa: BLE001
                LOG.error("[%s] fw_state telemetry failed: %s", self.label, exc)
                self.publish_ts({"fw_state": "FAILED", "fw_title": title, "fw_version": fwv, "failure_reason": str(exc)})
                return
            self.sleep(0.4 if st != "UPDATED" else 0)

def maybe_start_ota(client, merged: dict, state: dict, label: str):
    shared = merged.get("shared") or {}
    fv = shared.get("fw_version")
    ft = shared.get("fw_title")
    if fv is None and ft is None:
        return
    key = (str(ft), str(fv))
    if state.get("last_ota_pack") == key:
        return
    state["last_ota_pack"] = key
    LOG.info("[%s] new OTA descriptors: %s", label, shared)
    th = OtaFsm(client, {**merged, "shared": shared}, label)
    th.start()


def main():
    parser = argparse.ArgumentParser(description="ThingsBoard MQTT OTA stub + zone attribute publisher")
    parser.add_argument("--mqtt-host", default="localhost")
    parser.add_argument("--mqtt-port", type=int, default=11883)
    parser.add_argument("--access-token", required=True)
    parser.add_argument("--device-label", default="node")
    parser.add_argument("--zone-tag", default="Zone_1", help="thingsboard_customer_attribute zone")
    args = parser.parse_args()

    def on_connect(client, _userdata, _flags, reason_code, _props=None):  # noqa: ANN001
        rc = getattr(reason_code, "value", reason_code)
        if rc != 0:
            LOG.error("connect rc=%s", rc)
            return
        LOG.info("[%s] connected to ThingsBoard MQTT", args.device_label)
        client.subscribe(attributes_topic_subscribe(), qos=1)
        bootstrap = {"zone": args.zone_tag}
        client.publish(attributes_topic_publish(), json.dumps(bootstrap), qos=1)
        LOG.info("[%s] published client attributes %s", args.device_label, bootstrap)

    ota_seen = {}

    def on_message(_client, _userdata, msg):  # noqa: ANN001
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            LOG.warning("[%s] non-json attrs: %s", args.device_label, msg.payload[:200])
            return
        merged = payload if isinstance(payload, dict) else {}
        LOG.debug("[%s] attrs msg: %s", args.device_label, merged)
        maybe_start_ota(_client, merged, ota_seen, args.device_label)

    client = mqtt.Client(
        client_id=f"tb-{args.device_label}-{args.access_token[-4:]}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.username_pw_set(args.access_token)
    client.on_connect = on_connect
    client.on_message = on_message

    while True:
        try:
            client.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
            break
        except OSError as exc:
            LOG.warning("MQTT connect retry: %s", exc)
            time.sleep(5)

    client.loop_forever()


if __name__ == "__main__":
    main()
