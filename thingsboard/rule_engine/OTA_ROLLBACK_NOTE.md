## OTA rollback automation note

ThingsBoard CE has limited built-in aggregation across unrelated devices purely inside scripting nodes. Implementation uses:

1. **Per-device** `fw_state` / `fw_version` telemetry emitted by [`thingsboard_tb_sidecar.py`](../../chirpstack/chirpstack-docker/thingsboard_tb_sidecar.py).
2. **[`thingsboard/scripts/rollback_watchdog.py`](../scripts/rollback_watchdog.py)** polling REST telemetry for Zone2 devices; exit code **3** fires when ≥2 devices report FAILED (instructions print for UI rollback).

Optional: add a Rule Chain **REST API call** step hitting `http://host.docker.internal:PORT/rollback` that wraps the same REST calls.
