from appium import webdriver
from appium import webdriver as appium_webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.common.touch_action import TouchAction

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException
)

from skimage.metrics import structural_similarity as ssim
from skimage.morphology import skeletonize as ski_skeletonize

from appium.options.ios import XCUITestOptions

from PIL import Image

import cv2
import numpy as np
import base64
import traceback
import os
import sys
import json
import re
import subprocess
import threading
import requests
import hashlib
import time
import platform
from time import sleep
from datetime import datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET
import pytesseract

# ---------------------------------------------------------
# Tesseract
# ---------------------------------------------------------
if platform.system() == "Darwin":
    pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
else:
    pytesseract.pytesseract.tesseract_cmd = "/usr/local/bin/tesseract"

# ---------------------------------------------------------
# Project Paths
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent

APP_DIR = PROJECT_ROOT / "Appium"

TEMP_SCREENSHOT_DIR = APP_DIR / "Temp Screenshot"
ADB_LOG_DIR = APP_DIR / "ADB Logs"
CAPABILITY_DIR = APP_DIR / "Capabilities"
SCREENSHOT_DIR = APP_DIR / "Screenshots"
WATCHER_DIR = APP_DIR / "Watcher"
IMAGE_DIR = APP_DIR / "Image File Path"

# ---------------------------------------------------------
# Files
# ---------------------------------------------------------
temp_path = TEMP_SCREENSHOT_DIR / "temp_img.png"
Ref_Img_Path = TEMP_SCREENSHOT_DIR / "ref_img.png"

Image_File_Path = IMAGE_DIR / "Image_Path.txt"

Cap_path = CAPABILITY_DIR / "Capabilities.json"

temp_logfile = "temp_logcat.log"
temp_log_fullpath = ADB_LOG_DIR / temp_logfile

file_to_watch = WATCHER_DIR / "Watcher.txt"

# ---------------------------------------------------------
# Global Variables
# ---------------------------------------------------------
Common_Ref_Img_Path = None
ENABLE_TEXT_CROSSCHECK = True

log_process = None
driver = None
device_id = None

x_str = None
y_str = None

app_evpv = 0        # 0 = PV, 1 = EV
knob = 0

Trip_Count = None
Trips = None

Capability_path = str(Cap_path)
Screenshot_path = str(SCREENSHOT_DIR)
temp_logfilepath = str(ADB_LOG_DIR)

print(Capability_path)
print(file_to_watch)

if os.path.exists(file_to_watch):
    os.remove(file_to_watch)


def Wait_Input_Text(time):
    seconds, timeout = time.split(",")
    seconds = int(seconds)
    sleep(seconds)
    return "Ok#Wait over"


def start_server(input="str"):
    # Launch Appium in a new Terminal window on macOS
    subprocess.Popen([
        "osascript",
        "-e",
        'tell application "Terminal" to do script "appium"'
    ])
    return "Appium server started"

#######################################################
# Initialization Functions (macOS)
#######################################################
def failcaseinit(input):
    global driver, device_id, bundle_id

    input = str(input)

    with driver_lock:
        print("[INIT] XCUITest recovery started...")

        # Kill old driver
        try:
            if driver:
                driver.quit()
                print("[INIT] Old driver quit")
        except Exception as e:
            print(f"[INIT] Driver quit error (ignored): {e}")

        # Cooldown
        time.sleep(2.5)

        # Load capabilities
        with open(Capability_path, "r") as file:
            caps = json.load(file)

        print("[INIT] Restarting driver...")

        # Start new Appium session
        driver = webdriver.Remote("http://localhost:4723", caps)

        # Update globals
        device_id = caps.get("udid")
        bundle_id = caps.get("bundleId")   # iOS app identifier

        # Stabilization delay
        time.sleep(1.5)

        print("[INIT] Driver reinitialized successfully")

    return "PASS"

def is_uia2_socket_error(e):
    msg = str(e).lower()
    return (
        "socket hang up" in msg or
        "could not proxy command" in msg or
        "instrumentation process is not running" in msg or
        "invalid session id" in msg or
        "session is either terminated" in msg
    )


def recover_uia2_session():
    try:
        print("Recovering UIAutomator2 session...")

        # Optional: Restart UIAutomator2 if needed
        # subprocess.run(["adb", "shell", "pkill", "-f", "uiautomator"])

        failcaseinit("Hello")

        print("UIA2 recovery successful")
        return True

    except Exception as e:
        print("Recovery failed:", e)
        return False


# def is_flag_secure():
#     # try:
#     #     output = subprocess.check_output(
#     #         ["adb", "shell", "dumpsys", "window"],
#     #         encoding="utf-8"
#     #     )

#     #     for line in output.splitlines():
#     #         if "mCurrentFocus" in line:
#     #             match = re.search(r'u0\s+([^\s}]+)', line)
#     #             if match:
#     #                 window = match.group(1)
#     #                 idx = output.find(window)
#     #                 block = output[idx:idx + 500]
#     #                 return "FLAG_SECURE" in block

