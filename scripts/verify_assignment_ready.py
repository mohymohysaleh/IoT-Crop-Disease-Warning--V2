#!/usr/bin/env python3
"""
Pre-submission checks for Assignment 2 (ThingsBoard track).

  - Static: required repo files, recommended ThingsBoard export JSON under artifacts/exports.
  - Optional --tb: login to ThingsBoard REST and verify devices + sample telemetry.
  - Optional --docker: docker compose ps in chirpstack/chirpstack-docker.

Usage:
  py -3 scripts/verify_assignment_ready.py
  py -3 scripts/verify_assignment_ready.py --tb --docker

Does NOT configure rule chains, dashboards, mail, or OTA (ThingsBoard UI only).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CS_DIR = ROOT / "chirpstack" / "chirpstack-docker"
EXPORT_DIR = ROOT / "thingsboard" / "artifacts" / "exports"

REQUIRED_FILES = [
    "README.md",
    "docs/ASSIGNMENT2_REPORT.md",
    "docs/DEMO_VIDEO_SCRIPT.md",
    "chirpstack/chirpstack-docker/chirpstack_tb_bridge.py",
    "chirpstack/chirpstack-docker/Dockerfile.tb-bridge",
    "thingsboard/rule_engine/disease_risk_script.js",
    "thingsboard/dashboards/FARMER_DASHBOARD.md",
]

def _load_dotenv(path: Path) -> None:
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


def check_required_files(issues: list[str], oks: list[str]) -> None:
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        if p.is_file():
            oks.append(f"file  {rel}")
        else:
            issues.append(f"MISSING required file: {rel}")


def check_exports(warns: list[str], oks: list[str]) -> None:
    if not EXPORT_DIR.is_dir():
        warns.append(f"exports dir missing: {EXPORT_DIR.relative_to(ROOT)}")
        return
    json_files = [p for p in EXPORT_DIR.glob("*.json") if p.is_file()]
    if not json_files:
        warns.append(
            "No JSON in thingsboard/artifacts/exports/ — export dashboard + rule chain from TB UI "
            "(see thingsboard/artifacts/README_ARTIFACT_EXPORTS.md)."
        )
    else:
        oks.append(f"exports: {len(json_files)} .json file(s) in artifacts/exports/")
    # Specific names from FARMER_DASHBOARD.md / README_ARTIFACT_EXPORTS
    if not (EXPORT_DIR / "dashboard_farmer.json").is_file():
        warns.append("Optional for rubric: dashboard_farmer.json not found (export from Dashboards UI).")
    if not list(EXPORT_DIR.glob("rule_chain*.json")):
        warns.append("Optional: rule_chain_*.json not found (export from Rule chains UI).")


def check_thingsboard_rest(warns: list[str], issues: list[str], oks: list[str]) -> None:
    try:
        import requests
    except ImportError:
        warns.append("`requests` not installed; skipped --tb (pip install requests).")
        return

    _load_dotenv(CS_DIR / ".env")

    tb = os.environ.get("TB_URL", "http://localhost:9090").rstrip("/")
    user = os.environ.get("TB_USERNAME", "tenant@thingsboard.org")
    password = os.environ.get("TB_PASSWORD", "tenant")

    try:
        r = requests.post(
            f"{tb}/api/auth/login",
            json={"username": user, "password": password},
            timeout=20,
        )
    except requests.RequestException as e:
        issues.append(f"TB login failed ({tb}): {e}")
        return

    if r.status_code >= 400:
        issues.append(f"TB login HTTP {r.status_code}: {r.text[:200]}")
        return

    tok = (r.json() or {}).get("token")
    if not tok:
        issues.append("TB login: no token in response")
        return

    h = {"Authorization": f"Bearer {tok}"}
    d = requests.get(
        f"{tb}/api/tenant/devices",
        params={"pageSize": 100, "page": 0},
        headers=h,
        timeout=30,
    )
    if d.status_code >= 400:
        issues.append(f"TB /api/tenant/devices HTTP {d.status_code} (use TENANT_ADMIN, not sysadmin)")
        return

    rows = (d.json() or {}).get("data") or []
    by_name = {x.get("name"): x for x in rows}
    exp = [f"000000000000000{i}" for i in range(1, 10)] + ["0000000000000010"]
    missing = [n for n in exp if n not in by_name]
    if missing:
        warns.append(f"TB devices missing ({len(missing)}): e.g. {missing[:3]}... (run bridge + uplinks)")
    else:
        oks.append("TB: all 10 devEUI-named devices present")

    # Sample telemetry on node 1 + 6
    for label in ("0000000000000001", "0000000000000006"):
        if label not in by_name:
            continue
        did = by_name[label].get("id", {}).get("id")
        if not did:
            continue
        t = requests.get(
            f"{tb}/api/plugins/telemetry/DEVICE/{did}/values/timeseries",
            params={"keys": "temperature", "limit": 1},
            headers=h,
            timeout=20,
        )
        if t.status_code >= 400:
            warns.append(f"TB telemetry API {label}: HTTP {t.status_code}")
            continue
        pts = (t.json() or {}).get("temperature") or []
        if not pts:
            warns.append(f"TB: no temperature yet for {label} (needs uplinks through bridge)")
        else:
            oks.append(f"TB: {label} has temperature telemetry")


def check_docker(warns: list[str], issues: list[str], oks: list[str]) -> None:
    compose = CS_DIR / "docker-compose.yml"
    if not compose.is_file():
        issues.append("docker-compose.yml not found")
        return
    try:
        out = subprocess.run(
            ["docker", "compose", "-f", str(compose), "ps", "-a"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(CS_DIR),
        )
    except FileNotFoundError:
        warns.append("docker CLI not found; skipped --docker")
        return
    except subprocess.TimeoutExpired:
        issues.append("docker compose ps timed out")
        return

    if out.returncode != 0:
        issues.append(f"docker compose ps failed: {out.stderr or out.stdout}")
        return

    text = out.stdout or ""
    for line in text.splitlines():
        ln = line.lower()
        if "tb-chirpstack-bridge" in ln and "up" not in ln and "running" not in ln:
            warns.append("tb-chirpstack-bridge line does not look Up — ThingsBoard may miss LoRa telemetry")
            break
    if not text.strip():
        warns.append("docker compose ps: empty output (compose not running?)")
    else:
        oks.append("docker: compose ps succeeded (review for Up: chirpstack, mosquitto, thingsboard, tb-chirpstack-bridge)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Assignment 2 readiness checks")
    ap.add_argument("--tb", action="store_true", help="Query ThingsBoard REST (uses .env TB_* if present)")
    ap.add_argument("--docker", action="store_true", help="Run docker compose ps")
    args = ap.parse_args()

    issues: list[str] = []
    warns: list[str] = []
    oks: list[str] = []

    print("Assignment 2 - verify_assignment_ready.py\n")

    check_required_files(issues, oks)
    check_exports(warns, oks)

    if args.tb:
        check_thingsboard_rest(warns, issues, oks)
    if args.docker:
        check_docker(warns, issues, oks)

    for x in oks:
        print("[ok]", x)
    for x in warns:
        print("[warn]", x)
    for x in issues:
        print("[fail]", x)

    print()
    print("Manual (cannot be scripted here): thingsboard/rule_engine/RULE_CHAIN.md - rule chain in TB UI;")
    print("  Settings -> Mail; dashboard export; OTA package assignment; PDF report; demo video.")
    print()

    if issues:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
