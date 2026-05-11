import time
import json
import random
import base64
import struct
import requests
from datetime import datetime

# --- Configuration ---
API_URL = "http://localhost:8090/api"
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjaGlycHN0YWNrIiwiaXNzIjoiY2hpcnBzdGFjayIsInN1YiI6Ijk2MjQzOGM1LWUxMjUtNDA2ZS1iYjg0LWQxZDVkM2UwNjEyMiIsInR5cCI6ImtleSJ9.K70VP7SJY6S2d-4vDZbW0OE-vnVx6_0BOw-aYN4Hxy4"

# Application IDs from your database
APPS = [
    "e8e29522-e292-4845-af49-13ff5d4315e4", # Zone 1
    "dd205732-b347-472a-8e94-7a9adbbb5008"  # Zone 2
]

def get_devices(app_id):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    url = f"{API_URL}/devices?applicationId={app_id}&limit=50"
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return [d["devEui"] for d in resp.json()["result"]]
    except Exception as e:
        print(f"Error fetching devices for {app_id}: {e}")
        return []

def get_encoded_data(dev_eui, ticks):
    # Base data
    temp = random.uniform(22, 28)
    hum = random.uniform(45, 55)
    leaf = random.randint(0, 10)
    rain = 0.0
    
    # Disease pattern (Node 1)
    if dev_eui == "0000000000000001":
        hum = min(95, 60 + (ticks * 2))
        leaf = min(255, ticks * 20)
    # Rain pattern (Node 6)
    elif dev_eui == "0000000000000006":
        if ticks % 5 == 0:
            rain = 15.5
            hum = 90

    # Binary packing: Temp(h), Hum(B), Leaf(B), Rain(H)
    binary = struct.pack(">hBBH", int(temp * 100), int(hum), int(leaf), int(rain * 10))
    return base64.b64encode(binary).decode('utf-8')

def simulate_uplink(dev_eui, payload_b64):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    url = f"{API_URL}/devices/{dev_eui}/uplink" 
    data = {
        "fPort": 1,
        "data": payload_b64
    }
    try:
        resp = requests.post(url, json=data, headers=headers)
        if resp.status_code == 200:
            return True
        
        # If /uplink fails, try /simulate-uplink
        url_alt = f"{API_URL}/devices/{dev_eui}/simulate-uplink"
        resp_alt = requests.post(url_alt, json=data, headers=headers)
        if resp_alt.status_code == 200:
            return True
        
        # Print the error so we can fix it
        print(f"[{dev_eui}] FAILED. Status: {resp_alt.status_code}, Error: {resp_alt.text}")
        return False
    except Exception as e:
        print(f"[{dev_eui}] Connection Error: {e}")
        return False

print("Starting Definitive Simulation...")

# 1. Dynamically find all devices
ALL_DEVICES = []
for app in APPS:
    devs = get_devices(app)
    ALL_DEVICES.extend(devs)
    print(f"Found {len(devs)} devices in Application {app}")

if not ALL_DEVICES:
    print("No devices found. Check your API Key and Application IDs.")
    exit(1)

ticks = 0
try:
    while True:
        ticks += 1
        for dev_eui in ALL_DEVICES:
            payload = get_encoded_data(dev_eui, ticks)
            if simulate_uplink(dev_eui, payload):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] OK: {dev_eui}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] FAILED: {dev_eui}")
        
        print("-" * 50)
        time.sleep(300) # 5 minutes
except KeyboardInterrupt:
    print("\nStopped.")
