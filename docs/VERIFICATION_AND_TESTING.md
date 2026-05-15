# Verification & testing (full stack)

Use this as the single checklist when you want to prove ChirpStack → MQTT → ThingsBoard → rules → OTA are working.

**Ports (defaults in this repo):** ChirpStack UI **8080**, ChirpStack REST **8090**, ThingsBoard UI **9090**, **Mosquitto on host `localhost:1884`** (Docker maps **`1884:1883`** into the Mosquitto container), ThingsBoard device MQTT **`localhost:11883`**.

---

## 1. Docker

```powershell
cd D:\down\IoT-Crop-Disease-Warning--V2\chirpstack\chirpstack-docker
docker compose ps
```

**Expect:** `chirpstack`, `mosquitto`, `postgres`, `redis`, `thingsboard`, gateway-bridge services **running**.

**If not:** `docker compose logs <service> --tail 80`

---

## 2. ChirpStack UI & registration

Open **http://localhost:8080**, sign in.

### Tenants / apps missing in UI (but you can log in)

**Diagnose:**

```powershell
docker compose exec -T postgres psql -U chirpstack -d chirpstack -c "SELECT (SELECT COUNT(*) FROM tenant) AS tenants, (SELECT COUNT(*) FROM application) AS apps, (SELECT COUNT(*) FROM device) AS devices, (SELECT COUNT(*) FROM gateway) AS gws, (SELECT COUNT(*) FROM tenant_user) AS tenant_users;"
```

- **`tenants = 0` but `apps > 0`:** orphaned DB (tenant rows were removed). Applications still reference the old tenant UUID—ChirpStack shows nothing useful until Postgres is repaired or reset.
- **`apps > 0` but `devices = 0`:** only metadata remains; redo **`.\scripts\Reset-ChirpStackPostgres.ps1`** to replay the full **`002-data.sql`** bundle (devices, gateways, sessions, keys).

**Non-destructive repair (fixes missing tenant + `tenant_user` only):** from `chirpstack/chirpstack-docker`:

```powershell
.\scripts\Repair-ChirpStackTenantLinks.ps1
```

Reload the UI (hard refresh). Then **Tenants → ChirpStack → Applications** (Zone 1 / Zone 2). The network-level **Dashboard** can stay empty until gateways/devices send traffic—it is not where applications are listed.

`Repair-ChirpStackTenantLinks.ps1` runs **`scripts/repair_chirpstack_visibility.sql`** (same logic as **`003-tenant-user-from-admin.sql`**, plus **tenant resurrection** from `application.tenant_id` / `gateway.tenant_id`).

If SQL still shows **`devices = 0`** or **`gateways = 0`** after repair, Postgres was partially wiped—run **`Reset-ChirpStackPostgres.ps1`** so **`002-data.sql`** reloads everything (**ThingsBoard volumes** stay unless you remove them separately).

**Full reset (broken login + empty devices/gateways):** from `chirpstack/chirpstack-docker`, run:

```powershell
.\scripts\Reset-ChirpStackPostgres.ps1
```

**Run only in PowerShell** (above is correct). Using **`python`** / **`py`** on a `.ps1` file hits a Python SyntaxError—that is expected.

**If reset ends with **`public.user row count still 0`** after several minutes:** init likely **failed midway**—check Postgres logs **`docker compose logs postgres --tail 120`** for **`ERROR`** on **`002-data.sql`** (often a **`COPY`** line). When `COPY device` fails, later tables (including **`public.`"user"**) never load. Fix the bundled SQL from the repo, **remove only** the Postgres volume again (or rerun **`Reset-ChirpStackPostgres.ps1`**), then `docker compose up -d`.

(Type `RESET` when asked.) That **only** wipes the Compose **Postgres** volume and replays `configuration/postgresql/initdb/*.sql` (seeded UI user **`admin@local`** in **`public."user".email`**, **`tenant_user`** linked to tenant **ChirpStack**, 2 apps, 10 devices, 2 gateways). The reset script reads the actual **`email`** from Postgres and prints the matching **`set-password --email …`** command. Optional: set `$env:CHIRPSTACK_BOOTSTRAP_PASSWORD` before running with `-Force` to set the password non-interactively (remove the variable after).

### Login rejected / “credentials failed”

ChirpStack stores UI users in PostgreSQL in the table **`public."user"`**. If that table is **empty**, **no combination of email and password works** until you recreate an admin account (usually by re-seeding Postgres; see **“Everything disappeared”** below).

Count users (same compose directory as §1):