#     #     return False

#     # except Exception:
#     #     return False


def is_driver_alive():
    try:
        return driver is not None and driver.session_id is not None
    except Exception:
        return False


driver_lock = threading.Lock()

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode())


def is_appium_running(input, host="127.0.0.1", port=4723):
    param1, param2 = input.split(",", 1)
    url = f"http://{host}:{port}/status"

    try:
        response = requests.get(url, timeout=0.5)
        if response.status_code == 200:
            print("Appium server is running.")
            return "True"
    except requests.exceptions.ConnectionError:
        print("Appium server is not running.")
        return "False"


def shutdown_driver():
    global driver
    try:
        if driver:
            driver.quit()
            driver = None
        return "PASS: Driver shutdown"
    except:
        return "WARN: Driver shutdown failed"
    
def ensure_app_in_foreground(bundle_id):
    try:
        driver.activate_app(bundle_id)
        print(f"App '{bundle_id}' is now in the foreground.")
        return "PASS"
    except Exception as e:
        print(f"Failed to bring app to foreground: {e}")
        return f"FAIL: {e}"

def Launch_App(bundle_id):
    driver.activate_app(bundle_id)
    return "PASS"

def is_app_installed(bundle_id):
    return driver.is_app_installed(bundle_id)

def is_app_installed(bundle_id):
    return driver.is_app_installed(bundle_id)

def bring_app_to_foreground(bundle_id):
    driver.activate_app(bundle_id)
    return "PASS"

def Restart_App(bundle_id):
    driver.terminate_app(bundle_id)
    time.sleep(1)
    driver.activate_app(bundle_id)
    return "PASS"

def kill_webdriveragent():
    try:
        subprocess.run(
            ["xcrun", "simctl", "terminate", "booted", "com.facebook.WebDriverAgentRunner.xctrunner"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        sleep(3)
        return "PASS: Killed WebDriverAgent"
    except Exception:
        return "WARN: kill_webdriveragent failed"
    

def restart_everything():
    shutdown_driver()
    kill_webdriveragent()
    return init_driver()

def just_init(input):
    global driver
    input = ""

    start_time = time.time()

    # Load capabilities
    with open(Capability_path, "r") as file:
        caps = json.load(file)

    print("[INIT] Restarting driver...")

    # Create XCUITest options
    options = XCUITestOptions().load_capabilities(caps)

    # Start Appium session
    driver = webdriver.Remote(
        "http://127.0.0.1:4723",
        options=options
    )

    end_time = time.time()

    execution_time = end_time - start_time
    print(f"[INIT] Execution Time: {execution_time:.3f} seconds")

    return "Initialised"


from appium.options.ios import XCUITestOptions

def fast_screenshot(output_path):
    driver.save_screenshot(output_path)
    return output_path

def capture_screenshot_new(output_path):
    png = driver.get_screenshot_as_png()
    with open(output_path, "wb") as f:
        f.write(png)
    return output_path

def file_watcher(filepath, check_interval=1):
    global driver, stop_event

    print("[WATCHER] Started monitoring:", filepath)

    while not stop_event.is_set():

        if os.path.exists(filepath):
            print(f"[STOP TRIGGER] File detected: {filepath}")

            stop_event.set()

            try:
                with driver_lock:
                    if driver is not None:
                        driver.quit()
                        driver = None
                        print("[WATCHER] Driver quit successfully")

                os.remove(filepath)
                print("[WATCHER] Stop file removed")
                failcaseinit("Input")

            except Exception as e:
                print(f"[WATCHER ERROR]: {e}")

            break

        time.sleep(check_interval)

    print("[WATCHER] Thread exited")

def init_driver(variable_str="", timeout=10):
    global driver, device_id, stop_event, stop_thread_flag

    try:
        if driver is not None:
            try:
                driver.current_context
                return "PASS: Driver already initialized"
            except:
                try:
                    driver.quit()
                except:
                    pass
                driver = None

        with open(Capability_path, "r") as file:
            caps = json.load(file)

        print(caps)

        options = XCUITestOptions().load_capabilities(caps)

        driver = webdriver.Remote(
            "http://127.0.0.1:4723",
            options=options
        )

        safe_print("[INIT] Appium driver initialized")

        device_id = caps.get("udid")
        bundle_id = caps.get("bundleId")

        # Bring app to foreground
        driver.activate_app(bundle_id)

        stop_event = threading.Event()

        watcher_thread = threading.Thread(
            target=file_watcher,
            args=(file_to_watch,),
            daemon=True
        )
        watcher_thread.start()

        stop_thread_flag = False

        return "PASS: Driver initialized"

    except Exception as e:
        err = f"ERROR: Failed to initialize Appium driver: {str(e)}"
        safe_print(err)
        safe_print(traceback.format_exc())
        return err