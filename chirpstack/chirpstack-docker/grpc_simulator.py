import time
import random
import base64
import struct
import grpc
from datetime import datetime
from chirpstack_api import api

# --- Configuration ---
# gRPC API is usually multiplexed on the same port as the UI (8080)
GRPC_SERVER = "localhost:8080"
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjaGlycHN0YWNrIiwiaXNzIjoiY2hpcnBzdGFjayIsInN1YiI6Ijk2MjQzOGM1LWUxMjUtNDA2ZS1iYjg0LWQxZDVkM2UwNjEyMiIsInR5cCI6ImtleSJ9.K70VP7SJY6S2d-4vDZbW0OE-vnVx6_0BOw-aYN4Hxy4"

# Application IDs
APPS = [
    "e8e29522-e292-4845-af49-13ff5d4315e4", # Zone 1
    "dd205732-b347-472a-8e94-7a9adbbb5008"  # Zone 2
]

def get_encoded_data(dev_eui, ticks):
    temp = random.uniform(22, 28)
    hum = random.uniform(45, 55)
    leaf = random.randint(0, 10)
    rain = 0.0
    
    if dev_eui == "0000000000000001":
        hum = min(95, 60 + (ticks * 2))
        leaf = min(255, ticks * 20)
    elif dev_eui == "0000000000000006":
        if ticks % 5 == 0:
            rain = 15.5
            hum = 90

    # Binary packing (6 bytes)
    return struct.pack(">hBBH", int(temp * 100), int(hum), leaf, int(rain * 10))

print(f"Connecting to ChirpStack gRPC API at {GRPC_SERVER}...")

# Setup gRPC channel
channel = grpc.insecure_channel(GRPC_SERVER)
client = api.DeviceServiceStub(channel)
auth_token = [("authorization", f"Bearer {API_KEY}")]

# 1. Fetch all devices
all_devices = []
try:
    for app_id in APPS:
        req = api.ListDevicesRequest()
        req.application_id = app_id
        req.limit = 50
        resp = client.List(req, metadata=auth_token)
        for dev in resp.result:
            all_devices.append(dev.dev_eui)
    print(f"Found {len(all_devices)} devices.")
except Exception as e:
    print(f"Failed to fetch devices: {e}")
    exit(1)

ticks = 0
print("Starting gRPC Simulation...")

try:
    while True:
        ticks += 1
        for dev_eui in all_devices:
            payload = get_encoded_data(dev_eui, ticks)
            
            # Prepare Simulation Request
            sim_req = api.SimulateUplinkRequest()
            sim_req.dev_eui = dev_eui
            sim_req.f_port = 1
            sim_req.data = payload
            
            try:
                client.SimulateUplink(sim_req, metadata=auth_token)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Injected: {dev_eui}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed {dev_eui}: {e}")
        
        print("-" * 50)
        time.sleep(300) # 5 minutes
except KeyboardInterrupt:
    print("\nStopped.")
