import paho.mqtt.client as mqtt
import json, time, base64, struct, logging, sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

CONFIG = {
    "mqtt_host": "localhost",
    "mqtt_port": 1883,
    "gateways": [
        "aa00000000000001",  # Zone 1
        "aa00000000000002",  # Zone 2
    ]
}

def send_gateway_stats(client, gateway_eui: str):
    """
    Send a stats message to make ChirpStack see the gateway as Online.
    Topic: eu868/gateway/{id}/event/stats
    """
    stats = {
        "gatewayId": gateway_eui,
        "time":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "location": {
            "latitude":  30.0444,   # Cairo coords — change if you want
            "longitude": 31.2357,
            "altitude":  0
        },
        "configVersion": "1.0.0",
        "rxPacketsReceived":        10,
        "rxPacketsReceivedOk":      10,
        "txPacketsReceived":        0,
        "txPacketsEmitted":         0,
        "metadata": {
            "region_common_name": "EU868",
            "region_config_id":   "eu868"
        }
    }

    topic = f"eu868/gateway/{gateway_eui}/event/stats"
    result = client.publish(topic, json.dumps(stats), qos=1)
    log.info(f"Gateway {gateway_eui} → stats sent ({'✓' if result.rc == 0 else '✗'})")


def main():
    connected = [False]

    def on_connect(client, userdata, flags, rc, props=None):
        if rc == 0:
            connected[0] = True
            log.info("✓ Connected to MQTT broker")

    client = mqtt.Client(
        client_id="gateway-activator",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    client.on_connect = on_connect
    client.connect(CONFIG["mqtt_host"], CONFIG["mqtt_port"], keepalive=60)
    client.loop_start()
    time.sleep(1)

    log.info(f"Sending stats for {len(CONFIG['gateways'])} gateways every 30s...")
    log.info("Keep this running alongside your node simulators. Ctrl+C to stop.")

    while True:
        for gw_eui in CONFIG["gateways"]:
            send_gateway_stats(client, gw_eui)
        time.sleep(30)  # ChirpStack marks gateway offline if no stats for ~60s


if __name__ == "__main__":
    main()