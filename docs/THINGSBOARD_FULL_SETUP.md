# ThingsBoard — full setup steps (after ChirpStack is working)

Use this checklist **after** uplinks reach ChirpStack and **`application/#`** MQTT topics show events on the same broker as Compose (see `VERIFICATION_AND_TESTING.md`, §§3–5).

**ThingsBoard CE:** ingestion uses the **`tb-chirpstack-bridge`** service (Python script `chirpstack/chirpstack-docker/chirpstack_tb_bridge.py`) instead of the PE-only **Integrations** UI. **ThingsBoard PE:** use **MQTT integration** + **uplink converter** as below.

---

## 0. What you already need from ChirpStack

1. Docker Compose stack up: **`chirpstack`**, **`mosquitto`**, **`thingsboard`**, Postgres, Redis, gateways.
2. ChirpStack **accepts** uplinks (**device last seen**, no repeated “No device-session” errors).
3. ChirpStack **MQTT integration for the Zone 1 / Zone 2 applications** publishes to **`application/<APP_ID>/device/<DEV_EUI>/event/up`** on **`mosquitto:1883`** (inside Compose). Confirm from Mosquitto, e.g.:

   ```powershell
   cd chirpstack\chirpstack-docker
   docker compose exec mosquitto mosquitto_sub -h 127.0.0.1 -p 1883 -t "application/#" -v -C 3
   ```

   Run a simulator or **`py -3 scripts\_selftest_one_uplink.py`** while this subscribes; you should see at least one `event/up` line.

4. **Device profile payload codec** in ChirpStack: install the repo codec so **`object.temperature`** (and siblings) appear in MQTT JSON (`thingsboard/chirpstack/payload_codec.js` in UI “Payload codec”). If **`object`** is missing, the ThingsBoard converter still has a **`data`** Base64 fallback, but aligning the codec avoids surprises.

---

## 1. URLs, login, tier

| Item | Value |
|------|--------|
| ThingsBoard UI | **http://localhost:9090** |
| Default admin | **`sysadmin@thingsboard.org`** / **`sysadmin`** (change password immediately) |

**Important:** Devices, integrations, rule chains, and dashboards live in **tenant** scope. After login as platform admin:

- Open your **tenant** (“Tenant Administrator” dashboard), or  
- From system menu: **Tenants** → choose the default tenant → **Manage tenant** / open tenant UI.

All steps below assume you are logged in as **Tenant Administrator** (not only system-admin home).

---

## 2. Device profiles

Create **two** device profiles. Names must **match** what the uplink converter outputs (`deviceType`: **`Zone1_Sensor`** / **`Zone2_Sensor`**) so the MQTT integration can map type → profile.

| Profile name | Purpose |
|--------------|---------|
| **Zone1_Sensor** | Nodes `0000000000000001` … `0000000000000005` (Zone 1 app in ChirpStack) |
| **Zone2_Sensor** | Nodes `0000000000000006` … `0000000000000010`; use for **ThingsBoard OTA** only in this lab |

**Where in the UI:** log in as **Tenant Administrator** → left menu **Profiles** → **Device profiles** → **+** (or **Add device profile**).

*(Button labels differ slightly by ThingsBoard CE version; the path is always under **Device profiles**.)*

### 2a. Create **Zone1_Sensor**

1. Click **+** / **Add device profile**.
2. **Name:** type exactly **`Zone1_Sensor`** (case-sensitive for clean exports and dashboards).
3. **Rule chain** (optional): leave **Root Rule Chain** or your tenant default unless you already assigned a dedicated chain per profile.
4. **Queue name** (if shown): default is fine.
5. **Transport configuration**
   - Open the **Transport configuration** step or tab.
   - Select transport type **MQTT** (sometimes listed as **MQTT** / **Default** with MQTT device communication — not **HTTP** or **CoAP**).
   - Leave **MQTT device type** as the normal **Device** (not Gateway), unless your build only offers a single MQTT template.
6. **MQTT details** (if the wizard shows sub‑steps)
   - **Telemetry topic**, **Attributes topic**, **RPC** requests: keep **defaults** (this lab’s uplink path is **ChirpStack → Mosquitto → TB Integration**; you are not relying on each sensor opening its own MQTT client to ThingsBoard for telemetry, except Zone 2 **sidecars** which use **access token** + TB’s device MQTT on port **11883**).
   - **Payload**: **JSON** is standard; no binary Sparkplug unless you know you enabled it.