```powershell
@"
SELECT COUNT(*) AS n_login_users FROM public."user";
SELECT email FROM public."user";
"@ | docker compose exec -T postgres psql -U chirpstack -d chirpstack
```

- **`n_login_users = 0`:** recreate the Postgres volume so `configuration/postgresql/initdb/*.sql` loads again (**includes one admin row**). This repo’s dump uses **`admin@local`** as **`email`**; always confirm with **`SELECT email`** above.

- **`n_login_users > 0`:** **`chirpstack set-password`** matches **`public."user".email` exactly**. The login field on the UI is that same string (this repo **`admin@local`**). The password hash in the dump is **not** the same as stock “fresh install” docs.

  After login, if you still see empty tenants/apps, run **`.\scripts\Repair-ChirpStackTenantLinks.ps1`** (fills **`tenant_user`** when missing).

  Set a password you choose with the CLI **inside** the ChirpStack container (**`-it`** so prompted twice), using the email from **`SELECT email FROM public."user";`**:

  ```powershell
  docker compose exec -it chirpstack chirpstack --config /etc/chirpstack set-password --email YOUR_EMAIL_FROM_SELECT
  ```

  If you see **`Object does not exist (id: …)`**, ChirpStack could not find a user whose **`email`** equals the value you passed (the message labels it “id” even when you used **`--email`**). Fix: use the exact string from **`SELECT email FROM public."user";`**. If the table is still empty, wait for init or run **`.\scripts\Reset-ChirpStackPostgres.ps1`** (PowerShell, not `py`).

For a **fresh** ChirpStack install created by the installer (not from this repo’s SQL seed), upstream docs typically use **`admin` / `admin`** until you change it — **do not rely on that** after loading this repo’s init SQL.

---

### Gateways (fix “Never seen”)

**ChirpStack only updates “Last seen” for gateways that exist in the database.** Stats MQTT alone is not enough if the gateway was never added.

1. **Tenants → Gateways** — if you **re-seeded** from this repo, **`aa00000000000001`** and **`aa00000000000002`** are usually **already** listed. If either is missing, **Add** a gateway whose **Gateway ID** is exactly that string (same tenant as your apps; 16 hex chars, lowercase is fine).
2. Run **`gateway_activator.py`** (keep it running). It publishes **GatewayStats** on `eu868/gateway/<id>/event/stats` — that is what the ChirpStack Network Server consumes for **Last seen** (same broker as the `mosquitto` service in Docker). It may also publish **ConnState** on `.../state/conn` for MQTT integrations; the NS gateway MQTT backend listens on **`.../event/...`** topics.

3. Within about **1 minute**, gateways should show as **online** / **last seen** updating.

**Still “Never seen”?**

- **Windows: two programs on port 1883 (very common).** ChirpStack in Docker talks to the **Mosquitto container** (port **1883 inside** the container). On the **host**, this repo maps **`1884:1883`**, and Python simulators default to **`MQTT_PORT=1884`** so they hit the same broker. If you override compose to **`1883:1883`**, put **`MQTT_PORT=1883`** in `.env`.

  If something else listens on **`127.0.0.1:1884`** instead, change the compose host port accordingly and set **`MQTT_PORT`** to match.

  **Legacy note:** **`gateway_activator.py`** / **`simulate_uplink.py`** previously defaulted to **`1883`**, which silently hit a **different** Mosquitto on Windows when Docker used **1884** on the host.

  Use **`netstat -ano`** to see which PID owns host **`MQTT_PORT`**.

- In another terminal (same compose directory), confirm traffic on **the broker ChirpStack uses** (from **inside** the Mosquitto container):

  ```powershell
  docker compose exec mosquitto mosquitto_sub -h 127.0.0.1 -p 1883 -t "eu868/gateway/#" -v
  ```

  You should see **`.../event/stats`** (ChirpStack updates **Last seen** from these). If **nothing** appears while the activator runs, it is not publishing to this broker — fix host/port (see Windows note above) or restart compose.

- Check ChirpStack logs: `docker compose logs chirpstack --tail 100`

- Confirm **EU868** region is enabled and topic prefix is **`eu868`** (matches `gateway_activator` and `node_simulator`).

### Applications & devices

- You have an **Application** and **10 devices** with DevEUIs / DevAddr / session keys aligned with **`config/devices.json`**.
- Devices are **activated** (ABP) and use the correct **device profile** (with payload codec if you decode in ChirpStack).

### “Everything disappeared” (empty devices / gateways)

