# Demo video shot list (5–10 minutes)

Use OBS / Teams / Snipping Tool. Speak clearly; show timestamps in logs when possible.

1. **Intro (30 s)** — Show GitHub repo + README; state team + platform (ThingsBoard).
2. **Stack boot (45 s)** — `docker compose up` inside `chirpstack/chirpstack-docker`; browse `http://localhost:8080` (ChirpStack) & `http://localhost:9090` (ThingsBoard login).
3. **ChirpStack proof (90 s)** — Applications/devices list, MQTT live frames, annotate two gateways EUIs (`aa…01`, `aa…02`).
4. **Simulator (60 s)** — Start `python run_all_nodes.py`, tail one log file showing 5 min cadence commentary.
5. **ThingsBoard ingestion (120 s)** — Latest telemetry widgets + device profiles + integration status; narrate decoded fields.
6. **Risk escalation (120 s)** — Trigger HIGH/CRITICAL scenario (explain which nodes/modes accelerate humidity); display alarms/email if configured.
7. **OTA (150 s)** — Assign firmware (`thresholds_v2`) only to Zone2 profile; capture shared attributes + `fw_state` timeline via sidecars; optionally flip `TB_OTA_SIMULATE_FAIL=1`.
8. **Rollback (90 s)** — Run `python thingsboard/scripts/rollback_watchdog.py` with exported profile UUID; narrate remediation + UI steps.
9. **Security bonus (90 s, optional)** — Run `thingsboard/scripts/rogue_mqtt_client.py`; show CONNACK + TB logs/screens.
10. **Outro (30 s)** — Enumerate artifacts (exported JSON/ZIP/report).

Deliver final `.mp4` per classroom instructions.
