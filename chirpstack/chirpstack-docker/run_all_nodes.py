import subprocess, json, os, sys, time, signal, logging
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv

    load_dotenv(_script_dir / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

CONFIG = {
    "devices_file":      "config/devices.json",
    "simulator_script":  "node_simulator.py",
    "tb_sidecar_script": "thingsboard_tb_sidecar.py",
    "log_dir":           "logs",
    "gateway_eui_z1":    "aa00000000000001",
    "gateway_eui_z2":    "aa00000000000002",
    "nwk_skey":          "00000000000000000000000000000001",
    "app_skey":          "00000000000000000000000000000001",
    "interval":          int(os.environ.get("SIM_TELEMETRY_INTERVAL", "300")),
    "rng_seed":          int(os.environ.get("SIM_RNG_SEED", "453")),
    "thingsboard_host":  os.environ.get("THINGSBOARD_MQTT_HOST", "localhost"),
    "thingsboard_port":  int(os.environ.get("THINGSBOARD_MQTT_PORT", "11883")),
}


def tb_token_ok(tok):
    return bool(tok and not str(tok).startswith("REPLACE"))


def tb_sidecars_enabled():
    flag = os.environ.get("ENABLE_TB_SIDECARS", "1").strip().lower()
    return flag in ("1", "true", "yes")


def zone_tag(zone_slug):
    return "Zone_1" if zone_slug == "zone1" else "Zone_2"


def main():
    script_dir = str(_script_dir)
    os.chdir(script_dir)

    os.makedirs(CONFIG["log_dir"], exist_ok=True)
    with open(CONFIG["devices_file"], encoding="utf-8") as f:
        devices = json.load(f)

    zone1_fallback = devices.get("_zone1_mode_default", "NORMAL")
    node_configs = (
        [(d, "zone1", CONFIG["gateway_eui_z1"]) for d in devices["Zone1"]] +
        [(d, "zone2", CONFIG["gateway_eui_z2"]) for d in devices["Zone2"]]
    )

    processes = []
    for device, zone, gw_eui in node_configs:
        log_path = os.path.join(CONFIG["log_dir"], f"{device['id']}.log")
        log_file = open(log_path, "w", encoding="utf-8")

        node_mode = device.get("mode", zone1_fallback) if zone == "zone1" else "NORMAL"
        cmd = [
            sys.executable, CONFIG["simulator_script"],
            "--node-id",     device["id"],
            "--zone",        zone,
            "--dev-eui",     device["deveui"],
            "--dev-addr",    device["devaddr"],
            "--nwk-skey",    device.get("nwk_skey", CONFIG["nwk_skey"]),
            "--app-skey",    device.get("app_skey", CONFIG["app_skey"]),
            "--gateway-eui", gw_eui,
            "--interval",    str(CONFIG["interval"]),
            "--seed",        str(CONFIG["rng_seed"]),
        ]
        if zone == "zone1":
            cmd += ["--mode", node_mode]

        proc = subprocess.Popen(cmd, stdout=log_file, stderr=log_file, cwd=script_dir)
        processes.append(("lorawan", proc, device["id"], log_file))
        logging.info("  [ok] %s LoRa simulator started (PID %s)", device["id"], proc.pid)

        tok = device.get("thingsboard_access_token", "")
        if tb_sidecars_enabled() and tb_token_ok(tok):
            tb_log_path = os.path.join(CONFIG["log_dir"], f"{device['id']}_tb_sidecar.log")
            tb_log = open(tb_log_path, "w", encoding="utf-8")
            tb_cmd = [
                sys.executable,
                CONFIG["tb_sidecar_script"],
                "--mqtt-host", CONFIG["thingsboard_host"],
                "--mqtt-port", str(CONFIG["thingsboard_port"]),
                "--access-token", tok,
                "--device-label", device["id"],
                "--zone-tag", zone_tag(zone),
            ]
            tb_proc = subprocess.Popen(tb_cmd, stdout=tb_log, stderr=tb_log, cwd=script_dir)
            processes.append(("tb", tb_proc, device["id"] + "_tb", tb_log))
            logging.info("  [ok] %s ThingsBoard OTA sidecar started (PID %s)", device["id"], tb_proc.pid)

        elif zone == "zone2" and tb_sidecars_enabled() and not tb_token_ok(tok):
            logging.warning(
                "  %s has placeholder TB token — set thingsboard_access_token to enable OTA sidecar.",
                device["id"],
            )

        time.sleep(0.3)

    logging.info("All nodes running. Ctrl+C to stop.")

    def shutdown(sig, frame):
        for _, proc, _, lf in processes:
            proc.terminate()
            lf.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    while True:
        time.sleep(30)
        lorawan = [p for k, p, _, _ in processes if k == "lorawan"]
        alive = sum(1 for p in lorawan if p.poll() is None)
        logging.info("Heartbeat: %s/%s LoRa simulators alive", alive, len(lorawan))


if __name__ == "__main__":
    main()
