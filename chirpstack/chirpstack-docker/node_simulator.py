import paho.mqtt.client as mqtt
import json, os, time, base64, random, math, argparse, logging, sys, struct, zlib
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None or not str(v).strip():
        return default
    try:
        return int(str(v).strip(), 10)
    except ValueError:
        return default


# ─── CONFIG ───────────────────────────────────────────────────────────────────
CONFIG = {
    "mqtt_host": os.environ.get("MQTT_HOST", os.environ.get("MOSQUITTO_HOST", "localhost")),
    "mqtt_port": _env_int("MQTT_PORT", _env_int("MOSQUITTO_PORT", 1884)),
    # Your docker-compose gateway bridge topic template
    "uplink_topic": "eu868/gateway/{gateway_id}/event/up",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)


# ─── LORAWAN CRYPTO ───────────────────────────────────────────────────────────

def aes128_encrypt(key: bytes, data: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    enc = cipher.encryptor()
    return enc.update(data) + enc.finalize()


def encrypt_frm_payload(app_skey: bytes, dev_addr: bytes, fcnt: int, payload: bytes) -> bytes:
    """AES-128 CTR encryption of FRMPayload (LoRaWAN spec section 4.3.3)"""
    encrypted = bytearray()
    k = math.ceil(len(payload) / 16)
    for i in range(1, k + 1):
        # A_i block
        a_i = (
            b'\x01'           # direction=0 uplink
            + b'\x00\x00\x00\x00'
            + b'\x00'         # direction
            + dev_addr
            + struct.pack('<I', fcnt)
            + b'\x00'
            + bytes([i])
        )
        s_i = aes128_encrypt(app_skey, a_i)
        encrypted += s_i
    return bytes(a ^ b for a, b in zip(payload, encrypted[:len(payload)]))


def compute_mic(nwk_skey: bytes, dev_addr: bytes, fcnt: int, phy_without_mic: bytes) -> bytes:
    """
    Compute LoRaWAN MIC using AES-128 CMAC (LoRaWAN spec section 4.4).
    B_0 block + full PHY payload (without MIC), then CMAC truncated to 4 bytes.
    """
    b0 = (
        b'\x49'
        + b'\x00\x00\x00\x00'
        + b'\x00'             # direction uplink
        + dev_addr
        + struct.pack('<I', fcnt)
        + b'\x00'
        + bytes([len(phy_without_mic)])
    )
    msg = b0 + phy_without_mic

    # AES-CMAC implementation (RFC 4493)
    def _xor(a, b): return bytes(x ^ y for x, y in zip(a, b))
    def _shift_left(b):
        result = bytearray(16)
        for i in range(15):
            result[i] = ((b[i] << 1) | (b[i+1] >> 7)) & 0xFF
        result[15] = (b[15] << 1) & 0xFF
        return bytes(result)

    const_zero = b'\x00' * 16
    const_rb   = b'\x00' * 15 + b'\x87'

    # Generate subkeys
    l = aes128_encrypt(nwk_skey, const_zero)
    if l[0] & 0x80:
        k1 = _xor(_shift_left(l), const_rb)
    else:
        k1 = _shift_left(l)
    if k1[0] & 0x80:
        k2 = _xor(_shift_left(k1), const_rb)
    else:
        k2 = _shift_left(k1)

    # Pad and process blocks
    n = math.ceil(len(msg) / 16)
    if n == 0:
        n = 1
        flag = False
    else:
        flag = (len(msg) % 16 == 0)

    blocks = [msg[i*16:(i+1)*16] for i in range(n)]
    if flag:
        blocks[-1] = _xor(blocks[-1], k1)
    else:
        last = blocks[-1] + b'\x80' + b'\x00' * (15 - len(blocks[-1]))
        blocks[-1] = _xor(last, k2)

    x = const_zero
    for block in blocks:
        x = aes128_encrypt(nwk_skey, _xor(x, block))

    return x[:4]


def build_lorawan_phy(dev_addr_hex: str, nwk_skey_hex: str, app_skey_hex: str,
                       fcnt: int, payload: bytes) -> bytes:
    """
    Build a complete, MIC-valid LoRaWAN uplink PHYPayload.
    Returns raw bytes ready to be base64-encoded for the gateway bridge.
    """
    dev_addr  = bytes.fromhex(dev_addr_hex)[::-1]  # little-endian
    nwk_skey  = bytes.fromhex(nwk_skey_hex)
    app_skey  = bytes.fromhex(app_skey_hex)

    # Encrypt FRMPayload
    encrypted = encrypt_frm_payload(app_skey, dev_addr, fcnt, payload)

    # Build FHDR
    mhdr  = bytes([0x40])                      # Unconfirmed Data Up
    fctrl = bytes([0x00])
    fcnt_b = struct.pack('<H', fcnt & 0xFFFF)
    fhdr  = dev_addr + fctrl + fcnt_b          # no FOpts

    # Build PHY without MIC
    fport      = bytes([1])
    phy_no_mic = mhdr + fhdr + fport + encrypted

    # Compute and append MIC
    mic = compute_mic(nwk_skey, dev_addr, fcnt, phy_no_mic)
    return phy_no_mic + mic


# ─── DATA GENERATION ──────────────────────────────────────────────────────────

def _rng(global_seed: int, node_id: str) -> random.Random:
    mix = zlib.crc32(node_id.encode("utf-8")) & 0xFFFFFFFF
    return random.Random((global_seed ^ mix) & 0xFFFFFFFF)


def generate_reading(step: int, mode: str, rng: random.Random, interval_secs: int) -> dict:
    # Diurnal curve; step advances once per telemetry interval (default 300 s → 12 steps/hour).
    elapsed_h = (step * interval_secs) / 3600.0
    hour = elapsed_h % 24
    temp = round(22 + 8 * math.sin(math.pi * (hour - 6) / 12) + rng.uniform(-1, 1), 2)

    if mode == "NORMAL":
        return {"temperature": temp,
                "humidity":    round(rng.uniform(40, 65), 2),
                "leaf_wetness":round(rng.uniform(0, 2), 2),
                "rainfall":    round(rng.uniform(0, 1), 2)}
    elif mode == "BUILDUP":
        return {"temperature": temp,
                "humidity":    round(min(92, 65 + (step % 60) * 0.45 + rng.uniform(-1, 1)), 2),
                "leaf_wetness":round(min(10, (step % 60) * 0.15 + rng.uniform(0, 0.5)), 2),
                "rainfall":    round(rng.uniform(0, 2), 2)}
    else:  # RAINFALL
        return {"temperature": round(temp - rng.uniform(1, 3), 2),
                "humidity":    round(rng.uniform(88, 97), 2),
                "leaf_wetness":round(rng.uniform(8, 12), 2),
                "rainfall":    round(rng.uniform(8, 22), 2)}


def compute_risk(r: dict) -> str:
    h, t, lw, rain = r["humidity"], r["temperature"], r["leaf_wetness"], r["rainfall"]
    if h < 70 or t < 15 or t > 35:                       return "LOW"
    if h > 85 and 18 <= t <= 25 and lw > 8 and rain > 5: return "CRITICAL"
    if h > 85 and 18 <= t <= 25:                          return "HIGH"
    if 70 <= h <= 85 and 15 <= t <= 25:                   return "MODERATE"
    return "LOW"


# ─── MQTT GATEWAY BRIDGE PAYLOAD ──────────────────────────────────────────────

def build_gateway_message(phy_bytes: bytes, gateway_eui: str, rng: random.Random, fcnt: int) -> dict:
    """
    Build JSON for ``eu868/gateway/{id}/event/up`` (Protobuf JSON mapping).

    gw.proto ``UplinkRxInfo.crc_status`` defaults to ``NO_CRC`` (0) when omitted;
    ChirpStack NS discards simulator frames unless CRC is marked OK **and** timestamps
    / metadata look valid.
    """
    uplink_id = rng.randrange(0, 2**32)
    gw_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return {
        "phyPayload": base64.b64encode(phy_bytes).decode(),
        "txInfo": {
            "frequency": 868100000,
            "modulation": {
                "lora": {
                    "bandwidth":       125000,
                    "spreadingFactor": 7,
                    "codeRate":        "CR_4_5",
                }
            },
        },
        "rxInfo": {
            "gatewayId": gateway_eui,
            "uplinkId": uplink_id,
            "gwTime": gw_ts,
            "rssi":      rng.randint(-90, -60),
            "snr":       float(round(rng.uniform(5.0, 12.0), 1)),
            "context":   base64.b64encode(struct.pack('>II', uplink_id, fcnt & 0xFFFFFFFF)).decode(),
            "crcStatus": "CRC_OK",
            "metadata": {
                "region_common_name": "EU868",
                "region_config_id":    "eu868",
            },
        },
    }


# ─── MQTT CLIENT ──────────────────────────────────────────────────────────────

def make_mqtt_client(node_id: str):
    connected = [False]

    def on_connect(client, userdata, flags, rc, props=None):
        if rc == 0:
            connected[0] = True
            log.info(f"[{node_id}] ✓ Connected to MQTT broker")
        else:
            log.error(f"[{node_id}] ✗ MQTT connect failed rc={rc}")

    client = mqtt.Client(
        client_id=f"sim-{node_id}",
        userdata=node_id,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    client.on_connect = on_connect

    while True:
        try:
            client.connect(CONFIG["mqtt_host"], CONFIG["mqtt_port"], keepalive=60)
            client.loop_start()
            time.sleep(1)
            if connected[0]:
                break
        except Exception as e:
            log.error(f"[{node_id}] Cannot connect: {e}. Retrying in 3s...")
            time.sleep(3)

    return client


# ─── MAIN LOOP ────────────────────────────────────────────────────────────────

def run_simulator(node_id, zone, dev_eui, dev_addr,
                  nwk_skey, app_skey, gateway_eui, mode, interval,
                  rng_seed):

    rng = _rng(rng_seed, node_id)
    log.info(f"Starting {node_id} | zone={zone} | devAddr={dev_addr} | mode={mode} | seed={rng_seed}")
    client = make_mqtt_client(node_id)
    topic  = CONFIG["uplink_topic"].format(gateway_id=gateway_eui)
    step   = 0

    try:
        while True:
            if zone == "zone2":
                current_mode = ["NORMAL", "BUILDUP", "RAINFALL"][(step // 20) % 3]
            else:
                current_mode = mode

            reading  = generate_reading(step, current_mode, rng, interval)
            risk     = compute_risk(reading)

            # Build signed LoRaWAN frame (Binary format: Temp(h), Hum(B), Leaf(B), Rain(H))
            payload = struct.pack(
                ">hBBH",
                int(reading["temperature"] * 100),
                int(reading["humidity"]),
                int(reading["leaf_wetness"]),
                int(reading["rainfall"] * 10)
            )
            phy      = build_lorawan_phy(dev_addr, nwk_skey, app_skey, step, payload)
            msg      = build_gateway_message(phy, gateway_eui, rng, step)

            result   = client.publish(topic, json.dumps(msg), qos=1)
            status   = "✓" if result.rc == 0 else "✗"

            log.info(
                f"[{node_id}] #{step:04d} {current_mode:8s} | "
                f"T={reading['temperature']:5.1f}°C "
                f"H={reading['humidity']:5.1f}% "
                f"LW={reading['leaf_wetness']:4.1f}h "
                f"R={reading['rainfall']:4.1f}mm | "
                f"risk={risk:8s} | {status}"
            )

            step += 1
            time.sleep(interval)

    except KeyboardInterrupt:
        log.info(f"[{node_id}] Stopped.")
    finally:
        client.loop_stop()
        client.disconnect()


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LoRaWAN ABP Node Simulator")
    parser.add_argument("--node-id",     required=True)
    parser.add_argument("--zone",        required=True, choices=["zone1","zone2"])
    parser.add_argument("--dev-eui",     required=True, help="16 hex chars")
    parser.add_argument("--dev-addr",    required=True, help="8 hex chars e.g. 00000001")
    parser.add_argument("--nwk-skey",    default="00000000000000000000000000000001")
    parser.add_argument("--app-skey",    default="00000000000000000000000000000001")
    parser.add_argument("--gateway-eui", required=True, help="e.g. aa00000000000001")
    parser.add_argument("--mode",        default="NORMAL",
                        choices=["NORMAL","BUILDUP","RAINFALL"])
    parser.add_argument("--interval",    type=int, default=300,
                        help="Seconds between telemetry (assignment: 300 = 5 minutes)")
    parser.add_argument("--seed", type=int, default=453,
                        help="Deterministic RNG base (per-node mix applied)")
    args = parser.parse_args()

    run_simulator(
        node_id=args.node_id,
        zone=args.zone,
        dev_eui=args.dev_eui,
        dev_addr=args.dev_addr,
        nwk_skey=args.nwk_skey,
        app_skey=args.app_skey,
        gateway_eui=args.gateway_eui,
        mode=args.mode,
        interval=args.interval,
        rng_seed=args.seed,
    )