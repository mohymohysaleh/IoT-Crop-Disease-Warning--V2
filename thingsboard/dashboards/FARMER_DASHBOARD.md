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
