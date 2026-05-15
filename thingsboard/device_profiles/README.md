# Device profiles

Create two profiles in **Device profiles** matching the data-converter output:

| Profile name | MQTT default | Notes |
|---------------|--------------|-------|
| `Zone1_Sensor` | Access token default | Used for nodes 1–5 (devEUI map in converter) |
| `Zone2_Sensor` | Access token default | Used for nodes 6–10; assign OTA firmware here only |

Provisioning steps:

1. Create both profiles (transport **DEFAULT** is fine for MQTT devices emulated by the REST/MQTT integration path).
2. For each physical/logical device ThingsBoard creates from the integration (or pre-provisioned), assign the correct profile and paste the access token into [`chirpstack/chirpstack-docker/config/devices.json`](../chirpstack/chirpstack-docker/config/devices.json) (`thingsboard_access_token` for zone2 nodes enables the OTA sidecars).
3. Export each profile JSON (`device_profile_zone1_sensor.json`, `device_profile_zone2_sensor.json`) into `thingsboard/artifacts/exports/`.

Default queue settings are sufficient for this lab; enable **OTA** checkbox on Zone2 profile when using ThingsBoard FW updates UI.
