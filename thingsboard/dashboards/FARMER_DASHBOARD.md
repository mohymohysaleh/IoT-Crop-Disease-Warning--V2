# Farmer dashboard (ThingsBoard)

Create a dashboard **Farmer Crop Risk** with these widgets (Assignment §3.2 #7):

| Widget | Type | Data source |
|--------|------|-------------|
| **Risk by zone** | Entities table or Alias-based cards | Device type `Zone1_Sensor` / `Zone2_Sensor`, attribute or latest telemetry `risk_level` |
| **Temperature & humidity** | Time-series chart | Alias: all zone devices, keys `temperature`, `humidity` |
| **Rainfall bursts** | Bar chart (last 24–48 h) | `rainfall` telemetry |
| **Alert history** | Alarms table | Filter type `High crop risk` (or your alarm type) |

### Entity aliases

Add two device type aliases (e.g., `zone1_devices` → type = `Zone1_Sensor`, `zone2_devices` → type = `Zone2_Sensor`) or a single query alias for all ten devices.

After configuring, **Export** the dashboard JSON into `thingsboard/artifacts/exports/dashboard_farmer.json` for your ZIP.

---

## Step-by-step (ThingsBoard Community Edition)

Labels vary slightly by version (3.x vs 4.x). Use **Tenant Administrator**. Telemetry must be flowing (`risk_level` appears only **after** your Disease Risk rule chain runs).

### A. Open or create the dashboard

1. Left menu **Dashboards**.
2. Open **Farmer Crop Risk** (or **+** → **Create new dashboard** → **Title:** `Farmer Crop Risk` → **Add**).
3. Click **Open dashboard**.
4. Click the **pencil (Edit)** icon to enter **edit mode**.

### B. Entity aliases (do this before adding widgets)

1. In edit mode, open **Entity aliases** (often a shield/chain icon, **“Entity aliases”**, or under the **gear / Dashboard settings** menu at the top).
2. **+ Add alias** for Zone 1:
   - **Alias name:** `zone1_devices` (exact name helps when you wire widgets).
   - **Filter / resolution:** choose whatever your build offers to select **multiple devices** whose **type** is **`Zone1_Sensor`**.
     - Common patterns: **Device type** = `Zone1_Sensor`, **Entity list** with **Type** filter, or **Devices** filtered by **Device profile** = **Zone1_Sensor**.
   - Save the alias.
3. **+ Add alias** for Zone 2:
   - **Alias name:** `zone2_devices`
   - Same idea: **type** or **profile** = **`Zone2_Sensor`**.
4. Optional **all-zone alias** for charts:
   - **Alias name:** `all_field_devices`
   - Filter: **Entity list** → include **both** `zone1_devices` and `zone2_devices`, or a single query that returns all 10 devices (if your TB version supports **multiple filters** / **group**).

If you cannot find “device type” in the filter, pick **Entity list** → add **each of the 10 devices** manually once; the dashboard will still work.

### C. Widget 1 — Risk by zone

**Option 1 — Entities table**

1. **+ Add new widget** → **Tables** → **Entities table** (or **Alarms / Entities** table depending on skin).
2. **Add** → **Datasources** → **Entity alias:** `zone1_devices` (or add two widgets: one for `zone1_devices`, one for `zone2_devices`).
3. **Columns / Data keys:** add **Latest telemetry** (or **Timeseries** latest) **`risk_level`**. Add **entityName** if you want the devEUI / device name column.
4. **Title:** e.g. `Risk – Zone 1`. Repeat for Zone 2 if you use one table per zone.

**Option 2 — Cards**

1. **+ Add new widget** → **Cards** → **Markdown / Value / HTML value** or **Entities count / Latest values** (pick what your CE build lists).
2. Point datasource to `zone1_devices` / `zone2_devices` and display **`risk_level`** (often via “Latest values” with key `risk_level`).

### D. Widget 2 — Temperature & humidity (time-series chart)

1. **+ Add new widget** → **Charts** → **Timeseries line chart** (or **Timeseries**).
2. **Datasources:** entity alias **`all_field_devices`** (or **`zone1_devices` + `zone2_devices`** if you add two series groups — some UIs want one alias per chart).
3. **Timeseries keys:** add **`temperature`** and **`humidity`** (two keys; often under **Columns** / **Series**).
4. Set **Legend** to show **entity** + **key** so you can tell devices apart.
5. **Time window** (dashboard or widget): **Last 24 hours** (or live **last 1 h** for a demo).

### E. Widget 3 — Rainfall bursts (bar chart)

1. **+ Add new widget** → **Charts** → **Bar chart** (or **Timeseries bar**).
2. **Datasource:** same alias as above (`all_field_devices` or per-zone aliases).
3. **Key:** **`rainfall`**.
4. **Interval:** align with your uplink period (e.g. **5 minutes** if `SIM_TELEMETRY_INTERVAL=300`), or **1 hour** bars for a smoother chart.
5. **Window:** **Last 24–48 hours** as required by the brief.

### F. Widget 4 — Alert history

1. **+ Add new widget** → **Alarm widgets** → **Alarms table** (or **Alarm table**).
2. Configure **Entity / Alarm source:** often **All** for tenant, or restrict to aliases `zone1_devices` + `zone2_devices`.
3. **Alarm type:** set the **same type name** you used in **Create Alarm** in the rule chain (e.g. `High crop risk` as in this doc — must match your chain exactly).
4. **Severities / Status:** show **Active** + **Acknowledged** as needed for the demo.

### G. Save and export

1. **Save** the dashboard (floppy icon or **Save** in the top bar).
2. **Exit edit** when finished.
3. **Export:** **Dashboards** → row **Farmer Crop Risk** → **⋮** (kebab) → **Export dashboard** → save as **`dashboard_farmer.json`** under **`thingsboard/artifacts/exports/`**.
4. Or run: `py -3 scripts/export_tb_artifacts.py` from the repo root (re-reads from your live ThingsBoard).

### H. If a widget shows “No data”

| Symptom | What to check |
|---------|----------------|
| No `risk_level` | Rule chain not assigned, or **Save Timeseries** not persisting `risk_level`; run simulators and open **Device → Latest telemetry**. |
| Empty alias | Device **type** in TB must be **`Zone1_Sensor`** / **`Zone2_Sensor`** (matches bridge + profiles). |
| Alarms table empty | Alarm type string mismatches rule **Create Alarm**; trigger a test alarm from the chain. |
