#!/usr/bin/env python3
"""
Validate ThingsBoard provisioning: rule chain entry point, profile assignment, dashboard.

Reads TB_URL, TB_USERNAME, TB_PASSWORD from chirpstack/chirpstack-docker/.env (if present).

  py -3 scripts/verify_tb_assignment.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / "chirpstack" / "chirpstack-docker" / ".env"

RULE_CHAIN_NAME = os.environ.get("TB_RULE_CHAIN_NAME", "Disease Risk Engine")
DASHBOARD_TITLE = os.environ.get("TB_FARMER_DASHBOARD_TITLE", "Farmer Crop Risk")
ZONE_TYPES = ("Zone1_Sensor", "Zone2_Sensor")
EXPECTED_NODES = 8


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


def tb_login(tb: str, user: str, password: str) -> dict | None:
    r = requests.post(f"{tb}/api/auth/login", json={"username": user, "password": password}, timeout=30)
    if r.status_code >= 400:
        print("TB login failed:", r.status_code, r.text[:400])
        return None
    token = (r.json() or {}).get("token")
    if not token:
        print("No token in login response")
        return None
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def main() -> int:
    load_dotenv(ENV_PATH)
    tb = os.environ.get("TB_URL", "http://localhost:9090").rstrip("/")
    user = os.environ.get("TB_USERNAME", "tenant@thingsboard.org")
    password = os.environ.get("TB_PASSWORD", "tenant")

    headers = tb_login(tb, user, password)
    if not headers:
        return 1

    ok = True

    vi = requests.get(f"{tb}/api/system/info", headers=headers, timeout=30)
    if vi.status_code < 400:
        body = vi.json() or {}
        ver = body.get("thingsboardVersion") or body.get("tbVersion") or body.get("version")
        print("ThingsBoard:", ver or body)
    else:
        print("GET /api/system/info:", vi.status_code, "(continuing)")

    rc_list = requests.get(f"{tb}/api/ruleChains", params={"pageSize": 100, "page": 0}, headers=headers, timeout=30)
    chain_id = None
    if rc_list.status_code < 400:
        for row in (rc_list.json() or {}).get("data") or []:
            if (row.get("name") or "") == RULE_CHAIN_NAME:
                chain_id = (row.get("id") or {}).get("id")
                break
    if not chain_id:
        print("FAIL: rule chain", repr(RULE_CHAIN_NAME), "not found")
        return 1
    print("Rule chain id:", chain_id)

    gr = requests.get(f"{tb}/api/ruleChain/{chain_id}", headers=headers, timeout=30)
    if gr.status_code >= 400:
        print("FAIL: GET ruleChain", gr.status_code)
        return 1
    first = (gr.json() or {}).get("firstRuleNodeId") or {}
    if not first.get("id"):
        print("FAIL: firstRuleNodeId is not set - chain will not run from Input")
        ok = False
    else:
        print("OK: firstRuleNodeId is set")

    meta = requests.get(f"{tb}/api/ruleChain/{chain_id}/metadata", headers=headers, timeout=60)
    if meta.status_code >= 400:
        print("FAIL: GET ruleChain metadata", meta.status_code)
        ok = False
    else:
        nodes = (meta.json() or {}).get("nodes") or []
        n = len(nodes)
        if n == 0:
            print(
                "FAIL: GET /api/ruleChain/.../metadata returned 0 rule nodes (rule_node table may also be empty). "
                "thingsboard/tb-postgres:latest has been seen to accept POST /metadata with HTTP 200 but not insert rows - "
                "use image thingsboard/tb-postgres:4.2.1.1 in docker-compose and recreate the container, then re-run "
                "scripts/provision_tb_assignment.py. "
                "If it still fails: Rule chains - Import - rule_chain_disease_risk_engine.provisioned_metadata.json "
                "or build the chain manually (RULE_CHAIN.md). "
                "Ensure Save attributes uses TbMsgAttributesNode on TB 4.2+ (see provision script)."
            )
            ok = False
        elif n < EXPECTED_NODES:
            print(f"WARN: metadata has {n} nodes (expected {EXPECTED_NODES})")
        else:
            print(f"OK: metadata reports {n} rule nodes")

    dpi = requests.get(
        f"{tb}/api/deviceProfileInfos",
        params={"pageSize": 100, "page": 0},
        headers=headers,
        timeout=30,
    )
    if dpi.status_code >= 400:
        print("WARN: deviceProfileInfos failed", dpi.status_code)
    else:
        name_to_id: dict[str, str] = {}
        for row in (dpi.json() or {}).get("data") or []:
            nm = row.get("name")
            pid = (row.get("id") or {}).get("id")
            if nm and pid:
                name_to_id[nm] = pid
        for z in ZONE_TYPES:
            pid = name_to_id.get(z)
            if not pid:
                print(f"WARN: device profile {z!r} not found")
                ok = False
                continue
            pr = requests.get(f"{tb}/api/deviceProfile/{pid}", headers=headers, timeout=30)
            if pr.status_code >= 400:
                print("WARN: GET deviceProfile", z, pr.status_code)
                ok = False
                continue
            drc = ((pr.json() or {}).get("defaultRuleChainId") or {}).get("id")
            if drc != chain_id:
                print(f"FAIL: profile {z!r} defaultRuleChainId={drc!r} expected {chain_id!r}")
                ok = False
            else:
                print(f"OK: profile {z} uses Disease Risk Engine")

    dash = requests.get(f"{tb}/api/tenant/dashboards", params={"pageSize": 100, "page": 0}, headers=headers, timeout=30)
    if dash.status_code >= 400:
        print("WARN: list dashboards failed", dash.status_code)
    else:
        titles = [(row.get("title") or row.get("name") or "") for row in (dash.json() or {}).get("data") or []]
        if DASHBOARD_TITLE not in titles:
            print("FAIL: dashboard", repr(DASHBOARD_TITLE), "not found")
            ok = False
        else:
            print("OK: dashboard", repr(DASHBOARD_TITLE), "exists")

    if ok:
        print("Verification: all critical checks passed.")
        return 0
    print("Verification: finished with failures (see above).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
