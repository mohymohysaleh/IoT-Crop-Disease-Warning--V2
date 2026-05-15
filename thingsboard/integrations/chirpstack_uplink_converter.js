/**
 * ThingsBoard MQTT integration → Uplink data converter (JavaScript).
 * Paste into Integrations → your ChirpStack MQTT integration → Data converter (Uplink).
 *
 * Prerequisite: ChirpStack device profile codec (see ../chirpstack/payload_codec.js)
 * so uplink JSON includes object.* fields. Otherwise decodeBase64(input.data) fallback runs.
 */
var Z2 = {
  "0000000000000006": true,
  "0000000000000007": true,
  "0000000000000008": true,
  "0000000000000009": true,
  "0000000000000010": true,
};

function zoneForEui(eui) {
  if (eui == null) {
    return "Zone_1";
  }
  var norm = ("" + eui).toLowerCase();
  return Z2[norm] ? "Zone_2" : "Zone_1";
}

function decodeBytesFromDataB64(b64) {
  if (b64 == null) {
    return null;
  }
  var bytes = decodeBase64(b64);
  if (bytes.length < 6) {
    return null;
  }
  var t = (bytes.charCodeAt(0) << 8) | (bytes.charCodeAt(1) & 0xff);
  if (t > 32767) {
    t -= 65536;
  }
  var temperature = t / 100.0;
  var humidity = bytes.charCodeAt(2);
  var leaf_wetness = bytes.charCodeAt(3);
  var rainRaw = (bytes.charCodeAt(4) << 8) | (bytes.charCodeAt(5) & 0xff);
  var rainfall = rainRaw / 10.0;
  return {
    temperature: temperature,
    humidity: humidity,
    leaf_wetness: leaf_wetness,
    rainfall: rainfall,
  };
}

function Decoder(payload, metadata) {

  var input = decodeToJson(payload);
  var dev = input.deviceInfo || {};
  var eui = (dev.devEui || dev.dev_eui || "").toLowerCase();
  var deviceName = dev.deviceName || eui || "unknown_device";
  var deviceType =
    eui && Z2[eui] ? "Zone2_Sensor" : "Zone1_Sensor";

  var telem = {};
  var obj = input.object;
  if (obj != null && typeof obj === "object") {
    var inner = obj.data != null && typeof obj.data === "object" ? obj.data : obj;
    if (inner.temperature != null) telem.temperature = inner.temperature;
    if (inner.humidity != null) telem.humidity = inner.humidity;
    if (inner.leaf_wetness != null) telem.leaf_wetness = inner.leaf_wetness;
    if (inner.rainfall != null) telem.rainfall = inner.rainfall;
  } else if (input.data != null) {
    var parsed = decodeBytesFromDataB64(input.data);
    if (parsed != null) {
      telem = parsed;
    }
  }

  return {
    deviceName: deviceName,
    deviceType: deviceType,
    attributes: { zone: zoneForEui(eui) },
    telemetry: telem,
  };
}
