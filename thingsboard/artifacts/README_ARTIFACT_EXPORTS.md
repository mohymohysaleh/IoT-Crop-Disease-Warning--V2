# Exported ThingsBoard artifacts (for submission ZIP)

ThingsBoard CE stores most configuration in the UI. After you complete setup, export the following and save them under `thingsboard/artifacts/exports/`:

| Artifact | UI path |
|-----------|---------|
| **Disease Risk** rule chain JSON | Rule chains → Disease Risk Engine → ⋮ → Export |
| **OTA / Rollback** auxiliary chain (optional) | Same |
| **Farmer dashboard** JSON | Dashboards → Farmer → ⋮ → Export |
| **Zone1_Sensor** device profile | Device profiles → ⋮ → Export |
| **Zone2_Sensor** device profile | Same |
| **MQTT integration** | Integrations → Export (if available on your build) |
| **Data converter** | Already versioned in repo: `integrations/chirpstack_uplink_converter.js` |

If your ThingsBoard build does not expose export for integrations, include screenshots + the committed JS file.

Use meaningful filenames, e.g. `rule_chain_disease_risk.json`, `dashboard_farmer.json`, `device_profile_zone2_sensor.json`.
