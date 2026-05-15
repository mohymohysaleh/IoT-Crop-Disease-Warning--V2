# OTA package content (assignment §3.3)

1. Zip this folder (or only `thresholds_v2.json`) as `zone2_thresholds_v2.zip`.
2. In ThingsBoard **OTA updates** create a **Firmware** resource, version `1.1.0`, title `thresholds_v2`.
3. Assign the package to **Device profile** `Zone2_Sensor` only.
4. Start the Python sidecars with real access tokens (see `chirpstack/chirpstack-docker/config/devices.json`). They automatically walk `fw_state` telemetry when shared attributes `fw_*` arrive.

To **force a FAILED** path for rollback testing set environment variable `TB_OTA_SIMULATE_FAIL=1` before launching `thingsboard_tb_sidecar.py`.
