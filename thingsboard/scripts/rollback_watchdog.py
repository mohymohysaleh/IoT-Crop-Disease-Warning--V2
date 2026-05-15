#!/usr/bin/env python3
"""
Poll Zone2_Sensor devices for fw_state == FAILED and trigger operator alert / optional REST cleanup.
Run on the host (not inside Docker) with tenant credentials.

Environment:
  TB_URL                e.g. http://localhost:9090
  TB_USERNAME           default tenant@thingsboard.org (create in UI) or sysadmin@thingsboard.org
  TB_PASSWORD
  TB_ZONE2_PROFILE_ID   UUID of Zone2_Sensor device profile (Settings → Device profiles)
"""
from __future__ import annotations

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

import os
import sys
import time
from typing import Any

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

TB_URL = os.environ.get("TB_URL", "http://localhost:9090").rstrip("/")
USER = os.environ.get("TB_USERNAME", "tenant@thingsboard.org")
PASSWORD = os.environ.get("TB_PASSWORD", "tenant")
ZONE2_PROFILE = os.environ.get("TB_ZONE2_PROFILE_ID")


def login() -> str:
    r = requests.post(
        f"{TB_URL}/api/auth/login",
        json={"username": USER, "password": PASSWORD},
        timeout=30,
    )
    r.raise_for_status()
    tok = r.json().get("token")
    if not tok:
        raise RuntimeError(r.text)
    return tok


def auth_headers(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


def list_zone2_devices(tok: str, profile_id: str) -> list[dict[str, Any]]:
    r = requests.get(
        f"{TB_URL}/api/tenant/devices",
        params={
            "pageSize": 100,
            "page": 0,
            "type": "",
            "textSearch": "",
            "sortProperty": "name",
            "sortOrder": "ASC",
            "deviceProfileId": profile_id,
        },
        headers=auth_headers(tok),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json().get("data") or []
    return data


def latest_fw_state(tok: str, device_id: str) -> tuple[str | None, str | None]:
    """Return (fw_state, fw_version) from latest telemetry."""
    end = int(time.time() * 1000)
    start = end - 86400_000 * 14
    keys = ",".join(["fw_state", "fw_version"])
    r = requests.get(
        f"{TB_URL}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries",
        params={
            "keys": keys,
            "interval": "0",
            "limit": 1,
            "agg": "NONE",
            "order": "DESC",
            "startTs": start,
            "endTs": end,
            "useStrictDataTypes": "false",
        },
        headers=auth_headers(tok),
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    fw_st = None
    fw_ver = None
    if isinstance(body.get("fw_state"), list) and body["fw_state"]:
        fw_st = body["fw_state"][0].get("value")
    if isinstance(body.get("fw_version"), list) and body["fw_version"]:
        fw_ver = body["fw_version"][0].get("value")
    return fw_st, fw_ver


def main() -> int:
    if not ZONE2_PROFILE:
        print("Set TB_ZONE2_PROFILE_ID to the UUID of Zone2_Sensor profile.", file=sys.stderr)
        return 2

    tok = login()
    devices = list_zone2_devices(tok, ZONE2_PROFILE)
    failures: list[str] = []
    for row in devices:
        did = row["id"]["id"]
        name = row.get("name") or did
        st, fv = latest_fw_state(tok, did)
        if st == "FAILED":
            failures.append(f"{name} ({did}) fw_version={fv}")
    print(f"Zone2 devices scanned: {len(devices)}, FAILED: {len(failures)}")
    for line in failures:
        print("  ", line)

    if len(failures) >= 2:
        print("\nRollback condition met (≥2 FAILED). Recommended actions:")
        print("  1) ThingsBoard UI → Device profiles → Zone2_Sensor → remove assigned OTA firmware.")
        print("  2) Re-assign previous firmware baseline or downgrade shared threshold attributes.")
        print("  3) Re-run integrations after resetting devices (optional).")
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