ChirpStack keeps tenants, applications, devices, gateways, and **UI login users** in **PostgreSQL**. Simulators and MQTT scripts **do not** delete registrations — if lists look empty, rows were removed (manual deletes in the UI, experiments with SQL, or a broken restore).

**Login:** if **`public."user"`** has zero rows (see § “Login rejected” above), signing in **always fails** until you re-seed or create a user.

**Check row counts:**

```powershell
cd D:\down\IoT-Crop-Disease-Warning--V2\chirpstack\chirpstack-docker
docker compose exec postgres psql -U chirpstack -d chirpstack -c "SELECT (SELECT COUNT(*) FROM tenant) AS tenants, (SELECT COUNT(*) FROM application) AS apps, (SELECT COUNT(*) FROM device) AS devices, (SELECT COUNT(*) FROM gateway) AS gateways;"
```

- **Apps exist but `devices = 0` or `gateways = 0`:** recreate missing objects (§2 gateways + applications/devices aligned with **`config/devices.json`**) **or** re-seed Postgres below.

**Full re-seed from this repo (wipes only ChirpStack Postgres — ThingsBoard keeps `thingsboard-data` unless you remove it):**

PostgreSQL runs `configuration/postgresql/initdb/*.sql` **only when the data directory is empty**. To replay **`002-data.sql`** (bundled Zone 1/2 apps, **10 devices**, **2 gateways**, keys, codec profile):

```powershell
cd D:\down\IoT-Crop-Disease-Warning--V2\chirpstack\chirpstack-docker
docker compose down
docker volume ls
# Remove the Postgres volume for this compose project (name often ends with `_postgresqldata`), e.g.:
docker volume rm chirpstack-docker_postgresqldata
docker compose up -d
```

Use the volume name shown by `docker volume ls` for **this** project. After Postgres starts, ChirpStack should show seeded apps/devices/gateways again — then follow **Login rejected** above: use **`set-password --email`** with the exact string from **`SELECT email FROM public."user";`** (the reset script prints this for you) after `COUNT(*)` is at least **1**.

---

## 3. Node simulators

```powershell
cd D:\down\IoT-Crop-Disease-Warning--V2\chirpstack\chirpstack-docker
py -3 run_all_nodes.py
```

**Expect:** `logs\node1.log` … `node10.log` with uplink lines and **✓** on publish.

**Optional:** `py -3 simulate_uplink.py` publishes the same style of **gateway `event/up`** frames for **all** devices in **`config/devices.json`** from a single process (ChirpStack v4’s REST API does **not** expose a device uplink simulator — any `…/simulate-uplink` URL returns **404**).

**Timing:** default **`SIM_TELEMETRY_INTERVAL=300`** (5 min) in `.env` → sparse traffic is normal. For a quick test set **`SIM_TELEMETRY_INTERVAL=30`** in `chirpstack/chirpstack-docker/.env`, restart simulators, then set back to **300** for the assignment.

---

## 4. MQTT: gateways vs applications

Run **with simulators + activator** running.

**Gateway path (always check this first):**

```powershell
docker compose exec mosquitto mosquitto_sub -h 127.0.0.1 -p 1883 -t "eu868/#" -v
```

**Expect:** `.../event/up` from nodes and `.../event/stats` from the activator.

**Application path (ChirpStack integration events):**

```powershell
docker compose exec mosquitto mosquitto_sub -h 127.0.0.1 -p 1883 -t "application/#" -v
```

**Expect:** `application/<APP_ID>/device/<DEV_EUI>/event/up` **after** ChirpStack accepts uplinks for a **registered** device. If gateway traffic exists but **application** is empty: fix device activation / MIC / keys, or integration not publishing (ChirpStack application MQTT integration).

---

## 5. ChirpStack “device never seen”

If **gateways** are online but **devices** still show **never seen**:

- MQTT **`…/gateway/…/event/up`** must include valid **Protobuf-JSON metadata**: notably **`crcStatus`** set to **`CRC_OK`** (if omitted it defaults to “no CRC” and the Network Server tends to discard the packet). **`node_simulator.py`** / **`simulate_uplink.py`** set **`gwTime`** and a random **`uplinkId`** for ChirpStack v4 gateway-bridge JSON.
- Uplink frames must carry a **MIC-valid** PHY payload (DevAddr endianness / keys aligned with Postgres seed and **`config/devices.json`**).
- Default **`SIM_TELEMETRY_INTERVAL=300`** sends only every **5 minutes** — wait once, or set **`SIM_TELEMETRY_INTERVAL=30`** briefly for demos.
- In the compose directory confirm **`eu868`** traffic: **`docker compose exec mosquitto mosquitto_sub -h 127.0.0.1 -p 1883 -t "eu868/gateway/#" -v`** (you want **`event/up`**, not only **`event/stats`**).
- Inspect **`docker compose logs chirpstack --tail 120`** if frames show on MQTT but the UI ignores them.

