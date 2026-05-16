# Disease Risk Engine rule chain (ThingsBoard CE)

Models Assignment 2 §2.2 assuming uplinks every **300 s**: **36** consecutive qualifying readings (~3 h) → MODERATE, **72** (~6 h) → HIGH rolling base, CRITICAL adds **leaf_wetness > 8** and **sum(rainfall over 288 samples) > 5 mm**.

## Node wiring

1. **Message type filter** — only **Post telemetry**.
2. **Get Attributes** — scope **Server**, keys: `riskEngineState`, `tellFailureIfAbsent`: false.  
   The next node receives `metadata.ss_riskEngineState` (server-scope string JSON).
3. **Transformation script** — paste [disease_risk_script.js](disease_risk_script.js) (still **`POST_TELEMETRY_REQUEST`**).
4. **Save Timeseries** — persist `temperature`, `humidity`, `leaf_wetness`, `rainfall`, `risk_level`, `rain_sum_24h`, etc.
5. **Transformation script** (small) — output **`POST_ATTRIBUTES_REQUEST`** with `{ "riskEngineState": "<json string>" }` only.  
   (The **Save attributes** node accepts **`POST_ATTRIBUTES_REQUEST`**, not raw telemetry.)
6. **Save Attributes** — server scope — persists `riskEngineState`.
7. **Script filter** (parallel branch from step 3): `return msg.raiseFarmerAlarm === true;`
8. **Create Alarm** (severity MINOR for HIGH / CRITICAL) *and/or* **To Email / Send Email** once SMTP is configured under **Settings → Mail**.

From the disease script output, connect **three** links: to **Save Timeseries**, to the **attributes** mini-transform, and to the **alarm** script filter.

Export the finished chain JSON into `thingsboard/artifacts/` for the submission ZIP (**Rule chains → ⋮ → Export**).
