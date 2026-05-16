# IoT Crop Disease Early Warning — Assignment 2 (ThingsBoard track)

Student project for **SWAPD 453 Spring 2026**. It wires **ChirpStack v4** LoRaWAN simulation to **ThingsBoard CE** using Docker Compose on the developer workstation.

## Prerequisites

- Docker Desktop (Compose v2)
- Python 3.10+ (`py -3 …` on Windows)

```powershell
py -3 -m pip install -r chirpstack/chirpstack-docker/requirements-assignment.txt
```

### Environment file (optional)

Copy the template and edit secrets locally (the real `.env` is gitignored):

```powershell
Copy-Item chirpstack\chirpstack-docker\.env.example chirpstack\chirpstack-docker\.env
```

Variables are loaded automatically by `run_all_nodes.py`, `gateway_activator.py`, `simulate_uplink.py`, **`node_simulator.py`** (when run standalone), `thingsboard_tb_sidecar.py`, and `thingsboard/scripts/rollback_watchdog.py` / `rogue_mqtt_client.py` when `python-dotenv` is installed.

## Bring-up

```powershell
cd chirpstack/chirpstack-docker
docker compose pull   # first run downloads ThingsBoard (~GB)
docker compose up -d
```

| Endpoint | Purpose |
|----------|---------|
| http://localhost:8080 | ChirpStack UI |
| http://localhost:8090 | ChirpStack REST (optional automation) |
| http://localhost:9090 | ThingsBoard CE — default `sysadmin@thingsboard.org` / `sysadmin` (**change immediately**) |
| mosquitto | Shared MQTT — this repo exposes host **`localhost:1884`** (mapped **1884:1883** into the Docker broker; set **`MQTT_HOST` / `MQTT_PORT`** in `.env` to match) |
| ThingsBoard devices `:11883` | Mapped to TB transport MQTT |

**ChirpStack login failing, empty Tenants/apps, or gateways/devices vanished?** From `chirpstack/chirpstack-docker`, try **`.\scripts\Repair-ChirpStackTenantLinks.ps1`** (non-destructive). For a full replay of the bundled seed use **`.\scripts\Reset-ChirpStackPostgres.ps1`**, then **set-password** as printed ([`docs/VERIFICATION_AND_TESTING.md`](docs/VERIFICATION_AND_TESTING.md) §2).

### Configure ChirpStack & ThingsBoard (high level)

1. Provision applications/devices + gateways EUIs (`aa00000000000001`, `aa00000000000002`).
2. Install codec [`thingsboard/chirpstack/payload_codec.js`](thingsboard/chirpstack/payload_codec.js) on the matching device profile.
3. Ensure application integration emits MQTT events (`application/+/device/+/event/up`).
4. Paste [`thingsboard/integrations/chirpstack_uplink_converter.js`](thingsboard/integrations/chirpstack_uplink_converter.js) into ThingsBoard MQTT integration uplink converter.
5. Implement rule chain described in [`thingsboard/rule_engine/RULE_CHAIN.md`](thingsboard/rule_engine/RULE_CHAIN.md).

**Detailed ThingsBoard UI steps** (profiles, MQTT integration, converter, rule chain, dashboard, OTA): [`docs/THINGSBOARD_FULL_SETUP.md`](docs/THINGSBOARD_FULL_SETUP.md).

### Run the simulators

```powershell
cd chirpstack/chirpstack-docker
py -3 run_all_nodes.py        # logs under .\logs\
```

Defaults: **300 s** cadence, RNG seed `453`, optional ThingsBoard OTA sidecars if you replace `thingsboard_access_token` values in [`config/devices.json`](chirpstack/chirpstack-docker/config/devices.json) and export `ENABLE_TB_SIDECARS=1` (default).

Environment highlights:

| Variable | Effect |
|----------|--------|
| `THINGSBOARD_MQTT_HOST`, `THINGSBOARD_MQTT_PORT` | MQTT target for sidecars (default `localhost:11883`). |
| `ENABLE_TB_SIDECARS` | Set `0` to skip TB clients even when tokens exist. |
| `TB_OTA_SIMULATE_FAIL` | Forces FAILED `fw_state` for rollback demos. |
| `CHIRPSTACK_REST_TOKEN` | Optional: ChirpStack UI → API keys (for custom REST scripts). `simulate_uplink.py` uses **MQTT** (`config/devices.json`), not this token. |

Rollback helper:

```powershell
py -3 thingsboard/scripts/rollback_watchdog.py
```

(Optional attack demo) `thingsboard/scripts/rogue_mqtt_client.py`

## Verification (what to expect & how to test)

Single checklist: **[`docs/VERIFICATION_AND_TESTING.md`](docs/VERIFICATION_AND_TESTING.md)** — includes fixing gateway **“Never seen”** (register gateways in ChirpStack with IDs `aa00000000000001` / `aa00000000000002`).

## Documentation & deliverables

| Artifact | Path |
|----------|------|
| Printable report (convert to PDF for submission) | [`docs/ASSIGNMENT2_REPORT.md`](docs/ASSIGNMENT2_REPORT.md) |
| Demo outline | [`docs/DEMO_VIDEO_SCRIPT.md`](docs/DEMO_VIDEO_SCRIPT.md) |
| Submission ZIP builder | `py -3 scripts/build_submission_zip.py` → `ASSIGNMENT2_SUBMISSION.zip` |
| Pre-submit checks (files, TB optional, docker optional) | `py -3 scripts/verify_assignment_ready.py` (+ `--tb` `--docker`) |
| Export TB dashboard + rule chains to `artifacts/exports/` | `py -3 scripts/export_tb_artifacts.py` (ThingsBoard must be running; uses `.env` `TB_*`) |
| Report -> PDF (needs [pandoc](https://pandoc.org/installing.html)) | `py -3 scripts/build_report_pdf.py` -> `ASSIGNMENT2_REPORT.pdf` |
| Export TB JSON into | `thingsboard/artifacts/exports/` |

## Reference PDFs (course brief)

Files in repo root: `Assignment 2.docx.pdf` (AWS baseline), `Assignment-2_Azure.docx.pdf`, `Assignment_2_ThingsBoard.docx.pdf`.

## License

Upstream ChirpStack Compose skeleton retains its original license; additions for this course deliverable are provided as educational examples only.
