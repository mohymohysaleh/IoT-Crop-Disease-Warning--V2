/**
 * ChirpStack v4 device-profile payload codec (JavaScript).
 * Matches binary payload from node_simulator.py: struct.pack(">hBBH", temp*100, hum, leaf, rain*10)
 *
 * In ChirpStack: Device profiles → your profile → Codec → JavaScript tab.
 */
function decodeUplink(input) {
  var bytes = input.bytes;
  var fPort = input.fPort;
  if (fPort !== 1) {
    return { data: {} };
  }
  if (bytes.length < 6) {
    return { data: {} };
  }
  var t = (bytes[0] << 8) | (bytes[1] & 0xff);
  if (t > 32767) {
    t -= 65536;
  }
  var temperature = t / 100.0;
  var humidity = bytes[2];
  var leaf_wetness = bytes[3];
  var rainRaw = (bytes[4] << 8) | (bytes[5] & 0xff);
  var rainfall = rainRaw / 10.0;
  return {
    data: {
      temperature: temperature,
      humidity: humidity,
      leaf_wetness: leaf_wetness,
      rainfall: rainfall,
    },
  };
}

function encodeDownlink(input) {
  return {};
}
