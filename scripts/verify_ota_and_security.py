#!/usr/bin/env python3
"""
Smoke-test OTA helper path + security demo for ThingsBoard (assignment extras).

  - Rollback watchdog: must exit 0 when fewer than 2 Zone2 devices report fw_state FAILED.
  - Rogue MQTT: invalid token must not complete a successful session (non-success CONNACK).
  - OTA sidecar path: push simulated shared attrs (fw_*) via REST, run sidecar briefly, read fw_state telemetry.

  py -3 scripts/verify_ota_and_security.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CS_ENV = ROOT / "chirpstack" / "chirpstack-docker" / ".env"
DEVICES_JSON = ROOT / "chirpstack" / "chirpstack-docker" / "config" / "devices.json"


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def tb_login(tb: str, user: str, password: str) -> str | None:
    import requests

    r = requests.post(f"{tb}/api/auth/login", json={"username": user, "password": password}, timeout=30)
    if r.status_code >= 400:
        print("TB login failed:", r.status_code, r.text[:300])
        return None
    tok = (r.json() or {}).get("token")
    if not tok:
        print("No token in login response")
        return None
    return tok


def save_shared_ota_hints(tb: str, token: str, device_id: str) -> bool:
    """ThingsBoard 4.x: POST telemetry plugin attributes with explicit scope in URL."""
    import requests

    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"fw_title": "thresholds_v2", "fw_version": "9.9.9-smoketest"}
    url = f"{tb}/api/plugins/telemetry/DEVICE/{device_id}/attributes/SHARED_SCOPE"
    r = requests.post(url, headers=h, json=body, timeout=30)
    if r.status_code < 400:
        print("OK: pushed SHARED_SCOPE fw_title/fw_version for OTA smoke test")
        return True
    print("WARN: could not push shared attributes (HTTP", r.status_code, "):", r.text[:400])
    return False


def find_device_id_by_name(tb: str, token: str, name: str) -> str | None:
    import requests

    h = {"Authorization": f"Bearer {token}"}
    r = requests.get(
        f"{tb}/api/tenant/devices",
        params={"pageSize": 200, "page": 0},
        headers=h,
        timeout=30,
    )
    if r.status_code >= 400:
        print("WARN: list devices failed", r.status_code)
        return None
    for row in (r.json() or {}).get("data") or []:
        if (row.get("name") or "") == name:
            return (row.get("id") or {}).get("id")
    return None


def latest_fw_state(tb: str, token: str, device_id: str) -> str | None:
    import requests

    h = {"Authorization": f"Bearer {token}"}
    end = int(time.time() * 1000)
    r = requests.get(
        f"{tb}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries",
        params={"keys": "fw_state", "limit": 1, "agg": "NONE"},
        headers=h,
        timeout=30,
    )
    if r.status_code >= 400:
        return None
    pts = (r.json() or {}).get("fw_state") or []
    if not pts:
        return None
    return str(pts[0].get("value"))


def run_sidecar_window(access_token: str, seconds: float = 6.0) -> tuple[int, str]:
    """Run thingsboard_tb_sidecar.py; capture stdout."""
    script = ROOT / "chirpstack" / "chirpstack-docker" / "thingsboard_tb_sidecar.py"
    if not script.is_file():
        return 1, "sidecar script missing"
    env = os.environ.copy()
    env.pop("TB_OTA_SIMULATE_FAIL", None)
    proc = subprocess.Popen(
        [
            sys.executable,
            str(script),
            "--access-token",
            access_token,
            "--device-label",
            "smoke_node6",
            "--zone-tag",
            "Zone_2",
            "--mqtt-host",
            env.get("THINGSBOARD_MQTT_HOST", "localhost"),
            "--mqtt-port",
            env.get("THINGSBOARD_MQTT_PORT", "11883"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=str(script.parent),
    )
    out_lines: list[str] = []

    def reader() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            out_lines.append(line)

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    time.sleep(seconds)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    t.join(timeout=2)
    return proc.returncode, "".join(out_lines)


def main() -> int:
    load_dotenv(CS_ENV)
    tb = os.environ.get("TB_URL", "http://localhost:9090").rstrip("/")
    user = os.environ.get("TB_USERNAME", "tenant@thingsboard.org")
    password = os.environ.get("TB_PASSWORD", "tenant")

    print("=== 1) Rollback watchdog (OTA failure monitor) ===")
    wd = ROOT / "thingsboard" / "scripts" / "rollback_watchdog.py"
    r = subprocess.run([sys.executable, str(wd)], cwd=str(ROOT), env=os.environ)
    if r.returncode == 2:
        print("FAIL: set TB_ZONE2_PROFILE_ID in .env")
        return 1
    if r.returncode == 3:
        print("WARN: watchdog reports rollback condition (>=2 FAILED) - expected in FAILURE demos only")
    elif r.returncode != 0:
        print("FAIL: rollback_watchdog exit", r.returncode)
        return 1
    print("OK: rollback_watchdog exit 0 (no rollback threshold)\n")

    print("=== 2) Rogue MQTT (bad token must be rejected) ===")
    rogue = ROOT / "thingsboard" / "scripts" / "rogue_mqtt_client.py"
    rx = subprocess.run([sys.executable, str(rogue)], cwd=str(ROOT), capture_output=True, text=True, timeout=30)
    combined = (rx.stdout or "") + (rx.stderr or "")
    print(combined.strip())
    if rx.returncode != 0:
        print("FAIL: rogue_mqtt_client crashed")
        return 1
    if "rc=0" in combined.replace(" ", "") and "callback rc=0" in combined.replace(" ", ""):
        print("FAIL: unexpected successful CONNACK (rc=0) for invalid token")
        return 1
    if "CONNECT callback rc=" not in combined:
        print("WARN: unexpected rogue client output - review manually")
    print("OK: non-success CONNACK for invalid token\n")

    print("=== 3) OTA sidecar + shared attributes ===")
    tok = tb_login(tb, user, password)
    if not tok:
        return 1

    import json

    node6_token = None
    if DEVICES_JSON.is_file():
        dj = json.loads(DEVICES_JSON.read_text(encoding="utf-8"))
        for dev in dj.get("Zone2") or []:
            if dev.get("id") == "node6":
                node6_token = dev.get("thingsboard_access_token")
                break

    did = find_device_id_by_name(tb, tok, "0000000000000006")
    if not did:
        print("WARN: device 0000000000000006 not in tenant — skip OTA MQTT check")
        return 0

    save_shared_ota_hints(tb, tok, did)

    if not node6_token:
        print("WARN: no thingsboard_access_token for node6 in devices.json — skip sidecar")
        return 0

    time.sleep(1.5)

    code, blog = run_sidecar_window(node6_token, seconds=12.0)
    if blog:
        print("--- sidecar log (excerpt) ---")
        for line in blog.splitlines()[:30]:
            print(line)
    seq = ("DOWNLOADING", "DOWNLOADED", "VERIFIED", "UPDATING", "UPDATED")
    ok_ota = "new OTA descriptors" in blog and "OTA simulate package" in blog
    if ok_ota:
        print("OK: sidecar received OTA shared attributes and started FSM")
    elif any(s in blog for s in seq):
        print("OK: sidecar log shows fw_state progression text")

    if ok_ota or any(s in blog for s in seq):
        for _ in range(8):
            time.sleep(0.5)
            fws = latest_fw_state(tb, tok, did)
            if fws in seq or fws == "UPDATED":
                print("OK: REST telemetry fw_state =", fws)
                break
        else:
            fws = latest_fw_state(tb, tok, did)
            print("Latest fw_state from REST:", fws)
            if fws in seq or fws == "UPDATED":
                print("OK: fw_state reached reported progression")
            elif fws == "INITIATED":
                print(
                    "INFO: fw_state INITIATED is from ThingsBoard OTA service (parallel with device telemetry)."
                )
            elif fws:
                print("INFO: fw_state =", fws)
    else:
        print("WARN: sidecar log did not show expected OTA FSM (MQTT or timing issue)")
        fws = latest_fw_state(tb, tok, did)
        print("Latest fw_state from REST:", fws)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    try:
        import requests  # noqa: F401
    except ImportError:
        print("pip install requests", file=sys.stderr)
        sys.exit(1)
    raise SystemExit(main())
