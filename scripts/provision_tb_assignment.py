#!/usr/bin/env python3
"""
Provision ThingsBoard Disease Risk rule chain + Farmer Crop Risk dashboard (CE) via REST.

Reads TB_URL, TB_USERNAME, TB_PASSWORD from chirpstack/chirpstack-docker/.env (if present).

  py -3 scripts/provision_tb_assignment.py
  py -3 scripts/provision_tb_assignment.py --dashboard-only
  py -3 scripts/provision_tb_assignment.py --rule-chain-only
  py -3 scripts/provision_tb_assignment.py --no-assign-profiles

Requires a Tenant Administrator (not SYS_ADMIN). After success, run:

  py -3 scripts/export_tb_artifacts.py

**First-time rule chain save:** omit rule node `id` fields in POST /api/ruleChain/metadata when the chain
has no nodes in the database yet; otherwise ThingsBoard's DAO never adds them (HTTP 200, empty graph).
The script does this automatically (see meta_for_rule_chain_rest_save).

Limitations: rule engine node types must match your ThingsBoard version.
CE **3.2.x/3.3.x** need **legacy** nodes: TbSaveTimeseriesNode and classic Save attributes **without**
extended processingSettings. **ThingsBoard 4.2+ CE images** use **TbMsgAttributesNode** (telemetry
package) for “save attributes”; **TbSaveAttributesNode** may be absent (`ClassNotFoundException`) and
then REST metadata saves return **empty nodes** — the UI shows only **Input**.

The script calls GET /api/system/info
to pick the layout; set TB_FORCE_LEGACY_RULE_NODES=1 to force legacy.

ThingsBoard 4.2+ uses TbMsgTimeseriesNode with processingSettings; time-series widgets need
full settings.yAxes on 4.2+ or charts throw JavaScript errors in the UI (older TB uses simpler
chart settings). Save Attributes only accepts POST_ATTRIBUTES_REQUEST — after the disease script
we fan out: Save Timeseries (telemetry), a small transform → POST_ATTRIBUTES + Save Attributes
riskEngineState, and the alarm JS filter (all from the same transform output).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / "chirpstack" / "chirpstack-docker" / ".env"
SCRIPT_JS = ROOT / "thingsboard" / "rule_engine" / "disease_risk_script.js"
LAST_META_SNAPSHOT = (
    ROOT / "thingsboard" / "artifacts" / "exports" / "rule_chain_disease_risk_engine.provisioned_metadata.json"
)
UI_IMPORT_BUNDLE = (
    ROOT / "thingsboard" / "artifacts" / "exports" / "rule_chain_disease_risk_engine.import.json"
)

RULE_CHAIN_NAME = os.environ.get("TB_RULE_CHAIN_NAME", "Disease Risk Engine")
DASHBOARD_TITLE = os.environ.get("TB_FARMER_DASHBOARD_TITLE", "Farmer Crop Risk")
ALARM_TYPE = os.environ.get("TB_FARMER_ALARM_TYPE", "High crop risk")
ZONE1_TYPE = "Zone1_Sensor"
ZONE2_TYPE = "Zone2_Sensor"

ALARM_DETAILS_BUILD_JS = (
    "var details = {};\n"
    "if (metadata.prevAlarmDetails) {\n"
    " details = JSON.parse(metadata.prevAlarmDetails);\n"
    " delete metadata.prevAlarmDetails;\n"
    "}\n"
    "return details;"
)


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
    r = requests.post(
        f"{tb}/api/auth/login",
        json={"username": user, "password": password},
        timeout=30,
    )
    if r.status_code >= 400:
        print("TB login failed:", r.status_code, r.text[:400])
        return None
    token = (r.json() or {}).get("token")
    if not token:
        print("No token in login response")
        return None
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def load_disease_script() -> str:
    if not SCRIPT_JS.is_file():
        raise SystemExit(f"Missing {SCRIPT_JS}")
    return SCRIPT_JS.read_text(encoding="utf-8")


def parse_semver_loose(s: str) -> tuple[int, int, int] | None:
    s = (s or "").strip()
    if not s:
        return None
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", s)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.match(r"(\d+)\.(\d+)", s)
    if m:
        return int(m.group(1)), int(m.group(2)), 0
    return None


def extract_tb_version_from_payload(body: object) -> tuple[int, int, int] | None:
    key_order = ("thingsboardVersion", "tbVersion", "productVersion", "version")
    if isinstance(body, dict):
        for k in key_order:
            v = body.get(k)
            if isinstance(v, str):
                p = parse_semver_loose(v)
                if p:
                    return p
        for v in body.values():
            if isinstance(v, (dict, list)):
                p = extract_tb_version_from_payload(v)
                if p:
                    return p
    elif isinstance(body, list):
        for x in body:
            p = extract_tb_version_from_payload(x)
            if p:
                return p
    return None


def get_thingsboard_version(tb: str, headers: dict) -> tuple[int, int, int] | None:
    """Best-effort parse from GET /api/system/info (tenant token works on CE)."""
    base = tb.rstrip("/")
    try:
        r = requests.get(f"{base}/api/system/info", headers=headers, timeout=30)
    except requests.RequestException:
        return None
    if r.status_code >= 400:
        return None
    return extract_tb_version_from_payload(r.json() or {})


def use_legacy_rule_nodes(version: tuple[int, int, int] | None) -> bool:
    """Before ~3.4, TbMsgTimeseriesNode / attribute processingSettings are not available."""
    if version is None:
        return False
    major, minor, _ = version
    if major < 3:
        return True
    if major > 3:
        return False
    return minor < 4


def use_tb42_chart_schema(version: tuple[int, int, int] | None) -> bool:
    """TB 4.2+ time-series widgets require settings.yAxes; TB 3.x / 4.0–4.1 use a slimmer schema."""
    if version is None:
        return True
    major, minor, _patch = version
    if major > 4:
        return True
    if major < 4:
        return False
    if minor > 2:
        return True
    if minor < 2:
        return False
    return True  # 4.2.x


# Wrap server JSON state as POST_ATTRIBUTES_REQUEST (Save Attributes rejects POST_TELEMETRY_REQUEST).
RISK_STATE_TO_ATTRS_JS = (
    "return {\n"
    "  msg: { riskEngineState: msg.riskEngineState },\n"
    "  metadata: metadata,\n"
    "  msgType: 'POST_ATTRIBUTES_REQUEST'\n"
    "};"
)


def meta_for_rule_chain_rest_save(meta: dict, *, existing_node_count: int) -> dict:
    """
    ThingsBoard DAO only inserts new rule nodes when id is null, or when updating an existing
    stored node. If the chain has zero rows in rule_node but the JSON includes client UUIDs,
    saveRuleChainMetaData runs with an empty toAddOrUpdate list and persists nothing (HTTP 200).
    Strip ids for first-time (empty) saves so the server assigns ids.
    """
    out = json.loads(json.dumps(meta))
    if existing_node_count == 0:
        for n in out.get("nodes") or []:
            n.pop("id", None)
    return out


def build_rule_chain_metadata(chain_id: str, node_ids: list[str], *, legacy: bool = False) -> dict:
    """Rule chain with fan-out from disease script (TB Save Attributes requires POST_ATTRIBUTES_REQUEST)."""
    if len(node_ids) != 8:
        raise ValueError("expected 8 rule node ids")
    rc = {"entityType": "RULE_CHAIN", "id": chain_id}
    n = node_ids

    def nid(i: int) -> dict:
        return {"entityType": "RULE_NODE", "id": n[i]}

    # TB 3.2: TbSaveAttributesNode + scope-only config. TB 4.x CE: TbMsgAttributesNode + processingSettings.
    if legacy:
        save_attrs_type = "org.thingsboard.rule.engine.action.TbSaveAttributesNode"
        save_attrs_configuration: dict = {
            "scope": "SERVER_SCOPE",
            "notifyDevice": False,
            "sendAttributesUpdatedNotification": True,
            "updateAttributesOnlyOnValueChange": False,
        }
    else:
        save_attrs_type = "org.thingsboard.rule.engine.telemetry.TbMsgAttributesNode"
        save_attrs_configuration = {
            "processingSettings": {"type": "ON_EVERY_MESSAGE"},
            "scope": "SERVER_SCOPE",
            "notifyDevice": False,
            "sendAttributesUpdatedNotification": True,
            "updateAttributesOnlyOnValueChange": False,
        }

    if legacy:
        timeseries_type = "org.thingsboard.rule.engine.telemetry.TbSaveTimeseriesNode"
        timeseries_configuration: dict = {"defaultTTL": 0}
    else:
        timeseries_type = "org.thingsboard.rule.engine.telemetry.TbMsgTimeseriesNode"
        timeseries_configuration = {
            "defaultTTL": 0,
            "useServerTs": False,
            "processingSettings": {"type": "ON_EVERY_MESSAGE"},
        }

    nodes = [
        {
            "id": nid(0),
            "ruleChainId": rc,
            "type": "org.thingsboard.rule.engine.filter.TbMsgTypeFilterNode",
            "name": "Only telemetry",
            "debugMode": False,
            "configuration": {"messageTypes": ["POST_TELEMETRY_REQUEST"]},
            "additionalInfo": {"description": "", "layoutX": 100, "layoutY": 50},
        },
        {
            "id": nid(1),
            "ruleChainId": rc,
            "type": "org.thingsboard.rule.engine.metadata.TbGetAttributesNode",
            "name": "Get riskEngineState",
            "debugMode": False,
            "configuration": {
                "tellFailureIfAbsent": False,
                "clientAttributeNames": [],
                "sharedAttributeNames": [],
                "serverAttributeNames": ["riskEngineState"],
                "latestTsKeyNames": [],
                "getLatestValueWithTs": False,
                "fetchTo": "METADATA",
            },
            "additionalInfo": {"layoutX": 300, "layoutY": 50},
        },
        {
            "id": nid(2),
            "ruleChainId": rc,
            "type": "org.thingsboard.rule.engine.transform.TbTransformMsgNode",
            "name": "Disease risk script",
            "debugMode": False,
            "configuration": {
                "scriptLang": "JS",
                "jsScript": load_disease_script(),
                "tbelScript": "return {msg: msg, metadata: metadata, msgType: msgType};",
            },
            "additionalInfo": {"description": disease_risk_script_digest(), "layoutX": 500, "layoutY": 50},
        },
        {
            "id": nid(3),
            "ruleChainId": rc,
            "type": timeseries_type,
            "name": "Save timeseries",
            "debugMode": False,
            "configuration": timeseries_configuration,
            "additionalInfo": {"layoutX": 720, "layoutY": 50},
        },
        {
            "id": nid(4),
            "ruleChainId": rc,
            "type": "org.thingsboard.rule.engine.transform.TbTransformMsgNode",
            "name": "Risk state to POST_ATTRIBUTES",
            "debugMode": False,
            "configuration": {
                "scriptLang": "JS",
                "jsScript": RISK_STATE_TO_ATTRS_JS,
                "tbelScript": (
                    'return {msg: {riskEngineState: msg.riskEngineState}, metadata: metadata, '
                    'msgType: "POST_ATTRIBUTES_REQUEST"};'
                ),
            },
            "additionalInfo": {"description": "Shifts msgType so Save Attributes persists riskEngineState", "layoutX": 500, "layoutY": 200},
        },
        {
            "id": nid(5),
            "ruleChainId": rc,
            "type": save_attrs_type,
            "name": "Save server state",
            "debugMode": False,
            "configuration": save_attrs_configuration,
            "additionalInfo": {"layoutX": 720, "layoutY": 200},
        },
        {
            "id": nid(6),
            "ruleChainId": rc,
            "type": "org.thingsboard.rule.engine.filter.TbJsFilterNode",
            "name": "Raise alarm?",
            "debugMode": False,
            "configuration": {
                "scriptLang": "JS",
                "jsScript": "return msg.raiseFarmerAlarm === true;",
                "tbelScript": "return msg.raiseFarmerAlarm === true;",
            },
            "additionalInfo": {"layoutX": 1140, "layoutY": 50},
        },
        {
            "id": nid(7),
            "ruleChainId": rc,
            "type": "org.thingsboard.rule.engine.action.TbCreateAlarmNode",
            "name": "Create farmer alarm",
            "debugMode": False,
            "configuration": {
                "alarmType": ALARM_TYPE,
                "severity": "MINOR",
                "propagate": True,
                "propagateToOwner": False,
                "propagateToTenant": False,
                "useMessageAlarmData": False,
                "overwriteAlarmDetails": True,
                "dynamicSeverity": False,
                "relationTypes": [],
                "scriptLang": "JS",
                "alarmDetailsBuildJs": ALARM_DETAILS_BUILD_JS,
                "alarmDetailsBuildTbel": "return {}",
            },
            "additionalInfo": {"layoutX": 1360, "layoutY": 50},
        },
    ]

    connections = [
        {"fromIndex": 0, "toIndex": 1, "type": "True"},
        {"fromIndex": 1, "toIndex": 2, "type": "Success"},
        {"fromIndex": 2, "toIndex": 3, "type": "Success"},
        {"fromIndex": 2, "toIndex": 4, "type": "Success"},
        {"fromIndex": 2, "toIndex": 6, "type": "Success"},
        {"fromIndex": 4, "toIndex": 5, "type": "Success"},
        {"fromIndex": 6, "toIndex": 7, "type": "True"},
    ]
    return {
        "ruleChainId": rc,
        "firstNodeIndex": 0,
        "nodes": nodes,
        "connections": connections,
        "ruleChainConnections": [],
    }


def disease_risk_script_digest() -> str:
    return "disease_risk_script.js (see repo)"


def write_rule_chain_ui_import_bundle(tb: str, headers: dict, chain_id: str, meta: dict) -> None:
    """ThingsBoard UI 'Import rule chain' often expects { ruleChain, metadata }."""
    gr = requests.get(f"{tb}/api/ruleChain/{chain_id}", headers=headers, timeout=30)
    if gr.status_code >= 400:
        return
    bundle = {"ruleChain": gr.json(), "metadata": meta}
    UI_IMPORT_BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    UI_IMPORT_BUNDLE.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print("UI import bundle:", UI_IMPORT_BUNDLE.relative_to(ROOT))


def patch_rule_chain_entry_point(tb: str, headers: dict, chain_id: str, first_node_id: dict) -> None:
    """Point the chain Input node at the first real rule node (TB sometimes omits this after metadata save)."""
    gr = requests.get(f"{tb}/api/ruleChain/{chain_id}", headers=headers, timeout=30)
    if gr.status_code >= 400:
        print("GET /api/ruleChain failed while patching entry point:", gr.status_code)
        return
    body = gr.json()
    want_id = (first_node_id or {}).get("id")
    cur_id = (body.get("firstRuleNodeId") or {}).get("id")
    if cur_id == want_id:
        return
    body["firstRuleNodeId"] = first_node_id
    pr = requests.post(f"{tb}/api/ruleChain", headers=headers, json=body, timeout=30)
    if pr.status_code >= 400:
        print("Could not set firstRuleNodeId on rule chain:", pr.status_code, pr.text[:400])
        return
    print("Rule chain entry point linked to first node:", want_id)


def find_rule_chain_id(tb: str, headers: dict, name: str) -> str | None:
    r = requests.get(
        f"{tb}/api/ruleChains",
        params={"pageSize": 100, "page": 0},
        headers=headers,
        timeout=30,
    )
    if r.status_code >= 400:
        return None
    for row in (r.json() or {}).get("data") or []:
        if (row.get("name") or "") == name:
            out = row.get("id") or {}
            if out.get("id"):
                return out["id"]
    return None


def ensure_rule_chain(tb: str, headers: dict) -> str | None:
    ver = get_thingsboard_version(tb, headers)
    forced = os.environ.get("TB_FORCE_LEGACY_RULE_NODES", "").strip().lower() in ("1", "true", "yes", "on")
    legacy = forced or use_legacy_rule_nodes(ver)
    if ver:
        print(f"ThingsBoard version: {ver[0]}.{ver[1]}.{ver[2]}")
    else:
        print(
            "ThingsBoard version: (not returned by GET /api/system/info). "
            "If your server is TB 3.2/3.3 and the chain stays empty in the UI, "
            "set TB_FORCE_LEGACY_RULE_NODES=1 and re-run."
        )
    if forced and not ver:
        print("TB_FORCE_LEGACY_RULE_NODES set (version API unavailable).")
    print(
        "Rule engine node profile:",
        "legacy TbSaveTimeseriesNode (TB < 3.4)" if legacy else "TbMsgTimeseriesNode (TB 3.4+ / 4.x)",
    )

    existing = find_rule_chain_id(tb, headers, RULE_CHAIN_NAME)
    node_ids = [str(uuid.uuid4()) for _ in range(8)]
    if existing:
        chain_id = existing
        print(f"Updating rule chain: {RULE_CHAIN_NAME} ({chain_id})")
        meta = build_rule_chain_metadata(chain_id, node_ids, legacy=legacy)
        meta["ruleChainId"] = {"entityType": "RULE_CHAIN", "id": chain_id}
    else:
        body = {
            "name": RULE_CHAIN_NAME,
            "type": "CORE",
            "firstRuleNodeId": None,
            "root": False,
            "debugMode": False,
            "configuration": None,
            "additionalInfo": {"description": "Assignment 2 disease risk (provision_tb_assignment.py)"},
        }
        pr = requests.post(f"{tb}/api/ruleChain", headers=headers, json=body, timeout=30)
        if pr.status_code >= 400:
            print("POST /api/ruleChain failed:", pr.status_code, pr.text[:500])
            return None
        chain_id = (pr.json() or {}).get("id", {}).get("id")
        if not chain_id:
            print("No id in rule chain response")
            return None
        print(f"Created rule chain: {RULE_CHAIN_NAME} ({chain_id})")
        meta = build_rule_chain_metadata(chain_id, node_ids, legacy=legacy)

    gm = requests.get(f"{tb}/api/ruleChain/{chain_id}/metadata", headers=headers, timeout=60)
    existing_node_count = len((gm.json() or {}).get("nodes") or []) if gm.status_code < 400 else 0

    grc = requests.get(f"{tb}/api/ruleChain/{chain_id}", headers=headers, timeout=30)
    if grc.status_code < 400:
        ver_e = (grc.json() or {}).get("version")
        if ver_e is not None:
            meta["version"] = ver_e

    to_post = meta_for_rule_chain_rest_save(meta, existing_node_count=existing_node_count)

    mr = requests.post(
        f"{tb}/api/ruleChain/metadata",
        headers=headers,
        json=to_post,
        params={"updateRelated": "true"},
        timeout=120,
    )
    if mr.status_code >= 400:
        print("POST /api/ruleChain/metadata failed:", mr.status_code, mr.text[:800])
        return None
    try:
        saved = (mr.json() or {}).get("nodes") or []
        if not saved:
            print(
                "WARNING: POST /api/ruleChain/metadata returned zero nodes in the response. "
                "If the editor still shows only Input, open Rule chains - Import and use:\n  "
                f"{UI_IMPORT_BUNDLE} (or {LAST_META_SNAPSHOT}). "
                "Pin image thingsboard/tb-postgres:4.2.1.1 if your image misbehaves (see docker-compose.yml).",
            )
    except Exception:
        pass

    after = requests.get(f"{tb}/api/ruleChain/{chain_id}/metadata", headers=headers, timeout=60)
    canon = (after.json() or {}) if after.status_code < 400 else (mr.json() or {})
    if (canon.get("nodes") or []) and canon["nodes"][0].get("id"):
        patch_rule_chain_entry_point(tb, headers, chain_id, canon["nodes"][0]["id"])
    LAST_META_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    LAST_META_SNAPSHOT.write_text(json.dumps(canon, indent=2), encoding="utf-8")
    print("Rule chain metadata saved.", "Snapshot:", LAST_META_SNAPSHOT.relative_to(ROOT))
    write_rule_chain_ui_import_bundle(tb, headers, chain_id, canon)
    return chain_id


def build_farmer_dashboard_configuration(*, tb_version: tuple[int, int, int] | None = None) -> dict:
    """Dashboard configuration per FARMER_DASHBOARD.md (per-zone risk + 48h charts)."""
    alias_z1 = str(uuid.uuid4())
    alias_z2 = str(uuid.uuid4())
    alias_all = str(uuid.uuid4())
    w_risk1 = str(uuid.uuid4())
    w_risk2 = str(uuid.uuid4())
    w_th = str(uuid.uuid4())
    w_rain = str(uuid.uuid4())
    w_alarm = str(uuid.uuid4())

    entity_aliases = {
        alias_z1: {
            "id": alias_z1,
            "alias": "zone1_devices",
            "filter": {
                "type": "deviceType",
                "resolveMultiple": True,
                "deviceNameFilter": "",
                "deviceTypes": [ZONE1_TYPE],
            },
        },
        alias_z2: {
            "id": alias_z2,
            "alias": "zone2_devices",
            "filter": {
                "type": "deviceType",
                "resolveMultiple": True,
                "deviceNameFilter": "",
                "deviceTypes": [ZONE2_TYPE],
            },
        },
        alias_all: {
            "id": alias_all,
            "alias": "all_field_devices",
            "filter": {
                "type": "deviceType",
                "resolveMultiple": True,
                "deviceNameFilter": "",
                "deviceTypes": [ZONE1_TYPE, ZONE2_TYPE],
            },
        },
    }

    tw_default = {
        "hideAggregation": False,
        "hideAggInterval": False,
        "hideTimezone": False,
        "selectedTab": 0,
        "realtime": {"realtimeType": 0, "interval": 1000, "timewindowMs": 172800000},
        "aggregation": {"type": "NONE", "limit": 25000},
    }

    def chart_tw(aggregation_type: str, agg_limit: int) -> dict:
        """Rolling last 48 h — avoids fixedTimewindow 0..1 ms which breaks charts."""
        return {
            "hideAggregation": False,
            "hideAggInterval": False,
            "hideTimezone": False,
            "selectedTab": 0,
            "realtime": {
                "realtimeType": 0,
                "timewindowMs": 172800000,
                "interval": 5000,
            },
            "aggregation": {"type": aggregation_type, "limit": agg_limit},
        }

    def tb42_time_series_chart_settings() -> dict:
        """TB 4.2+ chart widget expects settings.yAxes (otherwise: Cannot read 'keys' of undefined)."""
        return {
            "stack": False,
            "showLegend": True,
            "legendConfig": {
                "direction": "column",
                "position": "bottom",
                "sortDataKeys": False,
                "showMin": True,
                "showMax": True,
                "showAvg": True,
                "showTotal": False,
                "showLatest": False,
            },
            "thresholds": [],
            "dataZoom": True,
            "showTooltip": True,
            "tooltipTrigger": "axis",
            "padding": "12px",
            "xAxis": {
                "show": True,
                "position": "bottom",
                "showTickLabels": True,
                "showLine": True,
                "ticksFormat": {},
            },
            "yAxes": {
                "default": {
                    "id": "default",
                    "order": 0,
                    "show": True,
                    "position": "left",
                    "showTickLabels": True,
                    "showTicks": True,
                    "showLine": True,
                    "showSplitLines": True,
                    "splitLinesColor": "rgba(0, 0, 0, 0.12)",
                    "ticksColor": "rgba(0, 0, 0, 0.54)",
                    "lineColor": "rgba(0, 0, 0, 0.54)",
                    "tickLabelColor": "rgba(0, 0, 0, 0.54)",
                    "labelColor": "rgba(0, 0, 0, 0.54)",
                }
            },
            "noAggregationBarWidthSettings": {
                "strategy": "group",
                "groupWidth": {
                    "relative": True,
                    "relativeWidth": 2,
                    "absoluteWidth": 1000,
                },
                "barWidth": {
                    "relative": True,
                    "relativeWidth": 2,
                    "absoluteWidth": 1000,
                },
            },
            "animation": {
                "animation": True,
                "animationThreshold": 2000,
                "animationDuration": 500,
                "animationEasing": "cubicOut",
                "animationDelay": 0,
                "animationDurationUpdate": 300,
                "animationEasingUpdate": "cubicOut",
                "animationDelayUpdate": 0,
            },
            "background": {
                "type": "color",
                "color": "#fff",
                "overlay": {"enabled": False, "color": "rgba(255,255,255,0.72)", "blur": 3},
            },
        }

    def chart_widget_settings() -> dict:
        if use_tb42_chart_schema(tb_version):
            return tb42_time_series_chart_settings()
        return {"stack": False, "showLegend": True, "dataZoom": True}

    def entities_risk_widget(wid: str, alias_id: str, title: str) -> dict:
        return {
            "type": "latest",
            "sizeX": 12,
            "sizeY": 5,
            "config": {
                "timewindow": {
                    "displayValue": "",
                    "selectedTab": 0,
                    "realtime": {
                        "realtimeType": 1,
                        "interval": 1000,
                        "timewindowMs": 86400000,
                        "quickInterval": "CURRENT_DAY",
                        "hideInterval": False,
                        "hideLastInterval": False,
                        "hideQuickInterval": False,
                    },
                    "history": {
                        "historyType": 0,
                        "interval": 1000,
                        "timewindowMs": 60000,
                        "quickInterval": "CURRENT_DAY",
                        "hideInterval": False,
                        "hideLastInterval": False,
                        "hideFixedInterval": False,
                        "hideQuickInterval": False,
                    },
                    "aggregation": {"type": "NONE", "limit": 200},
                },
                "showTitle": True,
                "backgroundColor": "rgb(255, 255, 255)",
                "color": "rgba(0, 0, 0, 0.87)",
                "padding": "4px",
                "settings": {
                    "enableSearch": True,
                    "displayPagination": True,
                    "defaultPageSize": 10,
                    "defaultSortOrder": "entityName",
                    "displayEntityName": True,
                    "displayEntityType": False,
                    "enableSelectColumnDisplay": False,
                    "entitiesTitle": title,
                    "displayEntityLabel": False,
                    "entityNameColumnTitle": "Device",
                },
                "title": title,
                "dropShadow": True,
                "enableFullscreen": False,
                "datasources": [
                    {
                        "type": "entity",
                        "name": None,
                        "entityAliasId": alias_id,
                        "dataKeys": [
                            {
                                "name": "risk_level",
                                "type": "timeseries",
                                "label": "risk_level",
                                "color": "#f44336",
                                "settings": {"columnWidth": "0px"},
                                "_hash": 0.22,
                            },
                        ],
                    }
                ],
                "useDashboardTimewindow": False,
                "showLegend": False,
                "showTitleIcon": False,
                "titleStyle": {
                    "fontSize": "16px",
                    "fontWeight": 400,
                    "padding": "5px 10px 5px 10px",
                },
                "actions": {},
            },
            "id": wid,
            "typeFullFqn": "system.cards.entities_table",
        }

    dk_line = {
        "yAxisId": "default",
        "showInLegend": True,
        "dataHiddenByDefault": False,
        "type": "line",
        "lineSettings": {
            "showLine": True,
            "smooth": False,
            "lineWidth": 2,
            "showPoints": False,
        },
    }

    w_chart_th = {
        "type": "timeseries",
        "sizeX": 24,
        "sizeY": 6,
        "config": {
            "datasources": [
                {
                    "type": "entity",
                    "name": "",
                    "entityAliasId": alias_all,
                    "dataKeys": [
                        {
                            "name": "temperature",
                            "type": "timeseries",
                            "label": "Temperature",
                            "color": "#E53935",
                            "settings": {**dk_line},
                            "_hash": 0.31,
                            "units": "\u00b0C",
                            "decimals": 1,
                            "aggregationType": None,
                            "funcBody": None,
                            "usePostProcessing": None,
                            "postFuncBody": None,
                        },
                        {
                            "name": "humidity",
                            "type": "timeseries",
                            "label": "Humidity",
                            "color": "#1E88E5",
                            "settings": {**dk_line},
                            "_hash": 0.32,
                            "units": "%",
                            "decimals": 0,
                            "aggregationType": None,
                            "funcBody": None,
                            "usePostProcessing": None,
                            "postFuncBody": None,
                        },
                    ],
                }
            ],
            "timewindow": chart_tw("AVG", 25000),
            "showTitle": True,
            "title": "Temperature & humidity",
            "settings": chart_widget_settings(),
            "useDashboardTimewindow": False,
            "showLegend": True,
            "displayTimewindow": True,
        },
        "id": w_th,
        "typeFullFqn": "system.time_series_chart",
    }

    w_chart_rain = {
        "type": "timeseries",
        "sizeX": 24,
        "sizeY": 5,
        "config": {
            "datasources": [
                {
                    "type": "entity",
                    "name": "",
                    "entityAliasId": alias_all,
                    "dataKeys": [
                        {
                            "name": "rainfall",
                            "type": "timeseries",
                            "label": "rainfall",
                            "color": "#43A047",
                            "settings": {
                                "yAxisId": "default",
                                "showInLegend": True,
                                "dataHiddenByDefault": False,
                                "type": "bar",
                                "lineSettings": {
                                    "showLine": False,
                                    "smooth": False,
                                    "lineWidth": 2,
                                    "showPoints": False,
                                },
                                "barSettings": {
                                    "showBorder": False,
                                    "borderWidth": 2,
                                },
                            },
                            "_hash": 0.41,
                            "aggregationType": None,
                            "funcBody": None,
                            "usePostProcessing": None,
                            "postFuncBody": None,
                        },
                    ],
                }
            ],
            "timewindow": chart_tw("MAX", 5000),
            "showTitle": True,
            "title": "Rainfall bursts",
            "settings": chart_widget_settings(),
            "useDashboardTimewindow": False,
            "showLegend": True,
            "displayTimewindow": True,
        },
        "id": w_rain,
        "typeFullFqn": "system.time_series_chart",
    }

    w_alarms = {
        "type": "alarm",
        "sizeX": 24,
        "sizeY": 6,
        "config": {
            "timewindow": {"realtime": {"interval": 1000, "timewindowMs": 86400000}},
            "showTitle": True,
            "title": "Alert history",
            "settings": {
                "enableSearch": True,
                "displayPagination": True,
                "defaultPageSize": 10,
                "enableFilter": True,
            },
            "alarmSource": {
                "type": "entity",
                "name": "alarms",
                "entityAliasId": alias_all,
                "dataKeys": [
                    {"name": "createdTime", "type": "alarm", "label": "Created", "color": "#2196f3", "settings": {}, "_hash": 0.51},
                    {"name": "type", "type": "alarm", "label": "Type", "color": "#f44336", "settings": {}, "_hash": 0.52},
                    {"name": "severity", "type": "alarm", "label": "Severity", "color": "#ffc107", "settings": {}, "_hash": 0.53},
                ],
            },
            "alarmFilterConfig": {
                "statusList": [],
                "severityList": [],
                "typeList": [ALARM_TYPE],
                "searchPropagatedAlarms": True,
            },
            "datasources": [],
            "useDashboardTimewindow": False,
            "showLegend": False,
            "displayTimewindow": True,
        },
        "id": w_alarm,
        "typeFullFqn": "system.alarm_widgets.alarms_table",
    }

    layouts = {
        "main": {
            "widgets": {
                w_risk1: {"col": 0, "row": 0, "sizeX": 12, "sizeY": 5, "resizable": True},
                w_risk2: {"col": 12, "row": 0, "sizeX": 12, "sizeY": 5, "resizable": True},
                w_th: {"col": 0, "row": 5, "sizeX": 24, "sizeY": 6, "resizable": True},
                w_rain: {"col": 0, "row": 11, "sizeX": 24, "sizeY": 5, "resizable": True},
                w_alarm: {"col": 0, "row": 16, "sizeX": 24, "sizeY": 6, "resizable": True},
            },
            "gridSettings": {
                "layoutType": "default",
                "columns": 24,
                "margin": 10,
                "outerMargin": True,
                "backgroundColor": "#eeeeee",
                "color": "rgba(0,0,0,0.87)",
                "backgroundSizeMode": "100%",
                "autoFillHeight": True,
                "mobileAutoFillHeight": False,
                "mobileRowHeight": 70,
            },
        }
    }

    # TB 3.4+ / 4.x renders the visible grid from states.default.layouts, not layouts alone.
    states = {
        "default": {
            "name": DASHBOARD_TITLE,
            "root": True,
            "layouts": layouts,
        }
    }

    return {
        "description": "",
        "widgets": {
            w_risk1: entities_risk_widget(w_risk1, alias_z1, "Risk — Zone 1"),
            w_risk2: entities_risk_widget(w_risk2, alias_z2, "Risk — Zone 2"),
            w_th: w_chart_th,
            w_rain: w_chart_rain,
            w_alarm: w_alarms,
        },
        "layouts": layouts,
        "states": states,
        "entityAliases": entity_aliases,
        "filters": {},
        "settings": {
            "stateControllerId": "default",
            "showTitle": False,
            "showEntitiesSelect": True,
            "showDashboardTimewindow": True,
            "showDashboardExport": True,
            "toolbarAlwaysOpen": True,
        },
        "timewindow": tw_default,
    }


def find_dashboard(tb: str, headers: dict, title: str) -> dict | None:
    r = requests.get(
        f"{tb}/api/tenant/dashboards",
        params={"pageSize": 100, "page": 0},
        headers=headers,
        timeout=30,
    )
    if r.status_code >= 400:
        return None
    for row in (r.json() or {}).get("data") or []:
        if (row.get("title") or row.get("name") or "") == title:
            return row
    return None


def ensure_farmer_dashboard(tb: str, headers: dict) -> bool:
    ver = get_thingsboard_version(tb, headers)
    conf = build_farmer_dashboard_configuration(tb_version=ver)
    existing = find_dashboard(tb, headers, DASHBOARD_TITLE)
    if existing:
        did = existing.get("id", {}).get("id")
        if not did:
            print("Dashboard row missing id")
            return False
        gr = requests.get(f"{tb}/api/dashboard/{did}", headers=headers, timeout=30)
        if gr.status_code >= 400:
            print("GET dashboard failed", gr.status_code)
            return False
        body = gr.json()
        body["configuration"] = conf
        body["title"] = DASHBOARD_TITLE
        body["name"] = DASHBOARD_TITLE
        pr = requests.post(f"{tb}/api/dashboard", headers=headers, json=body, timeout=60)
    else:
        body = {
            "title": DASHBOARD_TITLE,
            "name": DASHBOARD_TITLE,
            "configuration": conf,
        }
        pr = requests.post(f"{tb}/api/dashboard", headers=headers, json=body, timeout=60)
    if pr.status_code >= 400:
        print("Save dashboard failed:", pr.status_code, pr.text[:800])
        return False
    print(f"Dashboard saved: {DASHBOARD_TITLE}")
    return True


def assign_chain_to_zone_profiles(tb: str, headers: dict, chain_id: str) -> None:
    """Set default rule chain on Zone1_Sensor and Zone2_Sensor device profiles."""
    r = requests.get(
        f"{tb}/api/deviceProfileInfos",
        params={"pageSize": 100, "page": 0},
        headers=headers,
        timeout=30,
    )
    if r.status_code >= 400:
        print("deviceProfileInfos failed:", r.status_code, r.text[:300])
        return
    profiles: dict[str, str] = {}
    for row in (r.json() or {}).get("data") or []:
        name = row.get("name")
        pid = (row.get("id") or {}).get("id")
        if name and pid:
            profiles[name] = pid
    for zone_name in (ZONE1_TYPE, ZONE2_TYPE):
        pid = profiles.get(zone_name)
        if not pid:
            print(f"Warning: device profile {zone_name!r} not found — create it first (THINGSBOARD_FULL_SETUP.md).")
            continue
        gr = requests.get(f"{tb}/api/deviceProfile/{pid}", headers=headers, timeout=30)
        if gr.status_code >= 400:
            print(f"GET deviceProfile {zone_name} failed", gr.status_code)
            continue
        prof = gr.json()
        prof["defaultRuleChainId"] = {"entityType": "RULE_CHAIN", "id": chain_id}
        wr = requests.post(f"{tb}/api/deviceProfile", headers=headers, json=prof, timeout=30)
        if wr.status_code >= 400:
            print(f"Save deviceProfile {zone_name} failed:", wr.status_code, wr.text[:400])
        else:
            print(f"Attached rule chain to device profile {zone_name}.")


def main() -> int:
    load_dotenv(ENV_PATH)
    p = argparse.ArgumentParser(description="Provision TB rule chain + farmer dashboard.")
    p.add_argument("--rule-chain-only", action="store_true")
    p.add_argument("--dashboard-only", action="store_true")
    p.add_argument("--no-assign-profiles", action="store_true")
    args = p.parse_args()

    tb = os.environ.get("TB_URL", "http://localhost:9090").rstrip("/")
    user = os.environ.get("TB_USERNAME", "tenant@thingsboard.org")
    password = os.environ.get("TB_PASSWORD", "tenant")

    headers = tb_login(tb, user, password)
    if not headers:
        return 1

    chain_id: str | None = None
    if not args.dashboard_only:
        chain_id = ensure_rule_chain(tb, headers)
        if not chain_id:
            return 1
        if not args.no_assign_profiles:
            assign_chain_to_zone_profiles(tb, headers, chain_id)

    if not args.rule_chain_only:
        if not ensure_farmer_dashboard(tb, headers):
            return 1

    print("Done. Export artifacts: py -3 scripts/export_tb_artifacts.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