7. **Alarm rules** / **Provision** / **Firmware**: skip or defaults for now.
8. **Save** (or **Add** / **Apply**). You should see **Zone1_Sensor** in the device profile list.

### 2b. Create **Zone2_Sensor**

Repeat **§2a** with name **`Zone2_Sensor`** only. All other defaults can match **Zone1_Sensor** unless you need different queue or rule chain.

### 2c. Enable **OTA / firmware** on **Zone2_Sensor** only

Required only if you will use ThingsBoard **Firmware / OTA packages** UI and **`thingsboard_tb_sidecar.py`** with real access tokens (`thingsboard/device_profiles/README.md`).

1. **Profiles** → **Device profiles** → open **Zone2_Sensor**.
2. Find the section named like **Firmware / OTA**, **OTA firmware updates**, or **Device profile firmware** (often a tab or checkbox in the transport / advanced area).
3. Enable **OTA** / **Firmware update** support for this profile (exact wording varies).
4. **Save**.

Do **not** enable the same OTA flag on **Zone1_Sensor** if you follow the repo’s “Zone 2 only OTA” design.

### 2d. After devices are created (Zone 2 tokens)

The CE **bridge** (or PE MQTT integration) **auto-creates** devices on first telemetry. For **nodes 6–10**:

1. **Devices** → open each Zone 2 device → **Manage credentials**.
2. Copy **MQTT** **Access token**.
3. Paste into **`chirpstack/chirpstack-docker/config/devices.json`** → **`thingsboard_access_token`** for that node (`thingsboard/device_profiles/README.md`).

### 2e. Export for your ZIP *(optional)*

1. **Device profiles** → row **Zone1_Sensor** → **⋮** (kebab) → **Export profile** / **Export**.
2. Save as e.g. **`device_profile_zone1_sensor.json`** under **`thingsboard/artifacts/exports/`**.
3. Repeat for **Zone2_Sensor** → **`device_profile_zone2_sensor.json`**.

See **`thingsboard/artifacts/README_ARTIFACT_EXPORTS.md`**.

---

## 3. Uplink data converter (PE only)

For **Professional Edition** MQTT integrations, create a converter from **`thingsboard/integrations/chirpstack_uplink_converter.js`**. **CE** users relying on **`tb-chirpstack-bridge`** can skip this — the bridge implements the same decoding rules.

1. **Data converters → Uplink → Add data converter**.
2. Name e.g. **`ChirpStack application JSON`**.
3. Type: **Uplink**, decode: **From integration payload**.
4. Replace the script body with the contents of  
   **`thingsboard/integrations/chirpstack_uplink_converter.js`** (repo file).
5. **Debug** with a real JSON sample from ChirpStack `application/.../event/up` if the UI offers “Test converter”; expect telemetry keys **temperature**, **humidity**, **leaf_wetness**, **rainfall** and device types **Zone1_Sensor** / **Zone2_Sensor**.

---

## 4. Bridge from Mosquitto → ThingsBoard

### 4a. Community Edition — `tb-chirpstack-bridge` (this repo)

There is **no** **Integrations** menu in CE. After **§2** (profiles **Zone1_Sensor** / **Zone2_Sensor** exist) and **ChirpStack `event/up`** traffic is flowing:

1. Put tenant credentials in **`chirpstack/chirpstack-docker/.env`**: **`TB_USERNAME`**, **`TB_PASSWORD`**, and optionally **`TB_ZONE1_PROFILE_ID`** / **`TB_ZONE2_PROFILE_ID`** (if omitted, the bridge looks up profiles by those exact names).
2. From **`chirpstack/chirpstack-docker`**, build and start the bridge:

   ```powershell
   docker compose up -d --build tb-chirpstack-bridge
   ```

   The container sets **`MQTT_HOST=mosquitto`**, **`MQTT_PORT=1883`**, **`TB_URL=http://thingsboard:9090`** automatically; **`.env`** supplies the password and optional profile UUIDs.

3. **Host-only** (no Docker bridge): `py -3 chirpstack_tb_bridge.py` with **`.env`** using **`MQTT_HOST=localhost`**, **`MQTT_PORT=1884`**, **`TB_URL=http://localhost:9090`**.

