import subprocess
import threading
import re
import time
from datetime import datetime
import os

# -------------------- File to save coordinates --------------------
TOUCH_LOG_FILE = r"D:\\Docker Containerization\\touch_coordinates.txt"

# -------------------- Get Touch Range --------------------
def get_touch_range():
    output = subprocess.check_output(['adb', 'shell', 'getevent', '-p'], universal_newlines=True)
    x_range = y_range = None
    for line in output.splitlines():
        if 'ABS_MT_POSITION_X' in line or '0035' in line:
            x_range = list(map(int, re.findall(r'min (\d+), max (\d+)', line)[0]))
        elif 'ABS_MT_POSITION_Y' in line or '0036' in line:
            y_range = list(map(int, re.findall(r'min (\d+), max (\d+)', line)[0]))
    if not x_range or not y_range:
        raise Exception("ERROR: Touch range not found.")
    return x_range, y_range

# -------------------- Get Screen Resolution --------------------
def get_screen_resolution():
    output = subprocess.check_output(['adb', 'shell', 'wm', 'size'], universal_newlines=True)
    match = re.search(r'Physical size: (\d+)x(\d+)', output)
    if not match:
        raise Exception("ERROR: Screen resolution not found.")
    return int(match.group(1)), int(match.group(2))

# -------------------- Mapping Raw to Pixel --------------------
def map_raw_to_pixel(raw_x, raw_y, x_range, y_range, screen_width, screen_height):
    min_x, max_x = x_range
    min_y, max_y = y_range
    pixel_x = int((raw_x - min_x) / (max_x - min_x) * screen_width)
    pixel_y = int((raw_y - min_y) / (max_y - min_y) * screen_height)
    return pixel_x, pixel_y

# -------------------- Save Touch to File --------------------
def save_touch_to_file(x, y):
    timestamp = datetime.now().strftime('%H:%M:%S')
    with open(TOUCH_LOG_FILE, 'w') as f:
        f.write(f"{x},{y},{timestamp}")

# -------------------- ADB Touch Listener --------------------
def adb_touch_listener(x_range, y_range, screen_width, screen_height):
    print("[INFO] Listening for real-time touches... (Press Ctrl+C to stop)")
    process = subprocess.Popen(['adb', 'shell', 'getevent', '-lt'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    x = y = None
    try:
        for line in process.stdout:
            match_named_x = re.search(r'ABS_MT_POSITION_X\s+([0-9a-fA-F]+)', line)
            match_named_y = re.search(r'ABS_MT_POSITION_Y\s+([0-9a-fA-F]+)', line)
            match_raw_x = re.search(r'0035\s+([0-9a-fA-F]+)', line)
            match_raw_y = re.search(r'0036\s+([0-9a-fA-F]+)', line)

            if match_named_x:
                x = int(match_named_x.group(1), 16)
            elif match_raw_x:
                x = int(match_raw_x.group(1), 16)

            if match_named_y:
                y = int(match_named_y.group(1), 16)
            elif match_raw_y:
                y = int(match_raw_y.group(1), 16)

            if x is not None and y is not None:
                pixel_x, pixel_y = map_raw_to_pixel(x, y, x_range, y_range, screen_width, screen_height)
                save_touch_to_file(pixel_x, pixel_y)
                print(f"[TOUCH] Raw: ({x},{y}) => Pixel: ({pixel_x},{pixel_y})")
                x = y = None
    except KeyboardInterrupt:
        print("[INFO] Touch listener stopped by user.")
    finally:
        process.terminate()

# -------------------- File to trigger exit --------------------
STOP_SIGNAL_FILE = r"D:\\Docker Containerization\\stop_touch_logger.txt"

def start_touch_logger():
    x_range, y_range = get_touch_range()
    screen_width, screen_height = get_screen_resolution()

    print(f"[INFO] Touch Ranges - X: {x_range}, Y: {y_range}")
    print(f"[INFO] Screen Resolution: {screen_width} x {screen_height}\n")

    adb_thread = threading.Thread(target=adb_touch_listener, args=(x_range, y_range, screen_width, screen_height))
    adb_thread.daemon = True
    adb_thread.start()

    try:
        while True:
            if os.path.exists(STOP_SIGNAL_FILE):
                print("[INFO] Stop signal detected. Exiting...")
                os.remove(STOP_SIGNAL_FILE)  # Optional: clean up
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("[INFO] Program exited by user.")

# -------------------- Entry Point --------------------
if __name__ == "__main__":
    start_touch_logger()
