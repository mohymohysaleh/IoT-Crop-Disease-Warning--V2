import subprocess, json, os, sys, time, signal, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

CONFIG = {
    "devices_file":     "config/devices.json",
    "simulator_script": "node_simulator.py",
    "log_dir":          "logs",
    "gateway_eui_z1":   "aa00000000000001",
    "gateway_eui_z2":   "aa00000000000002",
    "nwk_skey":         "00000000000000000000000000000001",
    "app_skey":         "00000000000000000000000000000001",
    "interval":         30,
}

def main():
    os.makedirs(CONFIG["log_dir"], exist_ok=True)
    with open(CONFIG["devices_file"]) as f:
        devices = json.load(f)

    node_configs = (
        [(d, "zone1", CONFIG["gateway_eui_z1"]) for d in devices["Zone1"]] +
        [(d, "zone2", CONFIG["gateway_eui_z2"]) for d in devices["Zone2"]]
    )

    processes = []
    for device, zone, gw_eui in node_configs:
        log_file = open(os.path.join(CONFIG["log_dir"], f"{device['id']}.log"), "w")
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
        ]
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        processes.append((proc, device["id"], log_file))
        logging.info(f"  ✓ {device['id']} started (PID {proc.pid})")
        time.sleep(0.3)

    logging.info("All nodes running. Ctrl+C to stop.")

    def shutdown(sig, frame):
        for proc, _, lf in processes:
            proc.terminate(); lf.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    while True:
        time.sleep(30)
        alive = sum(1 for p,_,_ in processes if p.poll() is None)
        logging.info(f"Heartbeat: {alive}/{len(processes)} alive")

if __name__ == "__main__":
    main()