import subprocess
import threading
import re
import time
import json
from datetime import datetime
from pathlib import Path
from appium import webdriver


# ================== PATH SETUP ==================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent  # adjust if needed

Cap_path = PROJECT_ROOT / "Appium" / "Capabilities" / "Capabilities.json"
Capability_path= str(Cap_path).replace("\\", "\\\\")
CAPABILITY_PATH = str(Capability_path)

# ================== LOAD APPIUM CAPABILITIES ==================

with open(CAPABILITY_PATH, "r") as file:
    capabilities = json.load(file)
print(CAPABILITY_PATH)
print("[INFO] Loaded Appium Capabilities")

# Start Appium Driver
def start_appium_driver():
    print("Launching app via Appium...")
    driver = webdriver.Remote("http://localhost:4723/wd/hub", capabilities)
    print("App launched via Appium\n")
    return driver

# Extract coordinates from getevent line
def extract_coordinates(line):
    match_x = re.search(r'0035\s+([0-9a-fA-F]+)', line)
    match_y = re.search(r'0036\s+([0-9a-fA-F]+)', line)
    x = int(match_x.group(1), 16) if match_x else None
    y = int(match_y.group(1), 16) if match_y else None
    return x, y

# Listen for ADB touch events
def adb_touch_listener():
    print("Listening for real-time touches... (Ctrl+C to stop)")
    process = subprocess.Popen(['adb', 'shell', 'getevent', '-lt'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    x, y = None, None
    last_log_time = time.time()
    try:
        for line in process.stdout:
            current_time = time.time()
            if current_time - last_log_time > 2:
                print("Still listening for touch events...")
                last_log_time = current_time

            if '0035' in line:
                x, _ = extract_coordinates(line)
            elif '0036' in line:
                _, y = extract_coordinates(line)

            if x is not None and y is not None:
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"[{timestamp}] Touch Detected -> X: {x}, Y: {y}")
                x, y = None, None
    except KeyboardInterrupt:
        print("\nTouch listener stopped by user.")
    finally:
        process.terminate()

# Main
if __name__ == "__main__":
    #driver = start_appium_driver()

    # Start ADB listener in background
    adb_thread = threading.Thread(target=adb_touch_listener)
    adb_thread.daemon = True
    adb_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program exited by user.")
    
