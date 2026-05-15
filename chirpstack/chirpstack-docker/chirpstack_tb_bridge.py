#!/usr/bin/env python3
"""
Subscribe to ChirpStack application uplinks on Mosquitto and push telemetry to
ThingsBoard Community Edition via HTTP device API (replaces PE-only Integrations).

Expects device profiles named Zone1_Sensor and Zone2_Sensor. Creates one TB
device per devEUI (name = lowercase devEUI) on first uplink.

Env (see .env.example):
  MQTT_HOST, MQTT_PORT — Mosquitto (1884 host / 1883 in-compose)
  TB_URL — http://localhost:9090 or http://thingsboard:9090 in Docker
  TB_USERNAME, TB_PASSWORD — ThingsBoard **Tenant Administrator** only (not sysadmin; see script RuntimeError if wrong).
  TB_ZONE1_PROFILE_ID, TB_ZONE2_PROFILE_ID — optional UUIDs; if unset or not found for this tenant, resolved by profile name
"""
from __future__ import annotations

import base64
import json
import logging
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

try:
    from dotenv import load_dotenv

    load_dotenv(os.environ.get("DOTENV_PATH", "") or Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

import paho.mqtt.client as mqtt
import requests

LOG = logging.getLogger("chirpstack_tb_bridge")

TOPIC_FILTER = "application/+/device/+/event/up"

Z2_EUIS = frozenset(
    {
        "0000000000000006",
        "0000000000000007",
        "0000000000000008",
        "0000000000000009",
        "0000000000000010",
    }
)


def zone_for_eui(eui: str) -> str:
    e = (eui or "").lower()
    return "Zone_2" if e in Z2_EUIS else "Zone_1"


def decode_bytes_from_data_b64(b64: str | None) -> dict[str, float | int] | None:
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64, validate=True)
    except (ValueError, TypeError):
        return None
    if len(raw) < 6:
        return None
    t = (raw[0] << 8) | raw[1]
    if t > 32767:
        t -= 65536
    temperature = t / 100.0
    humidity = raw[2]
    leaf_wetness = raw[3]
    rain_raw = (raw[4] << 8) | raw[5]
    rainfall = rain_raw / 10.0
    return {
        "temperature": round(temperature, 2),
        "humidity": humidity,
        "leaf_wetness": leaf_wetness,
        "rainfall": round(rainfall, 2),
    }


def _telemetry_from_object(obj: Any) -> dict[str, Any]:
    """ChirpStack codec may return flat fields or { data: { temperature, ... } }."""
    if not isinstance(obj, dict):
        return {}
    out: dict[str, Any] = {}
    inner = obj.get("data") if isinstance(obj.get("data"), dict) else obj
    if not isinstance(inner, dict):
        inner = obj
    for k in ("temperature", "humidity", "leaf_wetness", "rainfall"):
        if k in inner and inner[k] is not None:
            out[k] = inner[k]
    return out


def decode_uplink_payload(payload: bytes) -> tuple[str, str, dict[str, Any]]:
    """Return (dev_eui, human_name, telemetry_dict)."""
    input_obj = json.loads(payload.decode("utf-8"))
    dev = input_obj.get("deviceInfo") or {}
    eui = (dev.get("devEui") or dev.get("dev_eui") or "").lower()
    human = (dev.get("deviceName") or eui or "unknown_device").strip()

    telem: dict[str, Any] = {}
    obj = input_obj.get("object")
    if isinstance(obj, dict):
        telem = _telemetry_from_object(obj)
    if not telem and input_obj.get("data"):
        parsed = decode_bytes_from_data_b64(str(input_obj["data"]))
        if parsed:
            telem = dict(parsed)

    return eui, human, telem


