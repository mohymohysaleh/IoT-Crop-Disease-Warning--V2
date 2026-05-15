# Disease Risk Engine rule chain (ThingsBoard CE)

Models Assignment 2 §2.2 assuming uplinks every **300 s**: **36** consecutive qualifying readings (~3 h) → MODERATE, **72** (~6 h) → HIGH rolling base, CRITICAL adds **leaf_wetness > 8** and **sum(rainfall over 288 samples) > 5 mm**.

## Node wiring

1. After your integration posts telemetry for the sensor device → **Script filter** optional (drop empty payloads).
2. **Get Attributes** — scope **Server**, keys: `riskEngineState`, `tellFailureIfAbsent`: false.  
   The next node receives `metadata.ss_riskEngineState` (server-scope string JSON).
3. **Transformation script** — paste [disease_risk_script.js](disease_risk_script.js).
4. **Save Attributes** — server scope — map message field **`riskEngineState`** (ThingsBoard picks `msg`-level key).
5. **Save Timeseries** — persist `temperature`, `humidity`, `leaf_wetness`, `rainfall`, `risk_level`, `rain_sum_24h`.
6. **Script filter**: `return msg.raiseFarmerAlarm === true;`
7. **Create Alarm** (severity MINOR for HIGH / CRITICAL) *and/or* **To Email / Send Email** once SMTP is configured under **Settings → Mail**.

Export the finished chain JSON into `thingsboard/artifacts/` for the submission ZIP (**Rule chains → ⋮ → Export**).
