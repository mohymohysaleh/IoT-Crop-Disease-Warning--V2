# Security bonus checklist (ThingsBoard edition)

Completing every item earns the instructor rubric bonus (+1 course grade).

1. **X.509 device credentials** — Generate distinct client certificates using `thingsboard-gateway` tooling or openssl per [ThingsBoard X.509 guide](https://thingsboard.io/docs/user-guide/certificates/). Import public keys via device credentials UI. Tokens in `devices.json` remain placeholders for non-bonus demos.
2. **MQTTS TLS 1.2+** — Terminate TLS on an external mosquitto/nginx proxy mapped to `:8883`, or rely on ThingsBoard native TLS when running the monolith outside Docker Compose. Capture the handshake using Wireshark (loopback adapter on Windows).
3. **Customers & least privilege** — Create `Customer_Zone1` / `Customer_Zone2`; assign respective devices only. Demonstrate crossing customer boundaries fails to publish telemetry.
4. **Audit logging** — Enable audit logs (`thingsboard.yml` / UI) and screenshot login + credential failures.
5. **Device-profile alarm rules** (≥3 suggestions from brief) — e.g. inactive >30 min, telemetry frequency spike, plausible range violation on humidity/temperature.
6. **Attack demo** — Run [`rogue_mqtt_client.py`](../scripts/rogue_mqtt_client.py); capture MQTT CONNACK + TB logs showing rejection.

> Never submit production certificates, JWTs from live tenants, or actual SMTP passwords — use lab-only placeholders.