class TbBridge:
    def __init__(self) -> None:
        self.tb = os.environ.get("TB_URL", "http://localhost:9090").rstrip("/")
        self.user = os.environ.get("TB_USERNAME", "tenant@thingsboard.org")
        self.password = os.environ.get("TB_PASSWORD", "tenant")
        self._token: str | None = None
        self._lock = threading.Lock()
        self._profile_zone1: str | None = os.environ.get("TB_ZONE1_PROFILE_ID") or None
        self._profile_zone2: str | None = os.environ.get("TB_ZONE2_PROFILE_ID") or None
        # dev_eui -> access_token (cached)
        self._tokens: dict[str, str] = {}
        self._zones_sent: set[str] = set()
        self._tenant_admin_checked = False

    def wait_until_ready(self, max_attempts: int = 45, delay_sec: float = 2.0) -> None:
        """Block until ThingsBoard accepts login (handles slow TB startup after `docker compose up`)."""
        for i in range(max_attempts):
            try:
                r = requests.post(
                    f"{self.tb}/api/auth/login",
                    json={"username": self.user, "password": self.password},
                    timeout=15,
                )
                if r.status_code < 400 and r.json().get("token"):
                    if i:
                        LOG.info("ThingsBoard reachable at %s after %s attempts", self.tb, i + 1)
                    return
                LOG.warning("TB login returned %s (attempt %s/%s)", r.status_code, i + 1, max_attempts)
            except (requests.RequestException, OSError) as ex:
                LOG.warning("ThingsBoard not ready (%s/%s): %s", i + 1, max_attempts, ex)
            time.sleep(delay_sec)
        raise RuntimeError(f"ThingsBoard at {self.tb} did not accept login after {max_attempts} attempts (~{max_attempts * delay_sec:.0f}s).")

    def _require_tenant_admin(self) -> None:
        """TB CE allows /api/tenant/devices and POST /api/device only for TENANT_ADMIN."""
        if self._tenant_admin_checked:
            return
        tok = self.token()
        r = requests.get(
            f"{self.tb}/api/auth/user",
            headers={"Authorization": f"Bearer {tok}"},
            timeout=30,
        )
        r.raise_for_status()
        auth = (r.json().get("authority") or "").strip()
        if auth != "TENANT_ADMIN":
            raise RuntimeError(
                f"TB_USERNAME {self.user!r} has authority {auth!r}. "
                "Use a Tenant Administrator account in TB_USERNAME/TB_PASSWORD (e.g. tenant@thingsboard.org). "
                "SYS_ADMIN cannot call /api/tenant/devices or POST /api/device — the bridge will always get HTTP 403."
            )
        self._tenant_admin_checked = True
        LOG.info("ThingsBoard user %s is TENANT_ADMIN (device API allowed)", self.user)

    def _device_profile_exists(self, profile_id: str) -> bool:
        if not profile_id:
            return False
        r = requests.get(
            f"{self.tb}/api/deviceProfile/{profile_id}",
            headers=self.auth_headers(),
            timeout=30,
        )
        return r.status_code == 200

    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token()}"}

    def token(self) -> str:
        with self._lock:
            if self._token:
                return self._token
            r = requests.post(
                f"{self.tb}/api/auth/login",
                json={"username": self.user, "password": self.password},
                timeout=30,
            )
            r.raise_for_status()
            tok = r.json().get("token")
            if not tok:
                raise RuntimeError(r.text)
            self._token = tok
            return self._token

    def resolve_profiles(self) -> None:
        self._require_tenant_admin()
        r = requests.get(
            f"{self.tb}/api/deviceProfiles",
            params={"pageSize": 100, "page": 0},
            headers=self.auth_headers(),
            timeout=30,
        )
        r.raise_for_status()
        data = r.json().get("data") or []
        by_name = {row.get("name"): row.get("id", {}).get("id") for row in data if row.get("name")}

        if self._profile_zone1 and not self._device_profile_exists(self._profile_zone1):
            LOG.warning(
                "TB_ZONE1_PROFILE_ID %s not found for this tenant; resolving Zone1_Sensor by name",
                self._profile_zone1,
            )
            self._profile_zone1 = None
        if self._profile_zone2 and not self._device_profile_exists(self._profile_zone2):
            LOG.warning(
                "TB_ZONE2_PROFILE_ID %s not found for this tenant; resolving Zone2_Sensor by name",
                self._profile_zone2,
            )
            self._profile_zone2 = None

        if self._profile_zone1 and self._profile_zone2:
            LOG.info(
                "Using device profiles from env Zone1_Sensor=%s Zone2_Sensor=%s",
                self._profile_zone1,
                self._profile_zone2,
            )
            return

        if not self._profile_zone1:
            self._profile_zone1 = by_name.get("Zone1_Sensor")
            if not self._profile_zone1:
                raise RuntimeError(
                    "No TB_ZONE1_PROFILE_ID and no device profile named Zone1_Sensor in ThingsBoard."
                )
        if not self._profile_zone2:
            self._profile_zone2 = by_name.get("Zone2_Sensor")
            if not self._profile_zone2:
                raise RuntimeError(
                    "No TB_ZONE2_PROFILE_ID and no device profile named Zone2_Sensor in ThingsBoard."
                )
        LOG.info("Using device profiles Zone1_Sensor=%s Zone2_Sensor=%s", self._profile_zone1, self._profile_zone2)

    def profile_id_for_zone(self, zone_tag: str) -> str:
        assert self._profile_zone1 and self._profile_zone2
        return self._profile_zone2 if zone_tag == "Zone_2" else self._profile_zone1

    def find_existing_device(self, dev_eui: str) -> str | None:
        q = quote(dev_eui)
        r = requests.get(
            f"{self.tb}/api/tenant/devices",
            params={"pageSize": 50, "page": 0, "textSearch": q, "sortProperty": "name", "sortOrder": "ASC"},
            headers=self.auth_headers(),
            timeout=30,
        )
        r.raise_for_status()
        for row in r.json().get("data") or []:
            if row.get("name") == dev_eui.lower():
                did = row.get("id", {}).get("id")
                if did:
                    return str(did)
        return None

    def get_access_token_for_device_uuid(self, device_uuid: str) -> str:
        r = requests.get(
            f"{self.tb}/api/device/{device_uuid}/credentials",
            headers=self.auth_headers(),
            timeout=30,
        )
        r.raise_for_status()
        cred = r.json()
        if cred.get("credentialsType") != "ACCESS_TOKEN":
            raise RuntimeError(f"Unexpected credential type: {cred!r}")
        token = cred.get("credentialsId")
        if not token:
            raise RuntimeError("No ACCESS_TOKEN on device")
        return str(token)

    def create_device(self, dev_eui: str, zone_tag: str) -> str:
        pid = self.profile_id_for_zone(zone_tag)
        dev_type = "Zone2_Sensor" if zone_tag == "Zone_2" else "Zone1_Sensor"
        body = {
            "name": dev_eui.lower(),
            "type": dev_type,
            "deviceProfileId": {"id": pid, "entityType": "DEVICE_PROFILE"},
        }
        r = requests.post(f"{self.tb}/api/device", headers=self.auth_headers(), json=body, timeout=30)
        if r.status_code >= 400:
            oid = self.find_existing_device(dev_eui)
            if oid:
                return self.get_access_token_for_device_uuid(oid)
        r.raise_for_status()
        did = r.json().get("id", {}).get("id")
        if not did:
            raise RuntimeError(r.text)
        return self.get_access_token_for_device_uuid(str(did))

    def ensure_token(self, dev_eui: str, zone_tag: str) -> str:
        k = dev_eui.lower()
        if k in self._tokens:
            return self._tokens[k]
        oid = self.find_existing_device(dev_eui)
        tok: str
        if oid:
            tok = self.get_access_token_for_device_uuid(oid)
        else:
            tok = self.create_device(dev_eui, zone_tag)
        self._tokens[k] = tok
        return tok

    def post_telemetry(self, access_token: str, values: dict[str, Any]) -> None:
        r = requests.post(
            f"{self.tb}/api/v1/{access_token}/telemetry",
            json=values,
            timeout=30,
        )
        if r.status_code >= 400:
            LOG.error("telemetry failed %s %s", r.status_code, r.text[:500])

    def post_zone_client_attributes(self, access_token: str, dev_eui: str, zone: str) -> None:
        if dev_eui.lower() in self._zones_sent:
            return
        r = requests.post(
            f"{self.tb}/api/v1/{access_token}/attributes",
            json={"zone": zone},
            timeout=30,
        )
        if r.status_code < 400:
            self._zones_sent.add(dev_eui.lower())
        else:
            LOG.warning("client attributes (zone) failed %s %s", r.status_code, r.text[:300])


