# Exported ThingsBoard artifacts (for submission ZIP)

ThingsBoard CE stores most configuration in the UI. After you complete setup, export the following and save them under `thingsboard/artifacts/exports/`:

| Artifact | UI path |
|-----------|---------|
| **Disease Risk** rule chain (entity JSON + UI export) | Rule chains → Disease Risk Engine → ⋮ → Export |
| **Disease Risk** nodes and connections (full graph) | Use `rule_chain_disease_risk_engine.provisioned_metadata.json` after `py -3 scripts/provision_tb_assignment.py` (CE often returns empty nodes from GET `/api/ruleChain/.../metadata`). || **OTA / Rollback** auxiliary chain (optional) | Same |
| **Farmer dashboard** JSON | Dashboards → Farmer → ⋮ → Export |
| **Zone1_Sensor** device profile | Device profiles → ⋮ → Export |
| **Zone2_Sensor** device profile | Same |
| **MQTT integration** | Integrations → Export (if available on your build) |
| **Data converter** | Already versioned in repo: `integrations/chirpstack_uplink_converter.js` |

If your ThingsBoard build does not expose export for integrations, include screenshots + the committed JS file.

Use meaningful filenames, e.g. `rule_chain_disease_risk.json`, `dashboard_farmer.json`, `device_profile_zone2_sensor.json`.
