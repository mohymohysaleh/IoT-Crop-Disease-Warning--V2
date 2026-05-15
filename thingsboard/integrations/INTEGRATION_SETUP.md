# ThingsBoard MQTT integration (ChirpStack uplink)

**ThingsBoard Community Edition:** there is no **Integrations** UI. Use the Docker service **`tb-chirpstack-bridge`** (or run `chirpstack/chirpstack-docker/chirpstack_tb_bridge.py` on the host). It subscribes to `application/+/device/+/event/up` and posts HTTP telemetry like this document describes for PE.

**ThingsBoard PE:** configure after ChirpStack publishes uplinks on `application/+/device/+/event/up`.

## Broker (this repository’s Docker Compose)

| Field | Value |
|-------|-------|
| Host | `mosquitto` inside the compose network; use `localhost` only if ThingsBoard runs on the host while Mosquitto is bound to localhost:1883 |
| Port | `1883` |
| Topic filter | `application/+/device/+/event/up` |

## Data converter

Paste [chirpstack_uplink_converter.js](chirpstack_uplink_converter.js) into the integration’s uplink converter.

Device types produced: `Zone1_Sensor` and `Zone2_Sensor`.

## ChirpStack codec

Install [../chirpstack/payload_codec.js](../chirpstack/payload_codec.js) in the relevant ChirpStack device profile so `object.*` telemetry is decoded from the simulator’s binary payload.