4. Check logs: `docker compose logs -f tb-chirpstack-bridge`. In ThingsBoard **Devices**, new entities appear named by **devEUI** (lowercase hex) on first accepted **`event/up`**.

The bridge mirrors the logic in **`thingsboard/integrations/chirpstack_uplink_converter.js`** (telemetry + **zone** client attribute).

### 4b. Professional Edition — MQTT Integration (optional)

1. **Integrations → Integrations → +** → **MQTT** (name e.g. **`ChirpStack application uplink`**).
2. **Enabled** = on.
3. **Broker** (Compose network — ThingsBoard container talks to Mosquitto by service name):

   | Field | Value |
   |--------|--------|
   | Host | **`mosquitto`** |
   | Port | **`1883`** |

   If you ever run ThingsBoard **outside** Docker while Mosquitto is on the host, use host networking that reaches the same broker (not covered by default compose).

4. **Topic filter:** **`application/+/device/+/event/up`**
5. **QoS** 1 is fine.
6. Assign the **uplink data converter** from §3.
7. **Default device type / profile:** often left to converter output; ensure new devices are allowed to be **auto-provisioned** with types **Zone1_Sensor** / **Zone2_Sensor** (map **device type** → **device profile** where the UI offers it).
8. **Save**. Start or restart integration if there is an explicit control.

---

## 5. Smoke test ingestion

1. **CE:** start **`tb-chirpstack-bridge`** (§4a). **PE:** ensure the MQTT integration is enabled (§4b).
2. Start **`gateway_activator.py`** (if gateways must show activity) and **node simulators** (`run_all_nodes.py` or **`SIM_TELEMETRY_INTERVAL=30`** for a quicker test — see `.env`).
3. In ThingsBoard: **Devices**. Within a few telemetry intervals you should see **10 devices** with types **Zone1_Sensor** / **Zone2_Sensor**.
4. Open one device → **Latest telemetry**. Values **temperature**, **humidity**, **leaf_wetness**, **rainfall** should refresh.

If devices never appear:

- Confirm §0 (MQTT `application/#` on Mosquitto).
- **CE:** `docker compose ps tb-chirpstack-bridge` is **Up**; **`docker compose logs tb-chirpstack-bridge`** for HTTP 401/404; **`TB_USERNAME` / `TB_PASSWORD`** are a **tenant** user; profiles **Zone1_Sensor** / **Zone2_Sensor** exist.
- **PE:** integration **Enabled**, host **`mosquitto`**, port **1883**, topic **`application/+/device/+/event/up`**; **Integration events** / **Errors** (or `docker compose logs thingsboard --tail 120`).

---

## 6. Disease Risk Engine rule chain

Implements Assignment-style risk logic (`thingsboard/rule_engine/RULE_CHAIN.md`).

### 6a. Initial attribute (recommended)

The script in **`disease_risk_script.js`** expects server attribute **`riskEngineState`**. If absent, it starts from **`{ mod: 0, high: 0, rains: [], prevRisk: "LOW" }`**.  

You **do not** have to pre-create attributes on each device—the first telemetry run initializes state. Optionally set **`riskEngineState`** manually on devices for repeatable demos:

```json
{"mod":0,"high":0,"rains":[],"prevRisk":"LOW"}
```

### 6b. Build the chain

1. **Rule chains → Add rule chain**, name **`Disease Risk Engine`** (or similar).
2. Wire the nodes (see **`thingsboard/rule_engine/RULE_CHAIN.md`** for the parallel branches). From the **Disease risk** transformation, connect **three** outputs: **Save timeseries**, the **POST_ATTRIBUTES** mini-transform → **Save attributes**, and the **Raise alarm?** script filter → **Create alarm**.

   | Order | Node | Notes |
   |-------|------|------|
   | 1 | **Message type filter** | Only **Post telemetry**. |
   | 2 | **Get Attributes** | Scope **Server**, keys **`riskEngineState`**. |
   | 3 | **Transformation script** | Paste **`thingsboard/rule_engine/disease_risk_script.js`**. |
   | 4 | **Save timeseries** | Persists env + **`risk_level`**, **`rain_sum_24h`**, etc. TB 4.2+: **TbMsgTimeseriesNode**. |
   | 5 | **Transformation script** (short) | Emit **`POST_ATTRIBUTES_REQUEST`** with **`{ "riskEngineState": ... }`** only. |
   | 6 | **Save attributes** | Server scope. TB 4.2+ CE: use the **save attributes** component implemented as **`TbMsgAttributesNode`** (do **not** pick a legacy **`TbSaveAttributesNode`** class — it may be absent in the Docker image). |
   | 7 | **Script filter** | `return msg.raiseFarmerAlarm === true;` (branch still carries **Post telemetry**). |
   | 8 | **Create alarm** | e.g. type **High crop risk**; email needs **Settings → Mail** if you add **Send email**. |

