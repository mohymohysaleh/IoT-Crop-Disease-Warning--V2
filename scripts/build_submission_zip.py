#!/usr/bin/env python3
"""Collect Assignment 2 deliverable sources into ASSIGNMENT2_SUBMISSION.zip at repo root."""
from __future__ import annotations

import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "ASSIGNMENT2_SUBMISSION.zip"

INCLUDE = [
    "README.md",
    "docs/ASSIGNMENT2_REPORT.md",
    "docs/DEMO_VIDEO_SCRIPT.md",
    "docs/VERIFICATION_AND_TESTING.md",
    "docs/THINGSBOARD_FULL_SETUP.md",
    "chirpstack/chirpstack-docker/docker-compose.yml",
    "chirpstack/chirpstack-docker/chirpstack_tb_bridge.py",
    "chirpstack/chirpstack-docker/Dockerfile.tb-bridge",
    "chirpstack/chirpstack-docker/.env.example",
    "chirpstack/chirpstack-docker/node_simulator.py",
    "chirpstack/chirpstack-docker/run_all_nodes.py",
    "chirpstack/chirpstack-docker/gateway_activator.py",
    "chirpstack/chirpstack-docker/thingsboard_tb_sidecar.py",
    "chirpstack/chirpstack-docker/config/devices.json",
    "chirpstack/chirpstack-docker/simulate_uplink.py",
    "chirpstack/chirpstack-docker/scripts/Reset-ChirpStackPostgres.ps1",
    "chirpstack/chirpstack-docker/scripts/Repair-ChirpStackTenantLinks.ps1",
    "chirpstack/chirpstack-docker/scripts/repair_chirpstack_visibility.sql",
    "chirpstack/chirpstack-docker/requirements-assignment.txt",
    "thingsboard/integrations/chirpstack_uplink_converter.js",
    "thingsboard/integrations/INTEGRATION_SETUP.md",
    "thingsboard/chirpstack/payload_codec.js",
    "thingsboard/rule_engine/disease_risk_script.js",
    "thingsboard/rule_engine/RULE_CHAIN.md",
    "thingsboard/rule_engine/OTA_ROLLBACK_NOTE.md",
    "thingsboard/dashboards/FARMER_DASHBOARD.md",
    "thingsboard/device_profiles/README.md",
    "thingsboard/ota/sample_firmware_payload/thresholds_v2.json",
    "thingsboard/ota/sample_firmware_payload/README.md",
    "thingsboard/scripts/rollback_watchdog.py",
    "thingsboard/scripts/rogue_mqtt_client.py",
    "thingsboard/security/SECURITY_BONUS.md",
    "thingsboard/artifacts/README_ARTIFACT_EXPORTS.md",
    "thingsboard/artifacts/exports/",
    "scripts/build_submission_zip.py",
    "scripts/verify_assignment_ready.py",
    "scripts/export_tb_artifacts.py",
    "scripts/build_report_pdf.py",
]


def main() -> None:
    OUTPUT.unlink(missing_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in INCLUDE:
            path = ROOT / rel
            if path.is_dir():
                for fp in sorted(path.rglob("*")):
                    if fp.is_file():
                        arc = fp.relative_to(ROOT)
                        z.write(fp, arcname=str(arc.as_posix()))
            elif path.is_file():
                z.write(path, arcname=str(Path(rel).as_posix()))
            else:
                print("skip missing", rel)
    print("Wrote", OUTPUT)


if __name__ == "__main__":
    main()
