#!/usr/bin/env python3
"""
Export ThingsBoard rule chain(s) and dashboard JSON for submission.

Reads TB_URL, TB_USERNAME, TB_PASSWORD from chirpstack/chirpstack-docker/.env (if present).

To create the Disease Risk rule chain and Farmer Crop Risk dashboard on the server, run first:

  py -3 scripts/provision_tb_assignment.py

Writes:
  thingsboard/artifacts/exports/rule_chain_<sanitized_name>.json  (chain entity)
  thingsboard/artifacts/exports/rule_chain_<sanitized_name>_metadata.json  (nodes + wiring)
  thingsboard/artifacts/exports/dashboard_<sanitized_name>.json

If multiple chains/dashboards exist, exports all (or match by substring env TB_EXPORT_MATCH).

Usage:
  py -3 scripts/export_tb_artifacts.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / "chirpstack" / "chirpstack-docker" / ".env"
OUT_DIR = ROOT / "thingsboard" / "artifacts" / "exports"


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


def slug(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return s.lower() or "export"


def create_minimal_farmer_dashboard(tb: str, headers: dict) -> bool:
    """POST empty 'Farmer Crop Risk' dashboard if none exists (placeholder for FARMER_DASHBOARD.md)."""
    listing = requests.get(
        f"{tb}/api/tenant/dashboards",
        params={"pageSize": 100, "page": 0},
        headers=headers,
        timeout=30,
    )
    if listing.status_code >= 400:
        return False
    for row in (listing.json() or {}).get("data") or []:
        title = (row.get("title") or row.get("name") or "").lower()
        if "farmer" in title:
            return False
    body = {
        "title": "Farmer Crop Risk",
        "configuration": {
            "description": "",
            "widgets": {},
            "layouts": {
                "main": {
                    "widgets": {},
                    "gridSettings": {
                        "layoutType": "default",
                        "columns": 24,
                        "margin": 10,
                        "outerMargin": True,
                    },
                }
            },
            "entityAliases": {},
            "filters": {},
            "settings": {},
            "timewindow": {
                "hideAggregation": False,
                "hideAggInterval": False,
                "hideTimezone": False,
                "selectedTab": 0,
                "realtime": {"realtimeType": 0, "interval": 1000, "timewindowMs": 60000},
                "aggregation": {"type": "NONE", "limit": 25000},
            },
        },
    }
    pr = requests.post(f"{tb}/api/dashboard", headers=headers, json=body, timeout=30)
    if pr.status_code >= 400:
        print("Could not create Farmer Crop Risk placeholder:", pr.status_code, pr.text[:300])
        return False
    print("Created placeholder dashboard: Farmer Crop Risk (add widgets in TB UI per FARMER_DASHBOARD.md)")
    return True


def main() -> int:
    load_dotenv(ENV_PATH)
    tb = os.environ.get("TB_URL", "http://localhost:9090").rstrip("/")
    user = os.environ.get("TB_USERNAME", "tenant@thingsboard.org")
    password = os.environ.get("TB_PASSWORD", "tenant")
    match_sub = os.environ.get("TB_EXPORT_MATCH", "").strip().lower()

    r = requests.post(
        f"{tb}/api/auth/login",
        json={"username": user, "password": password},
        timeout=30,
    )
    if r.status_code >= 400:
        print("TB login failed:", r.status_code, r.text[:400])
        return 1
    token = (r.json() or {}).get("token")
    if not token:
        print("No token")
        return 1

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Ensure submission filename dashboard_farmer.json exists (minimal placeholder ok)
    create_minimal_farmer_dashboard(tb, headers)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Rule chains
    rc_list = requests.get(
        f"{tb}/api/ruleChains",
        params={"pageSize": 100, "page": 0},
        headers=headers,
        timeout=30,
    )
    if rc_list.status_code >= 400:
        print("ruleChains list failed:", rc_list.status_code, rc_list.text[:300])
        return 1

    chains = (rc_list.json() or {}).get("data") or []
    if not chains:
        print("No rule chains in tenant — create Disease Risk chain in UI first (RULE_CHAIN.md).")
    exported_rc = 0
    for row in chains:
        name = row.get("name") or "chain"
        if match_sub and match_sub not in name.lower():
            continue
        cid = row.get("id", {}).get("id")
        if not cid:
            continue
        detail = requests.get(f"{tb}/api/ruleChain/{cid}", headers=headers, timeout=30)
        if detail.status_code >= 400:
            print("skip rule chain", name, detail.status_code)
            continue
        body = detail.json()
        fn = OUT_DIR / f"rule_chain_{slug(name)}.json"
        fn.write_text(json.dumps(body, indent=2), encoding="utf-8")
        print("Wrote", fn.relative_to(ROOT))
        meta = requests.get(f"{tb}/api/ruleChain/{quote(cid, safe='')}/metadata", headers=headers, timeout=30)
        if meta.status_code < 400:
            mj = meta.json() or {}
            nodes = mj.get("nodes")
            if nodes:
                meta_fn = OUT_DIR / f"rule_chain_{slug(name)}_metadata.json"
                meta_fn.write_text(json.dumps(mj, indent=2), encoding="utf-8")
                print("Wrote", meta_fn.relative_to(ROOT))
            else:
                print(
                    "Skip rule chain metadata export (GET returned no nodes; use",
                    "rule_chain_disease_risk_engine.provisioned_metadata.json",
                    "after scripts/provision_tb_assignment.py).",
                )
        exported_rc += 1

    if exported_rc == 0 and chains:
        print("No rule chain matched TB_EXPORT_MATCH; clearing filter exports all.")
        for row in chains:
            name = row.get("name") or "chain"
            cid = row.get("id", {}).get("id")
            if not cid:
                continue
            detail = requests.get(f"{tb}/api/ruleChain/{cid}", headers=headers, timeout=30)
            if detail.status_code >= 400:
                continue
            fn = OUT_DIR / f"rule_chain_{slug(name)}.json"
            fn.write_text(json.dumps(detail.json(), indent=2), encoding="utf-8")
            print("Wrote", fn.relative_to(ROOT))
            meta = requests.get(f"{tb}/api/ruleChain/{quote(cid, safe='')}/metadata", headers=headers, timeout=30)
            if meta.status_code < 400:
                mj = meta.json() or {}
                if mj.get("nodes"):
                    meta_fn = OUT_DIR / f"rule_chain_{slug(name)}_metadata.json"
                    meta_fn.write_text(json.dumps(mj, indent=2), encoding="utf-8")
                    print("Wrote", meta_fn.relative_to(ROOT))
            exported_rc += 1

    # Dashboards (tenant list returns thin rows; fetch full dashboard by id)
    dash_list = requests.get(
        f"{tb}/api/tenant/dashboards",
        params={"pageSize": 100, "page": 0},
        headers=headers,
        timeout=30,
    )
    if dash_list.status_code >= 400:
        print("tenant/dashboards failed:", dash_list.status_code, dash_list.text[:300])
        return 1 if exported_rc == 0 else 0

    boards = (dash_list.json() or {}).get("data") or []
    if not boards:
        print("No dashboards — create Farmer dashboard in UI (FARMER_DASHBOARD.md).")
        return 0 if exported_rc else 0

    exported_db = 0
    for row in boards:
        name = row.get("name") or "dashboard"
        if match_sub and match_sub not in name.lower():
            continue
        did = row.get("id", {}).get("id")
        if not did:
            continue
        # Home dashboard uses /api/dashboard/home/{dashboardId} in some TB versions;
        # standard fetch:
        durl = f"{tb}/api/dashboard/{quote(did, safe='')}"
        dget = requests.get(durl, headers=headers, timeout=30)
        if dget.status_code >= 400:
            print("dashboard get failed", name, dget.status_code)
            continue
        body = dget.json()
        base = "dashboard_farmer" if "farmer" in name.lower() else f"dashboard_{slug(name)}"
        fn = OUT_DIR / f"{base}.json"
        fn.write_text(json.dumps(body, indent=2), encoding="utf-8")
        print("Wrote", fn.relative_to(ROOT))
        exported_db += 1

    if exported_db == 0 and boards:
        for row in boards:
            name = row.get("name") or "dashboard"
            did = row.get("id", {}).get("id")
            if not did:
                continue
            dget = requests.get(f"{tb}/api/dashboard/{quote(did, safe='')}", headers=headers, timeout=30)
            if dget.status_code >= 400:
                continue
            base = "dashboard_farmer" if "farmer" in name.lower() else f"dashboard_{slug(name)}"
            fn = OUT_DIR / f"{base}.json"
            fn.write_text(json.dumps(dget.json(), indent=2), encoding="utf-8")
            print("Wrote", fn.relative_to(ROOT))
            exported_db += 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
