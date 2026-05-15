// ThingsBoard "Script" rule node (JavaScript) — runs AFTER "Get Attributes" with server scope key riskEngineState.
// Wire: Telemetry received → Get attributes (riskEngineState) → This script → Save attributes (riskEngineState) → Save timeseries → route on raiseFarmerAlarm.
//
// Telemetry cadence assumption: uplink every 300 s → 36 consecutive readings ≈ 3 h, 72 ≈ 6 h.

var MOD_SLOTS = 36;
var HIGH_SLOTS = 72;
var RAIN_WINDOW = 288; // readings in 24 h at 5 min cadence

function safeParse(s, def) {
  if (s == null || s === "") return def;
  try {
    return JSON.parse(String(s));
  } catch (e) {
    return def;
  }
}

function deepCopy(obj) {
  return JSON.parse(JSON.stringify(obj || {}));
}

var t = Number(msg.temperature);
var h = Number(msg.humidity);
var lw = Number(msg.leaf_wetness);
var rainStep = Number(msg.rainfall);

var defState = { mod: 0, high: 0, rains: [], prevRisk: "LOW" };
var rawState = metadata.ss_riskEngineState;
var state = safeParse(rawState, null);
if (state == null) {
  state = deepCopy(defState);
}
if (state.rains == null) state.rains = [];

state.rains.push(Number(rainStep));
if (state.rains.length > RAIN_WINDOW) {
  state.rains = state.rains.slice(state.rains.length - RAIN_WINDOW);
}
var rain24 = 0;
for (var i = 0; i < state.rains.length; i++) {
  rain24 += state.rains[i];
}

var risk = "LOW";
if (h < 70 || t < 15 || t > 35) {
  state.mod = 0;
  state.high = 0;
  risk = "LOW";
} else {
  if (h >= 70 && h <= 85 && t >= 15 && t <= 25) {
    state.mod = (state.mod || 0) + 1;
  } else {
    state.mod = 0;
  }
  if (h > 85 && t >= 18 && t <= 25) {
    state.high = (state.high || 0) + 1;
  } else {
    state.high = 0;
  }

  var highEnough = state.high >= HIGH_SLOTS;
  if (highEnough && lw > 8 && rain24 > 5) {
    risk = "CRITICAL";
  } else if (highEnough) {
    risk = "HIGH";
  } else if (state.mod >= MOD_SLOTS) {
    risk = "MODERATE";
  } else {
    risk = "LOW";
  }
}

var prev = state.prevRisk || "LOW";
var raised =
  risk === prev
    ? false
    : (risk === "HIGH" || risk === "CRITICAL");
state.prevRisk = risk;

msg.risk_level = risk;
msg.riskEngineState = JSON.stringify({
  mod: state.mod,
  high: state.high,
  rains: state.rains,
  prevRisk: state.prevRisk,
});
msg.raiseFarmerAlarm = raised;
msg.rain_sum_24h = rain24;

return { msg: msg, metadata: metadata, msgType: msgType };
