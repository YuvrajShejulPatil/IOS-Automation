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

# ================== GET TOUCH RANGE ==================

def get_touch_range():
    output = subprocess.check_output(
        ["adb", "shell", "getevent", "-p"],
        universal_newlines=True
    )

    x_range = None
    y_range = None

    for line in output.splitlines():
        if "ABS_MT_POSITION_X" in line or "0035" in line:
            match = re.search(r"min\s+(\d+),\s+max\s+(\d+)", line)
            if match:
                x_range = [int(match.group(1)), int(match.group(2))]

        if "ABS_MT_POSITION_Y" in line or "0036" in line:
            match = re.search(r"min\s+(\d+),\s+max\s+(\d+)", line)
            if match:
                y_range = [int(match.group(1)), int(match.group(2))]

    if not x_range or not y_range:
        raise RuntimeError("Touch range not detected")

    return x_range, y_range


# ================== GET SCREEN RESOLUTION ==================

def get_screen_resolution():
    output = subprocess.check_output(
        ["adb", "shell", "wm", "size"],
        universal_newlines=True
    )
    match = re.search(r"Physical size:\s*(\d+)x(\d+)", output)
    if not match:
        raise RuntimeError("Screen resolution not detected")

    return int(match.group(1)), int(match.group(2))


# ================== MAP RAW TO PIXEL ==================

def map_raw_to_pixel(raw_x, raw_y, x_range, y_range, width, height):
    min_x, max_x = x_range
    min_y, max_y = y_range

    pixel_x = int((raw_x - min_x) / (max_x - min_x) * (width - 1))
    pixel_y = int((raw_y - min_y) / (max_y - min_y) * (height - 1))

    return pixel_x, pixel_y


# ================== START APPIUM (OPTIONAL) ==================

def start_appium_driver():
    print("[INFO] Starting Appium session...")
    driver = webdriver.Remote(
        "http://localhost:4723/wd/hub",
        desired_capabilities=capabilities
    )
    print("[INFO] Appium session started")
    return driver


# ================== ADB TOUCH LISTENER ==================

def adb_touch_listener(x_range, y_range, width, height, stop_event):
    print("[INFO] Listening for touches on /dev/input/event5...")
    print("[INFO] Touch the screen NOW")

    cmd = (
        "adb shell sh -c "
        "\"getevent -lt /dev/input/event5\""
    )

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        shell=True
    )

    current_slot = 0
    raw_x = None
    raw_y = None

    try:
        for line in iter(process.stdout.readline, ""):
            if stop_event.is_set():
                break

            # DEBUG (uncomment if needed)
            # print("[RAW]", line.strip())

            if "ABS_MT_SLOT" in line:
                current_slot = int(line.strip().split()[-1], 16)
                continue

            if current_slot != 0:
                continue

            if "ABS_MT_POSITION_X" in line:
                raw_x = int(line.strip().split()[-1], 16)

            if "ABS_MT_POSITION_Y" in line:
                raw_y = int(line.strip().split()[-1], 16)

            if raw_x is not None and raw_y is not None:
                px, py = map_raw_to_pixel(
                    raw_x, raw_y,
                    x_range, y_range,
                    width, height
                )

                print(f"[TOUCH] Raw({raw_x},{raw_y}) → Pixel({px},{py})")

                raw_x = None
                raw_y = None

    finally:
        process.terminate()
        print("[INFO] Touch listener stopped")




# ================== MAIN ==================

if __name__ == "__main__":

    # Uncomment if you want Appium session
    # driver = start_appium_driver()

    x_range, y_range = get_touch_range()
    screen_width, screen_height = get_screen_resolution()

    print(f"[INFO] X Range: {x_range}")
    print(f"[INFO] Y Range: {y_range}")
    print(f"[INFO] Screen: {screen_width} x {screen_height}")

    stop_event = threading.Event()

    adb_thread = threading.Thread(
        target=adb_touch_listener,
        args=(x_range, y_range, screen_width, screen_height, stop_event),
        daemon=True
    )
    adb_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Exiting...")
        stop_event.set()
        adb_thread.join()