If the **device** row shows **never seen** (narrower checks):

- Check **Live LoRaWAN frames** / **Events** tab for rejects (MIC / FCnt / disabled device).
- Compare **DevAddr**, **NwkSKey**, **AppSKey** in UI with `config/devices.json` **and** Postgres **`device_keys`** (this repo’s seed uses **`app_key` all zeros** for every node; **`app_skey`** in JSON must match **`SELECT encode(app_key,'hex') FROM device_keys`** or payloads decrypt wrongly and **last seen** never updates).
- **DevAddr in Postgres (`device.dev_addr`)** matches ChirpStack’s internal **big-endian** `DevAddr`: **`encode(dev_addr,'hex')`** equals the **`000000…`** hex in **`config/devices.json`** (PHY still uses LSByte‑first octets `01 00 00 00` on air for **`00000001`**). Wrong byte order yields **No device-session exists for dev_addr** even if keys are correct. Seeded **`device.device_session`** (ABP protobuf) must use the **same** DevAddr bytes as **`device.dev_addr`**.

---

## 6. ThingsBoard

Full step-by-step provisioning (MQTT integration → profiles → converter → rule chain → dashboard → OTA hooks): **`docs/THINGSBOARD_FULL_SETUP.md`**.

**http://localhost:9090** — log in (`sysadmin@thingsboard.org` / `sysadmin` by default; change password).

| Check | Good sign |
|--------|-----------|
| MQTT integration | Enabled; broker **`mosquitto:1883`** (from inside compose) or your host equivalent; topic **`application/+/device/+/event/up`**. |
| Devices | 10 devices; types **Zone1_Sensor** / **Zone2_Sensor** (or your naming). |
| Latest telemetry | **temperature**, **humidity**, **leaf_wetness**, **rainfall** updating. |

---

## 7. Rule chain & risk

- Telemetry includes **risk_level** (and any extras you added).
- **Alarms / mail** if configured when risk hits HIGH/CRITICAL (may need **SMTP** in ThingsBoard).

---

## 8. Dashboard

Widgets show **risk by zone**, **charts**, **rainfall**, **alarm history** and update while simulators run.

---

## 9. OTA (Zone 2)

1. Real **access tokens** in **`config/devices.json`** for node6–10 (not `REPLACE_...`).
2. **`ENABLE_TB_SIDECARS=1`** in `.env` (default).
3. Push firmware to profile **Zone2_Sensor** only.
4. **`logs\node6_tb_sidecar.log`** (etc.): **fw_state** DOWNLOADING → … → UPDATED (or **TB_OTA_SIMULATE_FAIL** for FAILED demo).

---

## 10. Rollback script (optional)

Fill **`.env`**: `TB_URL`, `TB_USERNAME`, `TB_PASSWORD`, `TB_ZONE2_PROFILE_ID`.

```powershell
py -3 D:\down\IoT-Crop-Disease-Warning--V2\thingsboard\scripts\rollback_watchdog.py
```

**Exit 0:** under threshold of FAILED devices; **exit 3:** rollback message printed.

---

## 11. “All green” in one glance

| Step | Pass criterion |
|------|----------------|
| Docker | `compose ps` all up |
| Gateways registered | Two gateways with IDs `aa...01` / `aa...02` |
| gateway_activator | Stats every 30 s; MQTT shows `event/stats` |
| Gateways UI | **Last seen** updates |
| Simulators | Logs show periodic **✓** |
| Devices UI / events | Uplinks / frames for all 10 |
| MQTT `application/#` | Uplink JSON when integration works |
| ThingsBoard | Telemetry keys updating |
| Risk / dashboard / OTA | As per your assignment wiring |

---

## 12. Related files

- **ThingsBoard walkthrough (profiles, integration, rule chain, dashboard):** `docs/THINGSBOARD_FULL_SETUP.md`
- Environment: `chirpstack/chirpstack-docker/.env.example` → copy to `.env`
- Integration JS: `thingsboard/integrations/chirpstack_uplink_converter.js`
- Rule chain: `thingsboard/rule_engine/RULE_CHAIN.md`
- Repo overview: `README.md`