3. **Automated option:** **`py -3 scripts/provision_tb_assignment.py`** (reads **`TB_*`** from **`chirpstack/chirpstack-docker/.env`**). Prefer Compose image **`thingsboard/tb-postgres:4.2.1.1`**, not unversioned **`latest`**. It writes **`thingsboard/artifacts/exports/rule_chain_disease_risk_engine.import.json`** (**Rule chains → Import**), with **`…provisioned_metadata.json`** as a fallback. If the editor still shows only **Input**, import that file or finish wiring manually.

4. Attach this chain on **Device profiles** **Zone1_Sensor** and **Zone2_Sensor** (default / telemetry rule chain).

### 6c. Export

**Rule chains → ⋮ → Export** → save e.g. `thingsboard/artifacts/exports/rule_chain_disease_risk.json`.

---

## 7. Farmer dashboard

Per **`thingsboard/dashboards/FARMER_DASHBOARD.md`**:

1. **Dashboards → + → Create new** (e.g. **Farmer Crop Risk**).
2. Add aliases: **`Zone1_Sensor`** / **`Zone2_Sensor`** device types or named device lists.
3. Widgets: **risk per zone**, **temperature/humidity** time series, **rainfall** bars, **Alarms** table.
4. **Save**; **Export** JSON → `thingsboard/artifacts/exports/dashboard_farmer.json`.

---

## 8. Zone 2 access tokens OTA / sidecars

For **`thingsboard_tb_sidecar.py`** (spawned from **`run_all_nodes.py`** when enabled):

1. In ThingsBoard, open each **Zone 2** device → **Device credentials** → copy **MQTT access token**.
2. Paste into **`chirpstack/chirpstack-docker/config/devices.json`** → **`thingsboard_access_token`** for nodes 6–10 (replace **`REPLACE_TB_TOKEN_*`**).
3. In **`.env`**: **`ENABLE_TB_SIDECARS=1`** (default), valid **`MQTT_HOST` / MQTT_PORT`** for simulators toward ChirpStack.

OTA UI flow & rollback script: **`thingsboard/rule_engine/OTA_ROLLBACK_NOTE.md`**, **`thingsboard/scripts/rollback_watchdog.py`**, **`VERIFICATION_AND_TESTING.md`** §§9–10.

---

## 9. One-glance verification

| Check | Pass |
|--------|------|
| TB UI loads | Login works |
| Integration | MQTT connected, **no** repeated errors |
| Devices | **10** devices with correct profiles |
| Latest telemetry | Four weather fields updating |
| Rule chain | **risk_level** (and **`riskEngineState`**) updating |
| Dashboard | Charts move with simulators |
| *(Optional)* Zone 2 tokens | **`fw_state`** in device telemetry / sidecar logs |

---

## 10. Repo file index

| Topic | Path |
|--------|------|
| Integration & broker snippet | `thingsboard/integrations/INTEGRATION_SETUP.md` |
| Converter source | `thingsboard/integrations/chirpstack_uplink_converter.js` |
| Device profiles checklist | `thingsboard/device_profiles/README.md` |
| Rule chain wiring | `thingsboard/rule_engine/RULE_CHAIN.md` |
| Risk script | `thingsboard/rule_engine/disease_risk_script.js` |
| Dashboard widget list | `thingsboard/dashboards/FARMER_DASHBOARD.md` |
| Submission exports | `thingsboard/artifacts/README_ARTIFACT_EXPORTS.md` |
| ChirpStack codec | `thingsboard/chirpstack/payload_codec.js` |
| Full stack checklist | `docs/VERIFICATION_AND_TESTING.md` |
