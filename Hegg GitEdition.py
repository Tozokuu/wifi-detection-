import time
import os
import re
import asyncio
import subprocess
import discord
from concurrent.futures import ThreadPoolExecutor

# ------------------------
# Discord Config
# ------------------------
BOT_TOKEN = "000000000000000000000000000000000000000000000000000"
CHANNEL_ID = 0000000000000000000

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# ------------------------
# Friend & Network Config
# ------------------------
FRIENDS = {
    "8ri5us": "08:0d:02:0f:04:0e",
    "73n5n4e": "00:28:00:05:00:00",
}

SUBNET = "00.0.0."
SLEEP_TIME = 1              # faster scans
ARRIVAL_THRESHOLD = 1
LEAVE_THRESHOLD = 1
MAX_THREADS = 200           # faster sweep
ARP_REFRESH_INTERVAL = 5    # only sweep every 5 scans

LOG_TO_FILE = True
LOG_FILE = r"C:\Users\Owner\Desktop\Wifidection\friend_log.txt"

# ------------------------
# Network Functions
# ------------------------
def ping_ip(ip):
    subprocess.run(
        ["ping", ip, "-n", "1", "-w", "50"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def refresh_arp_parallel():
    ips = [f"{SUBNET}{i}" for i in range(1, 255)]

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        executor.map(ping_ip, ips)

def scan_network():
    try:
        return subprocess.check_output("arp -a", shell=True).decode().lower()
    except:
        return ""

def extract_macs(arp_output):
    return {
        m.replace('-', ':')
        for m in re.findall(r'(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}', arp_output)
    }

def log_event(friend_name, event):
    if LOG_TO_FILE:
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

            with open(LOG_FILE, "a") as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp} - {friend_name} {event}\n")

        except Exception as e:
            print("Log error:", e)

# ------------------------
# Async Monitor Function
# ------------------------
async def monitor_friends():

    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("ERROR: Channel not found")
        return

    friend_states = {name: False for name in FRIENDS}
    detection_counts = {name: 0 for name in FRIENDS}
    miss_counts = {name: 0 for name in FRIENDS}

    loop = asyncio.get_running_loop()
    scan_counter = 0

    while True:

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] scanning...")

        # Refresh ARP occasionally
        if scan_counter % ARP_REFRESH_INTERVAL == 0:
            await loop.run_in_executor(None, refresh_arp_parallel)

        scan_counter += 1

        arp_output = scan_network()
        macs = extract_macs(arp_output)

        for name, mac in FRIENDS.items():

            detected = mac.lower() in macs

            if detected:
                detection_counts[name] += 1
                miss_counts[name] = 0
            else:
                miss_counts[name] += 1
                detection_counts[name] = 0

            # Arrival
            if detection_counts[name] >= ARRIVAL_THRESHOLD and not friend_states[name]:

                message = f"🟢 {name} connected to WiFi"
                print(f"[{timestamp}] {message}")

                await channel.send(message)
                log_event(name, "CONNECTED")

                friend_states[name] = True

            # Departure
            elif miss_counts[name] >= LEAVE_THRESHOLD and friend_states[name]:

                message = f"🔴 {name} disconnected from WiFi"
                print(f"[{timestamp}] {message}")

                await channel.send(message)
                log_event(name, "DISCONNECTED")

                friend_states[name] = False

        await asyncio.sleep(SLEEP_TIME)

# ------------------------
# Discord Event
# ------------------------
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    asyncio.create_task(monitor_friends())

# ------------------------
# Run Bot
# ------------------------
if __name__ == "__main__":

    try:
        client.run(BOT_TOKEN)

    except Exception as e:
        print("ERROR:", e)
        input("Press Enter to exit...")