def run_mqtt(bridge: TbBridge) -> None:
    host = os.environ.get("MQTT_HOST", "localhost")
    port = int(os.environ.get("MQTT_PORT", "1884"))

    bridge.wait_until_ready()
    bridge.resolve_profiles()

    def on_connect(client, _userdata, _flags, reason_code, _props=None):  # noqa: ANN001
        rc = getattr(reason_code, "value", reason_code)
        if rc == 0:
            LOG.info("MQTT connected %s:%s, subscribing %s", host, port, TOPIC_FILTER)
            client.subscribe(TOPIC_FILTER, qos=1)
        else:
            LOG.error("MQTT connect failed rc=%s", rc)

    def on_message(_c, _u, msg):  # noqa: ANN001
        if not msg.payload:
            return
        try:
            eui, _human, telem = decode_uplink_payload(msg.payload)
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as ex:
            LOG.debug("skip non-json or bad payload: %s", ex)
            return
        if not eui:
            LOG.debug("skip uplink without devEui")
            return
        if not telem:
            LOG.warning(
                "event/up on %s: no telemetry (install ChirpStack codec or check object/data). "
                "First 120 chars: %r",
                msg.topic,
                msg.payload[:120],
            )
            return
        z = zone_for_eui(eui)
        try:
            token = bridge.ensure_token(eui, z)
            bridge.post_zone_client_attributes(token, eui, z)
            bridge.post_telemetry(token, telem)
            LOG.info("TB telemetry ok devEUI=%s keys=%s", eui, list(telem.keys()))
        except requests.HTTPError as ex:
            LOG.error("ThingsBoard API error for %s: %s", eui, ex)
        except Exception as ex:  # noqa: BLE001
            LOG.exception("uplink handler failed %s: %s", eui, ex)

    client_id = os.environ.get("TB_BRIDGE_MQTT_CLIENT_ID") or f"tb-bridge-{uuid.uuid4().hex[:12]}"
    c = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
    )
    c.on_connect = on_connect
    c.on_message = on_message
    c.connect(host, port, keepalive=30)
    c.loop_forever()


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stdout,
    )
    b = TbBridge()
    run_mqtt(b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
