from appium import webdriver
from selenium.webdriver.common.by import By
import cv2
import numpy as np
import base64
import traceback, os, sys, json, re, subprocess, threading, requests
from datetime import datetime, timedelta
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.common.touch_action import TouchAction
from skimage.metrics import structural_similarity as ssim
import xml.etree.ElementTree as ET
from PIL import Image
from selenium.common.exceptions import WebDriverException
from pathlib import Path
import pytesseract
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
import hashlib
import time
from time import sleep
import traceback
import os


pytesseract.pytesseract.tesseract_cmd = r"C:\Users\yuvraj.s.MTPA332-L\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
# from datetime import datetime
# temp_path = "C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\temp_img.png"
# #temp_path = "D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\temp_img.png"
# Ref_Img_Path = "C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\ref_img.png"
# Image_File_Path = "C:\\MaxEye\\MEP00179\\Application\\Configuration_Files\\Appium\\Image FIle Path\\Image_Path.txt"
# Common_Ref_Img_Path = None


ENABLE_TEXT_CROSSCHECK = True
# Get the current script's directory
BASE_DIR = Path(__file__).resolve().parent

# Go up to project root if needed
PROJECT_ROOT = BASE_DIR.parent.parent  # adjust based on where your script is


# temp_path = "C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\temp_img.png"
temp_path = PROJECT_ROOT /  "Appium" / "Temp Screenshot" / "temp_img.png"
#temp_path = "D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\temp_img.png"
# Ref_Img_Path = "C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\ref_img.png"
Ref_Img_Path = PROJECT_ROOT /  "Appium" / "Temp Screenshot" / "ref_img.png"
# Image_File_Path = "C:\\MaxEye\\MEP00179\\Application\\Configuration_Files\\Appium\\Image FIle Path\\Image_Path.txt"
Image_File_Path = PROJECT_ROOT /  "Appium" / "Image FIle Path" / "Image_Path.txt"
Common_Ref_Img_Path = None


# Construct the full path dynamically
temp_log = PROJECT_ROOT /  "Appium" / "ADB Logs"
Cap_path =  PROJECT_ROOT /  "Appium" / "Capabilities" / "Capabilities.json"
ss_path= PROJECT_ROOT /  "Appium" / "Screenshots"
log_process = None
temp_logfile = "temp_logcat.log"  # Temporary log file before renaming
driver = None  # global variable to hold the Appium driver
device_id = None
x_str = None
y_str = None
app_evpv = 0 #0 PV 1 EV
knob = 0
Trip_Count = None
Trips = None
temp_logfilepath = str(temp_log).replace("\\", "\\\\")
Capability_path= str(Cap_path).replace("\\", "\\\\")
#Screenshot_path= str(ss_path).replace("\\", "\\\\")
Screenshot_path=ss_path

temp_log_fullpath = os.path.join(temp_logfilepath, temp_logfile)
print(Capability_path)

file_to_watch_t = PROJECT_ROOT /  "Appium" / "Watcher" / "Watcher.txt"
file_to_watch = str(file_to_watch_t).replace("\\", "\\\\")
print(file_to_watch)

if os.path.exists(file_to_watch):
    os.remove(file_to_watch)


def Wait_Input_Text(time):
    seconds,timeout=time.split(",")
    seconds=int(seconds)
    sleep(seconds)
    return "Ok#Wait over"

def start_server(input="str"):
    # Launch Appium in a new CMD window without blocking LabVIEW
    subprocess.Popen(["cmd.exe", "/c", "start cmd /k appium"], shell=True)
    return "Appium server started"

####################################################### Initialization function #############################################################
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

        # os.system("adb shell pkill -f uiautomator")
        # time.sleep(1.5)

        failcaseinit("Hello")

        print("UIA2 recovery successful")
        return True

    except Exception as e:
        print("Recovery failed:", e)
        return False


def is_flag_secure():
    try:
        output = subprocess.check_output(['adb', 'shell', 'dumpsys', 'window'], encoding='utf-8')
        for line in output.splitlines():
            if "mCurrentFocus" in line:
                match = re.search(r'u0\s+([^\s}]+)', line)
                if match:
                    window = match.group(1)
                    idx = output.find(window)
                    block = output[idx:idx + 500]
                    return "FLAG_SECURE" in block
        return False
    except:
        return False

def is_driver_alive():
    try:
        return driver is not None and driver.session_id is not None
    except:
        return False

driver_lock = threading.Lock()

def is_device_unlocked():
    try:
        result = subprocess.run(
            ["adb", "shell", "dumpsys", "window"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output = result.stdout

        # This condition works on most Android versions
        if "mDreamingLockscreen=true" in output or "mCurrentFocus=StatusBar" in output:
            print("Device is locked.")
            return False
        elif "mDreamingLockscreen=false" in output and "mCurrentFocus" in output:
            print("Device is unlocked.")
            return True
        else:
            print("Unable to determine lock state.")
            return False
    except Exception as e:
        print(f"Error checking lock state: {e}")
        return False
    
def is_app_in_foreground(package_name):
    """
    Check if the given package is currently in the foreground.
    Works with single or multiple devices (if device_id is set).
    """
    try:
        cmd = ["adb"]
        if device_id:  # only include -s if we know which device
            cmd += ["-s", device_id]
        cmd += ["shell", "dumpsys", "activity", "activities"]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output = result.stdout

        # Check for package in foreground indicators
        if ("mResumedActivity" in output or "ResumedActivity" in output or "mFocusedApp" in output) \
                and package_name in output:
            print(f"{package_name} is in the foreground.")
            return True
        else:
            print(f"{package_name} is NOT in the foreground.")
            return False

    except Exception as e:
        print(f"Error checking foreground app: {e}")
        return False



def Wakeup_Mobile(pin_code):
    try:
        # # Validate input
        # if not isinstance(pin_code, str):
        #     return f"Not ok: Expected pin_code as string, got {type(pin_code).__name__}"

        # # Wake up the phone
        # subprocess.run(["adb", "shell", "input", "keyevent", "224"], check=True)
        # sleep(1)

        # # Swipe up to unlock
        # subprocess.run(["adb", "shell", "input", "swipe", "300", "1000", "300", "500"], check=True)
        # sleep(1)

        # if is_device_unlocked():
        #     print('unlocked')
        # else:
        #     subprocess.run(["adb", "shell", "input", "text", pin_code], check=True)
        #     sleep(0.5)

        # # Press Enter
        # subprocess.run(["adb", "shell", "input", "keyevent", "66"], check=True)
        # sleep(2)

        return "Success"

    except subprocess.CalledProcessError as e:
        return f"ADB command failed: {e}"
    except Exception as e:
        return f"Unhandled error: {str(e)}\nTraceback:\n{traceback.format_exc()}"

def is_app_running(package_name):
    try:
        pid = subprocess.check_output(
            ["adb", "shell", "pidof", package_name],
            encoding="utf-8"
        ).strip()
        if pid:
            print(f"App '{package_name}' is running (PID: {pid}).")
            return True
        else:
            print(f"App '{package_name}' is not running.")
            return False
    except subprocess.CalledProcessError:
        print(f"App '{package_name}' is not running.")
        return False

def get_foreground_app():
    try:
        result = subprocess.check_output(
            ["adb", "-s", device_id, "shell", "dumpsys", "activity", "activities"],
            encoding="utf-8"
        )
        for line in result.splitlines():
            if "mResumedActivity" in line:
                return line.strip()
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error fetching foreground activity: {e}")
        return None

def bring_app_to_foreground(package_name):
    try:
        subprocess.run([
            "adb", "-s", device_id, "shell", "monkey", "-p", package_name,
            "-c", "android.intent.category.LAUNCHER", "1"
        ], check=True)
        print(f"{package_name} brought to foreground.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to bring {package_name} to foreground: {e}")

def Launch_App(package_name):
    try:
        subprocess.run([
            "adb", "-s", device_id, "shell", "monkey", "-p", package_name,
            "-c", "android.intent.category.LAUNCHER", "1"
        ], check=True)
        print(f"App '{package_name}' launched successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to launch app '{package_name}': {e}")

def ensure_app_in_foreground(package_name):
    if not is_app_running(package_name):
        print("App is not running. Cannot bring it to foreground.")
        Launch_App(package_name)
        return 

    fg_line = get_foreground_app()
    if fg_line:
        if package_name in fg_line:
            print("App is already in foreground.")
        else:
            print("App is running in background. Bringing it to foreground...")
            bring_app_to_foreground(package_name)
    else:
        print("Unable to determine the current foreground app.")

# === Safe print ===
def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode())

def is_appium_running(input,host='127.0.0.1', port=4723):
    param1, param2=input.split(",",1)
    url = f'http://{host}:{port}/status'
    try:
        response = requests.get(url, timeout=0.5)
        if response.status_code == 200:
            print("Appium server is running.")
            return "True"
    except requests.exceptions.ConnectionError:
        print("Appium server is not running.")
    return "False"


# 2. Shut down Appium driver
def shutdown_driver():
    global driver
    try:
        if driver:
            driver.quit()
        driver = None
        return "PASS: Driver shutdown"
    except:
        return "WARN: Driver shutdown failed"

# 3. Kill UiAutomator2 process on the Android device
def kill_uiautomator():
    try:
        subprocess.run(['adb', 'shell', 'am', 'force-stop', 'io.appium.uiautomator2.server'], stdout=subprocess.PIPE)
        subprocess.run(['adb', 'shell', 'am', 'force-stop', 'io.appium.uiautomator2.server.test'], stdout=subprocess.PIPE)
        sleep(3)
        return "PASS: Killed UiAutomator2"
    except:
        return "WARN: kill_uiautomator failed"

# 4. Restart everything (driver + uiautomator)
def restart_everything():
    shutdown_driver()
    kill_uiautomator()
    return init_driver()

# 5. Check if FLAG_SECURE is set (optional)
def is_flag_secure():
    try:
        output = subprocess.check_output(['adb', 'shell', 'dumpsys', 'window'], encoding='utf-8')
        focus_line = ""
        for line in output.splitlines():
            if "mCurrentFocus" in line:
                focus_line = line
                break
        if not focus_line:
            return False
        match = re.search(r'u0\s+([^\s}]+)', focus_line)
        if not match:
            return False
        window = match.group(1)
        idx = output.find(window)
        block = output[idx:idx + 500]
        return "FLAG_SECURE" in block
    except:
        return False

driver_lock = threading.Lock()

# def failcaseinit(input):
#     global driver, device_id, app_package

#     input = str(input)

#     with driver_lock:
#         # Read capabilities
#         with open(Capability_path, "r") as file:
#             caps = json.load(file)

#         print("[INIT] Restarting driver...")

#         # Create new Appium session
#         new_driver = webdriver.Remote("http://localhost:4723", caps)

#         # Update globals
#         driver = new_driver
#         device_id = caps["udid"]
#         app_package = caps["appPackage"]

#         # Start keep-alive again
#         # start_keep_alive(driver)

#         print("[INIT] Driver reinitialized OK")

#     return "PASS"
def just_init(input):
    global driver
    input=""

    start_time = time.time()   # ⏱️ Start

    # Reload capabilities
    with open(Capability_path, "r") as file:
        caps = json.load(file)

    print("[INIT] Restarting driver...")

    # Start new session
    driver = webdriver.Remote("http://localhost:4723", caps)

    end_time = time.time()   # ⏱️ End

    execution_time = end_time - start_time
    print(f"[INIT] Execution Time: {execution_time:.3f} seconds")
    return f"Initialised"
    
# just_init()
    
def failcaseinit(input):
    global driver, device_id, app_package

    input = str(input)

    with driver_lock:
        print("[INIT] UIA2 recovery started...")

        # 1️⃣ Kill old driver cleanly
        try:
            if driver:
                driver.quit()
                print("[INIT] Old driver quit")
        except Exception as e:
            print(f"[INIT] Driver quit error (ignored): {e}")

        # 2️⃣ Cooldown (VERY IMPORTANT)
        time.sleep(2.5)

        # 3️⃣ Reload capabilities
        with open(Capability_path, "r") as file:
            caps = json.load(file)

        print("[INIT] Restarting driver...")

        # 4️⃣ Start new session
        driver = webdriver.Remote("http://localhost:4723", caps)

        # 5️⃣ Update globals
        device_id = caps.get("udid")
        app_package = caps.get("appPackage")

        # 6️⃣ Final stabilization delay
        time.sleep(1.5)

        print("[INIT] Driver reinitialized OK")

    return "PASS"

# def file_watcher(filepath, check_interval=1):
#     """Background watcher that monitors for a stop file."""
#     while not stop_event.is_set():
#         if os.path.exists(filepath):
#             print(f"[STOP TRIGGER] File detected: {filepath}")
#             stop_event.set()
#             try:
#                 if driver:
#                     driver.quit()
                    
#                 driver = None
#                 os.remove(file_to_watch) 
#                 failcaseinit("demo")
#                 print("[STOP ACTION] Appium driver terminated.")
#             except Exception as e:
#                 print(f"[ERROR stopping driver]: {e}")
#             break
#         time.sleep(check_interval)

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
        

def capture_screenshot(output_path):
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        success = driver.save_screenshot(output_path)

        if not success:
            return "error:screenshot_not_created"
        if not os.path.exists(output_path):
            return "error:screenshot_file_missing"

        return output_path  # return actual path, not "ok"
    except Exception as e:
        return f"Not ok:capture_failed:{str(e)}"
    
def fast_screenshot(output_path):
    subprocess.run(
        f'adb exec-out screencap -p > "{output_path}"',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return output_path

def capture_screenshot_new(output_path, use_adb=True):
    if use_adb:
        fast_screenshot(output_path)
    else:
        png = driver.get_screenshot_as_png()
        with open(output_path, "wb") as f:
            f.write(png)
    return output_path



                                                                    ############## Init Main #############
def init_driver(variable_str="", timeout=10):
    global driver, device_id, stop_event,stop_thread_flag
    try:
        
        # If driver exists, check session
        if driver is not None:
            try:
                driver.current_activity  # Throws if session is dead
                return "PASS: Driver already initialized"
            except:
                try:
                    driver.quit()
                except:
                    pass
                driver = None

        # Read capabilities
        with open(Capability_path, "r") as file:
            caps = json.load(file)
        
        print(caps)

        # Start Appium session
        # driver = webdriver.Remote("http://localhost:4723", caps)
        driver = webdriver.Remote("http://localhost:4723", caps)
        # sleep(1)
        # start_keep_alive()
        safe_print("[INIT] Appium driver initialized")
        app_package = caps["appPackage"]
        device_id = caps["udid"]
        print(device_id)
        # Launch WhatsApp using ADB monkey command

        # ensure_app_in_foreground(app_package)
        
        stop_event = threading.Event()
        # stop_event.clear()
        # watcher_thread = threading.Thread(target=file_watcher, args=(file_to_watch,), daemon=True)
        # watcher_thread.start()
        watcher_thread = threading.Thread(target=file_watcher, args=(file_to_watch,), daemon=True)
        watcher_thread.start()
        
        stop_thread_flag = False  # global flag to stop the thread

        # monitor_thread = threading.Thread(target=appium_error_monitor, args=(5,), daemon=True)
        # monitor_thread.start()

        return "PASS: Driver initialized"

    except Exception as e:
        err = f"ERROR: Failed to initialize Appium driver: {str(e)}"
        safe_print(err)
        safe_print(traceback.format_exc())
        return err

# def Restart_App_Package_Name_Text(input):
#     """
#     LabVIEW-safe, hang-proof app restart
#     Input  : "Tata Motors PV App,<optional>"
#     Output : "Ok#..." or "Not ok#..."
#     """
#     global app_evpv

#     def adb(cmd, timeout=5):
#         try:
#             result = subprocess.run(
#                 cmd,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 text=True,
#                 timeout=timeout
#             )
#             return result.stdout.strip(), result.stderr.strip()
#         except subprocess.TimeoutExpired:
#             return "", "ADB_TIMEOUT"
#         except Exception as e:
#             return "", str(e)

#     try:
#         # ---------------- INPUT PARSE ----------------
#         app_name = input.split(",", 1)[0].strip().lower()

#         if app_name == "tata motors pv app":
#             package_name = "com.tatamotors.oneapp"
#             app_evpv=0
#         else:
#             package_name = "com.tatamotors.evoneapp"
#             app_evpv=1

#         # ---------------- FORCE STOP ----------------
#         cmd = ["adb"]
#         if device_id:
#             cmd += ["-s", device_id]
#         cmd += ["shell", "am", "force-stop", package_name]

#         _, err = adb(cmd, timeout=4)
#         if "ADB_TIMEOUT" in err:
#             return "Not ok#ADB timeout during force-stop"

#         sleep(0.8)

#         # ---------------- RESOLVE ACTIVITY ----------------
#         cmd = ["adb"]
#         if device_id:
#             cmd += ["-s", device_id]
#         cmd += [
#             "shell", "cmd", "package", "resolve-activity",
#             "--brief", package_name
#         ]

#         out, err = adb(cmd, timeout=5)
#         if not out or "not found" in out.lower():
#             return f"Not ok#Unable to resolve activity for {package_name}"

#         lines = out.splitlines()
#         if len(lines) < 2:
#             return f"Not ok#Invalid resolve-activity output"

#         app_activity = lines[1].replace("/", "").strip()

#         # ---------------- DIRECT ACTIVITY LAUNCH (MOST RELIABLE) ----------------
#         cmd = ["adb"]
#         if device_id:
#             cmd += ["-s", device_id]
#         cmd += [
#             "shell", "am", "start",
#             "-n", f"{package_name}/{app_activity}"
#         ]

#         _, err = adb(cmd, timeout=6)
#         if "ADB_TIMEOUT" in err:
#             return "Not ok#ADB timeout during launch"

#         sleep(2)

#         # ---------------- FALLBACK (MONKEY) ----------------
#         if not is_app_in_foreground(package_name):
#             cmd = ["adb"]
#             if device_id:
#                 cmd += ["-s", device_id]
#             cmd += [
#                 "shell", "monkey", "-p", package_name,
#                 "-c", "android.intent.category.LAUNCHER", "1"
#             ]
#             adb(cmd, timeout=4)
#             sleep(2)

#         # ---------------- FINAL CHECK ----------------
#         if is_app_in_foreground(package_name):
#             return f"Ok#{package_name} restarted successfully"
#         else:
#             return f"Not ok#{package_name} not in foreground"

#     except Exception as e:
#         return f"Not ok#Unhandled exception: {str(e)}"

# print(init_driver())

def Restart_App_Package_Name_Text(input):
    """
    LabVIEW-safe, robust app restart
    Input  : "Tata Motors PV App,<optional>"
    Output : "Ok#..." or "Not ok#..."
    """

    global app_evpv, device_id

    def adb(cmd, timeout=6):
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            return result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return "", "ADB_TIMEOUT"
        except Exception as e:
            return "", str(e)

    try:
        # ---------------- INPUT PARSE ----------------
        app_name = input.split(",", 1)[0].strip().lower()

        if app_name == "tata motors pv app":
            package_name = "com.tatamotors.oneapp"
            app_evpv = 0
        else:
            package_name = "com.tatamotors.evoneapp"
            app_evpv = 1

        # ---------------- FORCE STOP ----------------
        cmd = ["adb"]
        if device_id:
            cmd += ["-s", device_id]
        cmd += ["shell", "am", "force-stop", package_name]

        _, err = adb(cmd, timeout=4)
        if "ADB_TIMEOUT" in err:
            return "Not ok#ADB timeout during force-stop"

        sleep(1)

        # ---------------- GET LAUNCHABLE ACTIVITY ----------------
        cmd = ["adb"]
        if device_id:
            cmd += ["-s", device_id]
        cmd += [
            "shell", "cmd", "package", "resolve-activity",
            "--brief", package_name
        ]

        out, err = adb(cmd, timeout=5)

        component = None
        if out:
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            # Usually last line is the component
            component = lines[-1] if "/" in lines[-1] else None

        # ---------------- TRY DIRECT LAUNCH ----------------
        if component:
            cmd = ["adb"]
            if device_id:
                cmd += ["-s", device_id]
            cmd += [
                "shell", "am", "start",
                "-n", component
            ]

            _, err = adb(cmd, timeout=6)

            if "ADB_TIMEOUT" in err:
                return "Not ok#ADB timeout during launch"

            sleep(2)

        # ---------------- FALLBACK (MOST RELIABLE) ----------------
        if not is_app_in_foreground(package_name):
            cmd = ["adb"]
            if device_id:
                cmd += ["-s", device_id]
            cmd += [
                "shell", "monkey",
                "-p", package_name,
                "-c", "android.intent.category.LAUNCHER",
                "1"
            ]

            _, err = adb(cmd, timeout=5)
            if "ADB_TIMEOUT" in err:
                return "Not ok#ADB timeout during monkey launch"

            sleep(3)

        # ---------------- FINAL CHECK ----------------
        if is_app_in_foreground(package_name):
            return f"Ok#{package_name} restarted successfully"
        else:
            return f"Not ok#{package_name} not in foreground"

    except Exception as e:
        return f"Not ok#Unhandled exception: {str(e)}"
    
# print(init_driver())
# for i in range(20):
#     sleep(5)
#     print(Restart_App_Package_Name_Text("tata motors pv app,10"))
# init_driver()

def Get_Package_Name(input):
    """
    Reads the package name from a capabilities JSON file.

    Args:
        capability_path (str): Path to the Capabilities.json file.

    Returns:
        str: The app package name if found, else None.
    """
    try:
        if not os.path.exists(Capability_path):
            print(f"Error: Capability file not found at {Capability_path}")
            return None

        with open(Capability_path, "r") as file:
            caps = json.load(file)

        package_name = caps.get("appPackage")
        if package_name:
            return f"Ok#{package_name}"
        else:
            print("Error: 'appPackage' not found in Capabilities file.")
            return None

    except Exception as e:
        print(f"Error reading package name: {e}")
        return None

# for i in range(10):
#     init_driver()
#     print(f"for loop {i}")
#     print(restart_app("Input"))
#     sleep(10)

def Wait_Text(input):
    timeout,p=input.split(",")
    timeout=int(timeout)
    sleep(timeout)
    return "Ok#Wait over"


def Minimize_Android_Application(package_name, wait_time=0):
    """
    Minimizes (sends to background) the given Android app by package name.
   
    Args:
        package_name (str): App package name (e.g. 'com.whatsapp')
        wait_time (int): Optional time in seconds to wait before returning to home
    """
    try:
        # Read capabilities
        package_name = Get_Package_Name("input")
        p1,p2=package_name.split("#",1)
        package_name=p2
       
        # Option 1: Press HOME button (minimize app)
        subprocess.run(["adb", "-s", device_id, "shell", "input", "keyevent", "3"], check=True)
 
        # Optionally wait and verify if minimized
        if wait_time > 0:
            time.sleep(wait_time)
 
        # Option 2 (alternative): Explicitly stop app (comment out if not needed)
        # subprocess.run(["adb", "shell", "am", "force-stop", package_name], check=True)
 
        return f"Ok#App '{package_name}' minimized successfully."
    except subprocess.CalledProcessError as e:
        return f"Not ok#Failed to minimize app"
 
def run_adb_command(command):
    """Helper to run adb command safely using global device_id."""
    global device_id
    if device_id:
        command = ["adb", "-s", device_id] + command[1:]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip(), result.stderr.strip()

 
def is_app_running(package_name):
    """Check if app process exists."""
    out, _ = run_adb_command(["adb", "shell", "pidof", package_name])
    return bool(out)

def Close_Android_Application(package_name_input, device_id=None):
    """
    Universally closes an Android app (foreground + background)
    and removes it from the Recent Apps screen.
    Works on Android 7–14.
    
    Args:
        package_name_input (str): Full package name input (e.g., 'key#com.whatsapp')
        device_id (str): Optional ADB device ID (e.g., emulator-5554)
    """
    try:
        
        package_name = Get_Package_Name("input")
        p1,p2=package_name.split("#",1)
        package_name=p2
        print(f"Checking app: {package_name}")
            

        # Step 1: Check if app is running
        if is_app_running(package_name):
            print("App is currently running — stopping it...")
        else:
            print("App not running, proceeding to clear recents if visible...")

        # Step 2: Force-stop app (kills all processes)
        run_adb_command(["adb", "shell", "am", "force-stop", package_name])

        # Step 3: Try removing app from recents via task stack (optional)
        out, _ = run_adb_command(["adb", "shell", "am", "stack", "list"])
        for line in out.splitlines():
            if package_name in line and "taskId=" in line:
                task_id = line.split("taskId=")[1].split(" ")[0]
                run_adb_command(["adb", "shell", "am", "stack", "remove", task_id])
                print(f"Removed task {task_id} from recents.")
                break

        # Step 4: Fallback - Clear recents manually
        run_adb_command(["adb", "shell", "input", "keyevent", "187"])  # open recents
        time.sleep(1)
        run_adb_command(["adb", "shell", "input", "swipe", "500", "1000", "500", "0"])  # swipe up
        time.sleep(1)
        run_adb_command(["adb", "shell", "input", "keyevent", "3"])  # return to home

        # Step 5: Final check
        time.sleep(0.5)
        if not is_app_running(package_name):
            return f"Ok#'{package_name}' is fully closed and removed from recents."
        else:
            return f"Not ok#'{package_name}' process still exists (may be restarted via service)."
            

    except Exception as e:
        return f"Not ok#Error occurred: {e}"

# init_driver()
# print(Close_Android_Application("hello"))


#############################################################################################################
                                                #NEW FEATURE START#
#############################################################################################################


###########################################  Date and Time setter #########################################
def unique_points(points):
    seen = set()
    unique = []

    for p in points:
        if p not in seen:
            unique.append(p)
            seen.add(p)

    return unique

def get_date_time_points():
    points = []

    # Get all view groups (includes Compose containers)
    elements = driver.find_elements(
        AppiumBy.XPATH,
        "//*[self::android.view.ViewGroup or self::android.widget.LinearLayout or self::android.widget.FrameLayout]"
    )

    for el in elements:
        r = el.rect

        # 1️⃣ Size filter → looks like an input row
        if r["width"] < 0.8 * driver.get_window_size()["width"]:
            continue
        if r["height"] < 80 or r["height"] > 200:
            continue

        # 2️⃣ Must contain children (text + icon)
        if len(el.find_elements(AppiumBy.XPATH, ".//*")) < 2:
            continue

        x = r["x"] + r["width"] // 2
        y = r["y"] + r["height"] // 2

        points.append((int(x), int(y)))
    print(points)
    points=unique_points(points)

    return points



def get_4_field_points_generic():
    size = driver.get_window_size()
    w = size["width"]
    h = size["height"]

    x = w // 2

    # These ratios work across phones & orientations
    y_positions = [
        int(h * 0.38),  # Start date
        int(h * 0.45),  # Start time
        int(h * 0.55),  # End date
        int(h * 0.62)   # End time
    ]

    return [(x, y) for y in y_positions]



def get_selected_value_oold(picker):
    if not hasattr(picker, "_edit_text"):
        picker._edit_text = picker.find_element(
            AppiumBy.CLASS_NAME,
            "android.widget.EditText"
        )
    return picker._edit_text.text.strip()

def swipe_picker(picker, direction="up"):
    loc = picker.location
    size = picker.size

    x = loc['x'] + size['width'] // 2

    top    = loc['y'] + int(size['height'] * 0.25)
    bottom = loc['y'] + int(size['height'] * 0.75)

    if direction == "up":
        driver.swipe(x, bottom, x, top, 400)
    else:
        driver.swipe(x, top, x, bottom, 400)



def get_selected_value(picker, retries=5, delay=0.15):
    """
    Safe NumberPicker value reader.
    - Retries up to `retries` times if UIA2 returns None
    - Returns value string OR None
    """

    for attempt in range(retries):
        try:
            if not hasattr(picker, "_edit_text"):
                picker._edit_text = picker.find_element(
                    AppiumBy.CLASS_NAME,
                    "android.widget.EditText"
                )

            val = picker._edit_text.get_attribute("text")
            if val:
                return val.strip()

        except Exception:
            pass

        # Short UI settle time before retry
        time.sleep(delay)

    return None




########################  NEW   ######################
MONTHS = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec"
]


def normalize_picker_value(val):
    """Convert numeric or month text to normalized value"""
    if val is None:
        return None
    v = val.strip().lower()
    if v.isdigit():
        return int(v)
    # Month mapping
    if v in MONTHS:
        return MONTHS.index(v)
    return v  # fallback for other text pickers


def get_selected_value_fast(picker):
    try:
        edit = picker.find_element(
            AppiumBy.CLASS_NAME,
            "android.widget.EditText"
        )
        return edit.get_attribute("text")
    except Exception:
        return None

    
def swipe_picker_fast(picker, direction="up", duration=250):
    loc = picker.location
    size = picker.size
    x = loc['x'] + size['width'] // 2
    y1 = loc['y'] + int(size['height'] * 0.25)
    y2 = loc['y'] + int(size['height'] * 0.75)

    if direction == "up":
        driver.swipe(x, y2, x, y1, duration)
    else:
        driver.swipe(x, y1, x, y2, duration)

def safe_swipe(picker, direction, duration):
    try:
        swipe_picker_fast(picker, direction, duration)
        return True

    except Exception as e:
        if is_uia2_socket_error(e):
            if recover_uia2_session():
                return False  # retry loop
        raise

def smart_swipe(picker, diff):
    """Swipe intelligently based on numeric diff"""
    duration = 250
    if abs(diff) >= 8:
        duration = 100
    elif abs(diff) >= 3:
        duration = 300
    else:
        duration = 600
    direction = "up" if diff > 0 else "down"
    swipe_picker_fast(picker, direction, duration)
    return True  # always succeed (swipe attempted)

def smart_swipe_month(picker, current_idx, expected_idx):
    """
    Swipe intelligently for month picker
    current_idx, expected_idx -> 0..11
    """
    diff = (expected_idx - current_idx) % 12
    if diff == 0:
        return

    # Determine swipe direction (min steps)
    if diff <= 6:
        direction = "up"   # swipe forward
        steps = diff
    else:
        direction = "down" # swipe backward
        steps = 12 - diff

    # Swipe multiple steps in one go if far away
    duration = 180 if steps > 3 else 400
    for _ in range(steps):
        swipe_picker_fast(picker, direction, duration)
        time.sleep(0.05)  # tiny settle


def set_picker_value(picker, expected_value, max_swipes=30):
    expected = normalize_picker_value(expected_value)
    last = None

    for _ in range(max_swipes):
        try:
            raw = get_selected_value_fast(picker)
            current = normalize_picker_value(raw)

            if current == expected:
                return "Ok#Set"

            # Month or other non-numeric picker
            if not isinstance(current, int) or not isinstance(expected, int):
                # handle month smartly
                if isinstance(current, int) and isinstance(expected, int):
                    diff = (expected - current) % 12
                    if diff <= 6:
                        direction = "up"
                        steps = diff
                    else:
                        direction = "down"
                        steps = 12 - diff
                    for _ in range(steps):
                        swipe_picker_fast(picker, direction, 250)
                        time.sleep(0.05)
                else:
                    # fallback for text pickers
                    swipe_picker_fast(picker, "up", 300)
                last = current
                continue

            # Numeric picker diff
            diff = expected - current

            # Overshoot protection
            if last is not None:
                if (last < expected < current) or (last > expected > current):
                    swipe_picker_fast(picker, "down" if diff > 0 else "up", 600)
                    last = current
                    continue

            # Smart swipe for numeric
            smart_swipe(picker, diff)
            last = current

        except Exception as e:
            if is_uia2_socket_error(e):
                recover_uia2_session()
                return "Not ok#RETRY"
            return f"Not ok#{str(e)}"

    return f"Not ok#Failed to reach {expected_value}"



#################### MAIN #######################

def Set_Time_With_Text(input_str,_retry=0):
    """
    Generic NumberPicker handler (LabVIEW compatible)

    Input Examples:
        "15:August:2025:Confirm"
        "10:45:OK"
        "September:2026"
        "3:7:12:20:Done"

    Returns:
        "PASS"
        "FAIL|<reason>"
    """
    try:
        if not input_str:
            return "Not ok#Empty input string"

        param1,param2 = input_str.split(",")
        time,unit=param1.split(" ",1)
        time=int(time)
        unit=unit.strip().lower()

        if unit=="mins":
            time_plus = (datetime.now() + timedelta(minutes=time)).strftime("%H:%M")
        else:
            time_plus = (datetime.now() + timedelta(hours=time)).strftime("%H:%M")
        
        print(time_plus)
        print(datetime.now())

        parts=time_plus.split(":")

        # Detect confirm button
        confirm_text = "Confirm"
        if parts[-1].isalpha():
            confirm_text = parts.pop()

        values = parts

        pickers = driver.find_elements(
            AppiumBy.CLASS_NAME,
            "android.widget.NumberPicker"
        )

        print(f"NumberPickers found: {len(pickers)}")

        if not pickers:
            return "Not ok#No NumberPickers found"

        if len(values) > len(pickers):
            return f"Not ok#Input values ({len(values)}) > Pickers ({len(pickers)})"

        # Set pickers right → left
        for picker, value in zip(pickers, values):
        # for picker, value in zip(pickers, values):
            result=set_picker_value(picker, value)
            p1,p2=result.split("#")
            p2=p2.lower().strip()
            p1=p1.strip().lower()
            if p1=="not ok" and p2!="retry":
                return result
            elif p2=="retry":
                result=Set_Time_With_Text(input_str)

        # Click confirm if present
        try:
            driver.find_element(
                AppiumBy.XPATH,
                f"//android.widget.Button[@text='{confirm_text}']"
            ).click()
        except:
            pass
        print(datetime.now())

        return "Ok#Values seted properly"

    # except Exception as e:
    #     return f"Not ok#{str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Set_Time_With_Text(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    


def Set_Date_With_Text(input_str,_retry=0):
    """
    Generic NumberPicker handler (LabVIEW compatible)

    Input Examples:
        "15:August:2025:Confirm"
        "10:45:OK"
        "September:2026"
        "3:7:12:20:Done"

    Returns:
        "PASS"
        "FAIL|<reason>"
    """
    try:
        
        if not input_str:
            return "Not ok#Empty input string"

        param1,param2 = input_str.split(",")
        param1=param1.strip().lower()
        if param1 == "start":
            date_str = datetime.now().strftime("%b:%d:%Y")
        else:
            from dateutil.relativedelta import relativedelta

            one_year_later = datetime.now() + relativedelta(days=4)
            print(one_year_later)
            date_str = one_year_later.strftime("%b:%d:%Y")
        
        print(date_str)
        parts=date_str.split(":")

        # Detect confirm button
        confirm_text = "Confirm"
        if parts[-1].isalpha():
            confirm_text = parts.pop()

        values = parts

        pickers = driver.find_elements(
            AppiumBy.CLASS_NAME,
            "android.widget.NumberPicker"
        )

        print(f"NumberPickers found: {len(pickers)}")

        if not pickers:
            return "Not ok#No NumberPickers found"

        if len(values) > len(pickers):
            return f"Not ok#Input values ({len(values)}) > Pickers ({len(pickers)})"

        # Set pickers right → left
        # for picker, value in zip(reversed(pickers), reversed(values)):
        #     set_picker_value(picker, value)
        # for picker, value in zip(reversed(pickers), reversed(values)):
        for picker, value in zip(pickers, values):
            result = set_picker_value(picker, value)
            p1,p2=result.split("#")
            p1=p1.strip().lower()
            if p1=="not ok":
                return result
            
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                break   


        # Click confirm if present
        try:
            driver.find_element(
                AppiumBy.XPATH,
                f"//android.widget.Button[@text='{confirm_text}']"
            ).click()
        except:
            pass

        return "Ok#Values seted properly"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Set_Date_With_Text(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"


# init_driver()
# print(Set_Date_With_Text("End,10"))
# print(Set_Time_With_Text("1 mins,10"))

########################################## Hold Swipe to the right Mobilize ############################
import cv2
import os
import time


def Click_Hold_Swipe_Right_On_Image_old(text):
    """
    Find image, click it, hold it, and swipe fully to the right.

    Args:
        text (str): "image_path,timeout" (timeout ignored)

    Returns:
        str: "Ok#Clicked, held and swiped on image"
             "Not Ok# Aborted by abort signal"
             "ERROR: <details>"
    """
    try:
        # Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        image_path, _ = text.split(",", 1)
        
        capture_screenshot(temp_path)

        # 1️⃣ Take screenshot
        screenshot = "screen.png"
        # driver.get_screenshot_as_file(te)

        screen = cv2.imread(temp_path)
        template = cv2.imread(image_path)
        
        ## Screenshot ##
        
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        cv2.imwrite(full_path, curr_img)


        if screen is None or template is None:
            return f"Not ok# Screenshot or template image missing+{full_path}+{screen}+{template}"

        # 2️⃣ Find image
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, confidence, _, location = cv2.minMaxLoc(result)

        if confidence < 0.75:
            return f"Not ok# Image not found (confidence={confidence})+{full_path}"

        # 3️⃣ Image center
        h, w, _ = template.shape
        center_x = location[0] + w // 2
        center_y = location[1] + h // 2

        # 4️⃣ CLICK on image (tap)
        driver.execute_script("mobile: clickGesture", {
            "x": center_x,
            "y": center_y
        })

        time.sleep(0.3)  # small settle delay

        # 5️⃣ HOLD + SWIPE RIGHT
        size = driver.get_window_size()
        end_x = int(size["width"] * 0.98)

        driver.execute_script("mobile: swipeGesture", {
            "left": center_x,
            "top": center_y - 50,
            "width": end_x - center_x,
            "height": 100,
            "direction": "right",
            "percent": 1.0
        })

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        return f"Ok#Clicked, held and swiped on image+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"Not ok# Click_Hold_Swipe_Right_On_Image failed: {str(e)}"
    
# def Click_Hold_Swipe_Right_On_Image(text,_retry=0):
#     """
#     Detect slider by index, long-hold it, and swipe fully to the right.

#     Args:
#         text (str): "slider_index,timeout"

#     Returns:
#         str:
#             "Ok#Slider swiped successfully"
#             "Not Ok#Aborted by abort signal"
#             "Not Ok#<reason>"
#     """
#     try:
#         # Abort check
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#             return "Not Ok#Aborted by abort signal"

#         param1, param2 = text.split(",", 1)
#         slider_index = int(param1.strip())
#         timeout = int(param2.strip())

#         start_time = time.time()

#         while time.time() - start_time < timeout:

#             # Abort check inside loop
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Not Ok#Aborted by abort signal"

#             sliders = driver.find_elements(
#                 AppiumBy.CLASS_NAME,
#                 "android.widget.SeekBar"
#             )

#             if not sliders:
#                 time.sleep(0.5)
#                 continue

#             # Sort sliders top → bottom
#             sliders = sorted(sliders, key=lambda s: s.rect["y"])

#             if slider_index < 1 or slider_index > len(sliders):
#                 return f"Not Ok#Invalid slider index {slider_index}"

#             slider = sliders[slider_index - 1]
#             r = slider.rect

#             # Safe swipe coordinates
#             y = r["y"] + r["height"] // 2
#             x_start = r["x"] + int(r["width"] * 0.12)
#             x_end   = r["x"] + int(r["width"] * 0.90)

#             # 🔥 REAL hold + swipe
#             driver.execute_script("mobile: dragGesture", {
#                 "startX": x_start,
#                 "startY": y,
#                 "endX": x_end,
#                 "endY": y,
#                 "speed": 300
#             })

#             return "Ok#Slider swiped successfully"

#         return "Not Ok#Slider not detected within timeout"

#     # except Exception as e:
#     #     if os.path.exists(file_to_watch):
#     #         os.remove(file_to_watch)
#     #     return f"Not Ok#Click_Hold_Swipe_Right_On_Image failed: {str(e)}"
#     except Exception as e:

#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         if is_uia2_socket_error(e):
#             if _retry < 2:
#                 safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
#                 recover_uia2_session()
#                 sleep(1)
#                 return Click_Hold_Swipe_Right_On_Image(text, _retry=_retry + 1)

#             return "Not ok# UIA2 session recovery failed after retries"

#         return f"Not ok# {str(e)}"

def Click_Hold_Swipe_Right_On_Image(text, _retry=0):
    """
    Detect slider by index, long-hold it, and swipe fully to the right.

    Input:
        "slider_index,timeout"

    Output:
        Ok#Slider swiped successfully
        Not Ok#Aborted by abort signal
        Not Ok#Slider not detected within timeout
        Not Ok#Invalid slider index
    """

    try:

        # Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok#Aborted by abort signal"

        param1, param2 = text.split(",", 1)

        slider_index = int(param1.strip())
        timeout = int(param2.strip())

        # Ensure driver exists
        if not init_driver():
            return "Not Ok#Appium driver not initialized"

        start_time = time.time()

        while time.time() - start_time < timeout:

            # Abort check inside loop
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                return "Not Ok#Aborted by abort signal"

            sliders = driver.find_elements(
                AppiumBy.CLASS_NAME,
                "android.widget.SeekBar"
            )

            if not sliders:
                time.sleep(0.5)
                continue

            # Sort sliders top → bottom
            sliders = sorted(sliders, key=lambda s: s.rect["y"])

            if slider_index < 1 or slider_index > len(sliders):
                return f"Not Ok#Invalid slider index {slider_index}"

            slider = sliders[slider_index - 1]

            r = slider.rect

            # Safe swipe coordinates
            y = r["y"] + r["height"] // 2
            x_start = r["x"] + int(r["width"] * 0.12)
            x_end = r["x"] + int(r["width"] * 0.90)

            # Perform swipe
            driver.execute_script(
                "mobile: dragGesture",
                {
                    "startX": x_start,
                    "startY": y,
                    "endX": x_end,
                    "endY": y,
                    "speed": 300
                }
            )

            return "Ok#Slider swiped successfully"

        return "Not Ok#Slider not detected within timeout"

    except Exception as e:

        if os.path.exists(file_to_watch):
            try:
                os.remove(file_to_watch)
            except Exception:
                pass

        # Handle UIAutomator2 crash
        if is_uia2_socket_error(e):

            if _retry < 2:

                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")

                recover_uia2_session()

                sleep(1)

                return Click_Hold_Swipe_Right_On_Image(text, _retry=_retry + 1)

            return "Not Ok#UIA2 session recovery failed after retries"

        return f"Not Ok#{str(e)}"
    
# init_driver()
# print(Click_Hold_Swipe_Right_On_Image("0,10"))

# init_driver()
# Click_Hold_Swipe_Right_On_Image_old("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Immobilise.png,5")


############################################## Setting sliding values #################################

# # --- Read current radius value ---
# def read_time_value():
#     txt = driver.find_element(
#         AppiumBy.XPATH,
#         "//*[contains(@text,'min')]"
#     ).text
#     return txt.strip()

# # --- Read current radius value ---
# def read_radius_value():
#     txt = driver.find_element(
#         AppiumBy.XPATH,
#         "//*[contains(@text,'km')]"
#     ).text
#     return txt.strip()

# # --- Read current radius value ---
# def read_speed_value():
#     txt = driver.find_element(
#         AppiumBy.XPATH,
#         "//*[contains(@text,'km/hr') and not(contains(@text,'Speed'))]"
#     ).text
#     return txt.strip()


import re
from selenium.common.exceptions import StaleElementReferenceException

_last_radius = ""
_last_time = ""
_last_speed = ""

def _fast_read_text(keyword):
    try:
        driver.implicitly_wait(0)  # 🔥 NON BLOCKING
        elements = driver.find_elements(
            AppiumBy.CLASS_NAME,
            "android.widget.TextView"
        )

        for el in elements:
            try:
                txt = el.text
                if txt and keyword in txt:
                    return txt.strip()
            except StaleElementReferenceException:
                continue
        return None
    finally:
        driver.implicitly_wait(0.5)  # restore

def read_time_value():
    global _last_time
    txt = _fast_read_text("min")
    if txt:
        _last_time = txt
    return _last_time

def read_radius_value():
    global _last_radius
    txt = _fast_read_text("km")
    if txt:
        _last_radius = txt
    return _last_radius

# def read_speed_value():
#     global _last_speed
#     try:
#         driver.implicitly_wait(0)
#         elements = driver.find_elements(
#             AppiumBy.CLASS_NAME,
#             "android.widget.TextView"
#         )

#         for el in elements:
#             try:
#                 txt = el.text
#                 if txt and "km/hr" in txt and "Speed" not in txt:
#                     _last_speed = txt.strip()
#                     return _last_speed
#             except StaleElementReferenceException:
#                 continue
#         return _last_speed
#     finally:
#         driver.implicitly_wait(0.5)

def read_speed_value():
    """
    Reads the speed value from the screen.
    Returns the last known speed if current value is invalid or not found.
    """
    global _last_speed
    try:
        driver.implicitly_wait(0)
        elements = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")

        for el in elements:
            try:
                txt = el.text
                if txt and "km/hr" in txt:
                    # Extract numeric part using regex
                    match = re.search(r"(\d+)\s*km/hr", txt)
                    if match:
                        _last_speed = match.group(1) + "km/hr"
                        return _last_speed
            except StaleElementReferenceException:
                continue

        return _last_speed

    finally:
        driver.implicitly_wait(0.5)

def set_Coordinates(input):
    global x_str,y_str
    param1, pram2=input.split(",")
    x_str,y_str=param1.split("_")
    return "Ok#Coordinates are assigned to global variable"

           ########### BY COORD ###########

def Click_Hold_Swipe_Right_By_XY_Text_ValSet(text,_retry=0):
    """
    Incremental swipe right until:
        1. target value is reached, OR
        2. maximum swipe limit is reached

    Input format:
        "x,y,target_value,max_swipes"

    Returns:
        "Ok#Target reached:<value>"
        "FAIL#Max swipe reached without reaching target"
        "Not Ok#Aborted by abort signal"
        "ERROR#<details>"
    """
    try:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        target_value, max_swipes = text.split(",")
        x = int(float(x_str))
        y = int(float(y_str))
        target_value = str(target_value)
        max_swipes = int(max_swipes)
        notreq,valid_param=target_value.split(" ")

        # Initial click to focus slider
        driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
        time.sleep(0.1)

        size = driver.get_window_size()
        step_x = int(size["width"] * 0.02)  # very small swipe
        end_x = int(size["width"] * 0.95)

        for _ in range(max_swipes):
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                return "Not Ok# Aborted by abort signal"

            # Small swipe right
            swipe_end_x = min(x + step_x, end_x)
            driver.execute_script(
                "mobile: dragGesture",
                {
                    "startX": x,
                    "startY": y,
                    "endX": swipe_end_x,
                    "endY": y,
                    "duration": 180
                }
            )

            time.sleep(0.1)

            # Read current value
            if valid_param == "km":
                current_value = str(read_radius_value())
            elif valid_param == "min":
                current_value = str(read_time_value())
            else:
                target_value = target_value.replace(" ","")
                current_value = str(read_speed_value())
            
            print(f"current:{current_value}")

            # Check target
            if current_value == target_value:
                ## Screenshot ##
                capture_screenshot(temp_path)
                curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"screenshot_{timestamp}.png"
                full_path = os.path.join(Screenshot_path, save_path)
                cv2.imwrite(full_path, curr_img)

                return f"Ok#Target reached:{current_value}+{full_path}"

            # Move start point forward for next swipe
            x = swipe_end_x

            # If reached end of slider, stop
            if x >= end_x:
                break

        # Read final value after all swipes
        final_value = str(read_radius_value())
        if final_value == target_value:
            ## Screenshot ##
            capture_screenshot(temp_path)
            curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"screenshot_{timestamp}.png"
            full_path = os.path.join(Screenshot_path, save_path)
            cv2.imwrite(full_path, curr_img)

            return f"Ok#Target reached:{final_value}+{full_path}"
        else:
            ## Screenshot ##
            capture_screenshot(temp_path)
            curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"screenshot_{timestamp}.png"
            full_path = os.path.join(Screenshot_path, save_path)
            cv2.imwrite(full_path, curr_img)

            return f"Not ok#Max swipe reached, final value: {final_value}+{full_path}"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
    #     return f"Not ok#Click_Hold_Swipe_Right_By_Coordinates_Dynamic failed: {str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Click_Hold_Swipe_Right_By_XY_Text_ValSet(text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    
#     ################ BY IMAGE ################

def find_image_on_screen(template_path, threshold=0.8):
    driver.save_screenshot(temp_path)
    screen = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)

    if screen is None:
        raise Exception("Screenshot read failed")
    
    print(template_path)

    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise Exception(f"Template not loaded: {template_path}")

    sh, sw = screen.shape
    th, tw = template.shape

    if th > sh or tw > sw:
        raise Exception(
            f"Template bigger than screen | "
            f"T:{tw}x{th}, S:{sw}x{sh}"
        )

    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    if max_val < threshold:
        raise Exception("Slider image not found")

    return max_loc[0] + tw // 2, max_loc[1] + th // 2


def Set_Image_Path(input):

    param1,param2= input.split(",")
    os.makedirs(os.path.dirname(Image_File_Path), exist_ok=True)
    p=Path(param1)
    if app_evpv == 1:
        param1 = str(p.with_name("EV_" + p.name))
        param1=str(param1)
        param1 = param1.replace("\\", "\\\\")
    with open(Image_File_Path, "w", encoding="utf-8") as f:
        f.write(param1.strip())
        
    return "Ok#Image set successfully"

def find_all_images_on_screen(template_path, threshold=0.85):
    capture_screenshot(temp_path)

    img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if img is None:
        raise ValueError("Screenshot is None")

    if template is None:
        raise ValueError(f"Template not found: {template_path}")

    ih, iw = img.shape
    th, tw = template.shape

    # auto-resize template if bigger
    if th > ih or tw > iw:
        scale = min(iw / tw, ih / th) * 0.9
        template = cv2.resize(
            template,
            (int(tw * scale), int(th * scale))
        )
        th, tw = template.shape

    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(res >= threshold)

    points = []
    for pt in zip(*locations[::-1]):
        cx = pt[0] + tw // 2
        cy = pt[1] + th // 2
        points.append((int(cx), int(cy)))


    return points

def cluster_points(points, radius=30):
    """
    Groups nearby points into clusters and returns center of each cluster.
    """
    clusters = []

    for x, y in points:
        placed = False

        for cluster in clusters:
            cx, cy, count = cluster
            if abs(cx - x) <= radius and abs(cy - y) <= radius:
                # update centroid
                cluster[0] = (cx * count + x) // (count + 1)
                cluster[1] = (cy * count + y) // (count + 1)
                cluster[2] += 1
                placed = True
                break

        if not placed:
            clusters.append([x, y, 1])

    # return only (x,y)
    return [(int(c[0]), int(c[1])) for c in clusters]


def normalize_value(val):
    """
    Handles: '10km', '10 km', '10 KM', '10 Km'
    Returns: int(10)
    """
    if val is None:
        return None

    # keep digits only
    num = "".join(ch for ch in str(val) if ch.isdigit())
    return int(num) if num else None
# print(normalize_value("10km/hr"))
def SetKnobIndex_Text(input):
    global knob
    try:
        knob, timeout = input.split(",")
        knob = knob.strip()
        timeout = timeout.strip()

        return "Ok#Knob value set successfully"

    except Exception as e:
        return f"Not ok#Failed to set knob value: {str(e)}"

def normalize_value(val):
    """
    Normalize value to integer.
    Handles 'km', 'min', 'km/hr', 'kmph', or any numeric string.
    Returns None if cannot parse.
    """
    try:
        val_str = str(val).lower()
        # Extract first number from the string
        match = re.search(r"\d+", val_str)
        if match:
            return int(match.group())
        return None
    except Exception:
        return None

# def Click_Hold_Swipe_Right_By_Photo_Text_ValSet(text,_retry=0):
#     global knob  # declare knob as global
#     try:
#         knob =int(knob)
#         # 🔥 Check image file path
#         if not os.path.exists(Image_File_Path):
#             return "Not ok#Image path file missing"

#         with open(Image_File_Path, "r", encoding="utf-8") as f:
#             image_path = f.read().strip()

#         if not os.path.exists(image_path):
#             return f"Not ok#Template image missing:{image_path}"

#         # 🔥 Detect knobs
#         raw_points = find_all_images_on_screen(image_path)
#         points = cluster_points(raw_points)
#         print(f"Detected points: {points}")
#         print(f"Raw points: {raw_points}")

#         if len(points) == 0:
#             return "Not ok#Zero knobs found"

#         # -------------------------
#         # Parse input: "10 km,50"
#         # -------------------------
#         if "," not in text:
#             return "Not ok#Invalid input format, expected 'value,timeout'"

#         target_value, timeout = text.split(",")
#         target_value = target_value.strip()
#         timeout = int(timeout.strip())

#         # knob index (optional), default 0
#         # knob_index = 0
#         if "_" in target_value:
#             parts = target_value.split("_")
#             if len(parts) == 2:
#                 target_value, knob = parts
#                 knob = int(knob)

#         if knob >= len(points) or knob < 0:
#             return f"Not ok#Invalid knob index:{knob}"

#         x, y = points[knob]
#         if x is None or y is None:
#             return f"Not ok#Invalid coordinates for knob:{knob}"

#         print(f"Using knob index: {knob}, coordinates: ({x}, {y})")

#         # 🔥 Tap the knob first
#         driver.execute_script("mobile: clickGesture", {"x": x, "y": y})

#         # Window size
#         size = driver.get_window_size()
#         end_x = int(size["width"] * 0.95)

#         # Swipe step config
#         FAST_STEP = int(size["width"] * 0.02)
#         SLOW_STEP = int(size["width"] * 0.006)
#         DRAG_FAST = 80
#         DRAG_SLOW = 120

#         last_value = None
#         max_swipes = 50

#         # Determine value type
#         valid_param = ""
#         if " " in target_value:
#             _, valid_param = target_value.split(" ")
#         elif "/" in target_value:
#             valid_param = "km/hr"
#         elif "km" in target_value:
#             valid_param = "km"
#         elif "min" in target_value:
#             valid_param = "min"
#         else:
#             valid_param = "other"

#         for swipe_count in range(max_swipes):

#             # Stop condition if file exists
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break

#             # 🔥 Read current value
#             if valid_param == "km":
#                 current_value = str(read_radius_value())
#             elif valid_param == "min":
#                 current_value = str(read_time_value())
#             elif valid_param == "km/hr":
#                 current_value = str(read_speed_value())
#             else:
#                 current_value = str(read_speed_value())

#             if current_value == target_value:
#                 return f"Ok#Target reached:{current_value}"

#             # Decide swipe step
#             if current_value == last_value:
#                 step = FAST_STEP
#                 duration = DRAG_FAST
#             else:
#                 step = SLOW_STEP
#                 duration = DRAG_SLOW

#             last_value = current_value

#             # Normalize values
#             curr = normalize_value(current_value)
#             target = normalize_value(target_value)

#             if curr is None or target is None:
#                 return f"Not ok#Normalization failed, current:{current_value}, target:{target_value}"

#             # Break if already at target
#             if curr == target:
#                 return f"Ok#Target reached:{current_value}"

#             # Decide swipe direction
#             step_dir = step if curr < target else -step
#             swipe_end_x = x + step_dir

#             # Limit swipe_end_x to screen width
#             swipe_end_x = max(0, min(swipe_end_x, end_x))

#             # 🔥 Perform swipe
#             driver.execute_script(
#                 "mobile: dragGesture",
#                 {
#                     "startX": int(x),
#                     "startY": int(y),
#                     "endX": int(swipe_end_x),
#                     "endY": int(y),
#                     "duration": int(duration)
#                 }
#             )

#             x = swipe_end_x  # update start for next swipe

#         return f"Not ok#Max swipe reached, last:{current_value}"

#     except Exception as e:

#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         if is_uia2_socket_error(e):
#             if _retry < 2:
#                 safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
#                 recover_uia2_session()
#                 sleep(1)
#                 return Click_Hold_Swipe_Right_By_Photo_Text_ValSet(text, _retry=_retry + 1)

#             return "Not ok# UIA2 session recovery failed after retries"

#         return f"Not ok# {str(e)}"

def Click_Hold_Swipe_Right_By_Photo_Text_ValSet(text, _retry=0):
    """
    Robust swipe function that dynamically adjusts swipe distance based on difference
    between current and target values. Works with units like km, km/hr, min, etc.

    Input:
        text: "value,timeout" or "value_knobIndex,timeout" e.g. "15 km/hr,10"
    Output:
        Ok#Target reached:<value>
        Not ok#<reason>
    """
    global knob  # use global knob

    try:
        knob = int(knob)

        # 🔥 Check image path
        if not os.path.exists(Image_File_Path):
            return "Not ok#Image path file missing"

        with open(Image_File_Path, "r", encoding="utf-8") as f:
            image_path = f.read().strip()

        if not os.path.exists(image_path):
            return f"Not ok#Template image missing:{image_path}"

        # 🔥 Detect knobs on screen
        raw_points = find_all_images_on_screen(image_path)
        points = cluster_points(raw_points)
        print(f"Detected points: {points}, Raw points: {raw_points}")

        if len(points) == 0:
            return "Not ok#Zero knobs found"

        # -------------------------
        # Parse input
        # -------------------------
        if "," not in text:
            return "Not ok#Invalid input format, expected 'value,timeout'"

        target_value, timeout = text.split(",")
        target_value = target_value.strip()
        timeout = int(timeout.strip())

        # Optional knob index
        if "_" in target_value:
            parts = target_value.split("_")
            if len(parts) == 2:
                target_value, knob = parts
                knob = int(knob)

        if knob >= len(points) or knob < 0:
            return f"Not ok#Invalid knob index:{knob}"

        x, y = points[knob]
        if x is None or y is None:
            return f"Not ok#Invalid coordinates for knob:{knob}"

        print(f"Using knob index: {knob}, coordinates: ({x}, {y})")

        # 🔥 Tap the knob first
        driver.execute_script("mobile: clickGesture", {"x": x, "y": y})

        # Window size
        size = driver.get_window_size()
        end_x = int(size["width"] * 0.95)

        max_swipes = 60
        last_value = None

        # -------------------------
        # Determine unit type
        # -------------------------
        valid_param = ""
        if " " in target_value:
            _, valid_param = target_value.split()
        elif "/" in target_value:
            valid_param = "km/hr"
        elif "km" in target_value:
            valid_param = "km"
        elif "min" in target_value:
            valid_param = "min"
        else:
            valid_param = "other"

        # -------------------------
        # Swiping loop
        # -------------------------
        for swipe_count in range(max_swipes):

            # Stop if file exists
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                break

            # 🔥 Read current value
            if valid_param == "km":
                current_value = str(read_radius_value())
            elif valid_param == "min":
                current_value = str(read_time_value())
            elif valid_param == "km/hr":
                current_value = str(read_speed_value())
            else:
                current_value = str(read_speed_value())

            if current_value == target_value:
                return f"Ok#Target reached:{current_value}"

            # Normalize numeric values
            curr = normalize_value(current_value)
            target = normalize_value(target_value)

            if curr is None or target is None:
                return f"Not ok#Normalization failed, current:{current_value}, target:{target_value}"

            # 🔥 Dynamic step based on difference
            diff = abs(target - curr)

            if diff > 5:       # large difference → big swipe
                step = int(size["width"] * 0.07)
                duration = 10
            else:               # small difference → fine swipe
                step = int(size["width"] * 0.03)
                duration = 20

            # Adjust swipe direction
            step_dir = step if curr < target else -step
            swipe_end_x = x + step_dir
            swipe_end_x = max(0, min(swipe_end_x, end_x))

            # 🔥 Perform swipe
            driver.execute_script(
                "mobile: dragGesture",
                {
                    "startX": int(x),
                    "startY": int(y),
                    "endX": int(swipe_end_x),
                    "endY": int(y),
                    "duration": int(duration)
                }
            )

            x = swipe_end_x  # update start for next swipe
            last_value = current_value

            # Stop if target reached after swipe
            if normalize_value(str(current_value)) == target:
                return f"Ok#Target reached:{current_value}"

        return f"Not ok#Max swipe reached, last:{current_value}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        # Retry for UIA2 socket errors
        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                sleep(1)
                return Click_Hold_Swipe_Right_By_Photo_Text_ValSet(text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

# init_driver()
# print(Set_Image_Path("C:\\Users\\panch\\Downloads\\knob.png,10"))
# print(SetKnobIndex_Text("0,10"))
# print(Click_Hold_Swipe_Right_By_Photo_Text_ValSet("5min,10"))


def Fine_Adjust_Slider(target, y):
    size = driver.get_window_size()
    step = int(size["width"] * 0.002)

    for _ in range(10):
        curr = int(read_radius_value())
        if curr == target:
            return f"Ok#Target reached:{curr}"

        direction = step if curr < target else -step

        driver.execute_script(
            "mobile: dragGesture",
            {
                "startX": int(size["width"] * 0.5),
                "startY": y,
                "endX": int(size["width"] * 0.5) + direction,
                "endY": y,
                "duration": 120
            }
        )

        time.sleep(0.08)

    return f"Not Ok#Final adjust failed, last value:{curr}"

def ensure_driver_alive():
    """
    Fast non-blocking Appium session health check.
    Self-recovers automatically if anything is wrong.
    """

    try:
        # Fastest possible no-op call
        _ = driver.session_id
        _ = driver.current_activity
        return True

    except Exception as e:
        safe_print(f"[HEALTH] Driver not alive: {e}")
        return failcaseinit("Dummy")

############################################### GET CAR CURRENT LOCATION ###################################

def Get_Curent_Location(input):
    global Car_Current_Location
    elements = driver.find_elements(
            AppiumBy.CLASS_NAME,
            "android.widget.TextView"
        )

    for i, el in enumerate(elements):
        txt = el.text.strip()
        if txt and (i==2):
            print(f"[{i}] {txt}")
            Car_Current_Location=txt
    return f"Ok#{Car_Current_Location}"



def get_lat_long_from_maps_search():
    try:
        el = driver.find_element(
            AppiumBy.CLASS_NAME,
            "android.widget.EditText"
        )
        txt = el.text.strip()

        # Expected format: "18.64283759,73.8017841"
        lat_str, lon_str = txt.split(",")

        lat = float(lat_str)
        lon = float(lon_str)

        return lat, lon

    except Exception as e:
        # Return None for both lat and lon on error
        return None, None

######################################## Driver Score ######################################

# def Get_Driver_Score_Text(input):
#     global Driver_Score
#     param1,param2=input.split(",")

#     elements = driver.find_elements(
#         AppiumBy.CLASS_NAME,
#         "android.widget.TextView"
#     )

#     # # Safety check
#     # if len(elements) <= 6:
#     #     return "Not ok#Driver score element not found"

    

#     ## Screenshot ##
#     capture_screenshot(temp_path)
#     curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     save_path = f"screenshot_{timestamp}.png"
#     full_path = os.path.join(Screenshot_path, save_path)
#     cv2.imwrite(full_path, curr_img)

#     valid = elements[6]   # direct indexing
#     Validation_txt = valid.text.strip()

#     el = elements[5]   # direct indexing
#     txt = el.text.strip()

#     if Validation_txt == "No data available":
#         return f"Not ok#No data available on screen+{full_path}"

#     if not txt:
#         return "Not ok#Empty Driver score text"

#     Driver_Score = float(txt)

#     if Driver_Score > 0:
#         return f"Ok#Driver score: {Driver_Score}+{full_path}"
#     else:
#         return f"Not ok#Driver Score: {Driver_Score}+{full_path}"


def Get_Driver_Score_Text(input,_retry=0):
    global Driver_Score
    try:
        param1, param2 = input.split(",")
        number = re.findall(r'\d+', param1)[0]
        number=int(number)

        elements = driver.find_elements(
            AppiumBy.CLASS_NAME,
            "android.widget.TextView"
        )
        
        for i in elements:
            print(i.text)

        # Safety check for indexing
        if len(elements) <= 6:
            return "Not Ok#Driver score elements not found"

        ## Screenshot ##
        capture_screenshot(temp_path)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)

        cv2.imwrite(full_path, curr_img)

        # # Direct indexing (now protected)
        Validation_txt = elements[3].text.strip()
        txt = elements[3].text.strip()

        if Validation_txt == "No data available":
            return f"Not Ok#No data available on screen+{full_path}"

        if not txt:
            return f"Not Ok#Empty Driver score text+{full_path}"

        try:
            Driver_Score = float(txt)
        except ValueError:
            return f"ERROR#Invalid Driver score value: {txt}+{full_path}"

        if Driver_Score > number:
            return f"Ok#Driver score: {Driver_Score}+{full_path}"
        else:
            return f"Not Ok#Driver Score: {Driver_Score}+{full_path}"

    except ValueError:
        return "ERROR#Invalid input format. Expected: param1,param2"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Get_Driver_Score_Text(input, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

# init_driver()
# print(Get_Driver_Score_Text(">0,10"))
 ################## SOS #################

# ################ Main ###########
    
def PressAndHold_By_Gesture_Text(input_str,_retry=0):
    """
    input_str formats:
        "x,y,hold_ms"
        "x%,y%,hold_ms"

    Examples:
        "540,1620,6000"
        "50%,80%,5000"

    Returns:
        Ok# ...
        Not Ok# ...
        ERROR# ...
    """

    import time

    start_time = time.perf_counter()

    try:
        # ==============================
        # Parse input
        # ==============================
        # hold_ms,timeout = input_str.split(",", 1)
        data,timeout=input_str.split(",")
        x_str,y_str,hold_ms=data.split("_")
        hold_ms = int(hold_ms.strip())

        win = driver.get_window_size()
        w, h = win["width"], win["height"]

        # ==============================
        # Resolve coordinates
        # ==============================
        if "%" in x_str:
            x = int(float(x_str.replace("%", "")) * w / 100)
        else:
            x = int(float(x_str))

        if "%" in y_str:
            y = int(float(y_str.replace("%", "")) * h / 100)
        else:
            y = int(float(y_str))

        if not (0 <= x <= w and 0 <= y <= h):
            return f"Not Ok# Coordinates out of bounds ({x},{y})"

        if hold_ms < 1000 or hold_ms > 15000:
            return "Not Ok# Invalid hold duration"

        # ==============================
        # GESTURE HOLD
        # ==============================
        # driver.execute_script(
        #     "mobile: dragGesture",
        #     {
        #         "startX": x,
        #         "startY": y,
        #         "endX": x,
        #         "endY": y,
        #         "duration": hold_ms   # ⏱ HOLD HERE
        #     }
        driver.execute_script(
            "mobile: longClickGesture",
            {
                "x": x,
                "y": y,
                "duration": hold_ms
            }
        )

        exec_time = (time.perf_counter() - start_time) * 1000
        return f"Ok# GestureHold({hold_ms}ms) at ({x},{y})"

    # except Exception as e:
    #     exec_time = (time.perf_counter() - start_time) * 1000
    #     return f"Not ok# {str(e)} | {exec_time:.1f}ms"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return PressAndHold_By_Gesture_Text(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

def PressAndHold_By_Image(input_str,_retry=0):
    """
    input_str formats:
        "image_path,hold_ms,threshold"

    Examples:
        "C:/images/sos.png,6000,0.8"
        "sos.png,5000,0.75"

    Returns:
        Ok# ...
        Not Ok# ...
        ERROR# ...
    """



    start_time = time.perf_counter()

    try:
        # ==============================
        # Parse input (OLD STYLE)
        # ==============================
        image_path,timeout= input_str.split(",")
        hold_ms = 6000
        threshold = 0.1

        if hold_ms < 1000 or hold_ms > 15000:
            return "Not Ok# Invalid hold duration"

        # ==============================
        # Take screenshot from Appium
        # ==============================
        png_base64 = driver.get_screenshot_as_base64()
        screen_bytes = base64.b64decode(png_base64)
        screen_np = np.frombuffer(screen_bytes, np.uint8)
        screen_img = cv2.imdecode(screen_np, cv2.IMREAD_COLOR)

        if screen_img is None:
            return "Not Ok# Failed to capture screenshot"

        # ==============================
        # Load template image
        # ==============================
        template = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if template is None:
            return f"Not Ok# Image not found: {image_path}"

        # ==============================
        # Template matching
        # ==============================
        result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            return f"Not Ok# Image not found (score={max_val:.2f})"

        # ==============================
        # Calculate center coordinates
        # ==============================
        h, w = template.shape[:2]
        x = int(max_loc[0] + w / 2)
        y = int(max_loc[1] + h / 2)

        # ==============================
        # GESTURE HOLD (SAME AS OLD)
        # ==============================
        driver.execute_script(
            "mobile: longClickGesture",
            {
                "x": x,
                "y": y,
                "duration": hold_ms
            }
        )

        exec_time = (time.perf_counter() - start_time) * 1000
        return f"Ok# ImageHold({hold_ms}ms) at ({x},{y}) | score={max_val:.2f}"

    # except Exception as e:
    #     exec_time = (time.perf_counter() - start_time) * 1000
    #     return f"Not Ok# {str(e)} | {exec_time:.1f}ms"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return PressAndHold_By_Image(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

def Get_Vehicle_Health_Status_Text(input,_retry=0):
    try:
        # ---------------- Input validation ----------------
        if not input or "," not in input or ":" not in input:
            return "Not ok#Invalid input format. Expected: section:parameter,xxx"

        param1, param2 = input.split(",", 1)

        if ":" not in param1:
            return "Not ok#Invalid section format. Expected section:parameter"

        section, parameter = param1.split(":", 1)
        section = section.strip().lower()
        parameter = parameter.strip().lower()

        # ---------------- Fetch elements safely ----------------
        try:
            elements = driver.find_elements(
                AppiumBy.CLASS_NAME,
                "android.widget.TextView"
            )
        except Exception as e:
            return f"Not ok#Failed to fetch UI elements: {str(e)}"

        with_issues = []
        without_issues = []
        current_section = None

        # ---------------- Parse UI text ----------------
        for el in elements:
            try:
                text = el.text.strip().lower()
            except Exception:
                continue

            if not text:
                continue

            if text == "systems with issues":
                current_section = "with_issues"
                continue

            if text == "systems without any issues":
                current_section = "without_issues"
                continue

            if current_section == "with_issues":
                with_issues.append(text)
            elif current_section == "without_issues":
                without_issues.append(text)
            
        print(with_issues)
        print(without_issues)
        
        capture_screenshot(Ref_Img_Path)
        curr_img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"Ref_Screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)
        
        # ---------------- Validation logic ----------------
        if section == "systems with issues" or section == "system with issues" or section == "system with issue" or section == "systems with issue":
            if parameter in with_issues:
                return f"Ok#System with issues contains {parameter}+{full_path}"
            else:
                return f"Not ok#System with issues does not contain {parameter}+{full_path}"

        elif section == "systems without any issues" or section == "system without any issues" or section == "system without any issue" or section == "systems without any issue":
            if parameter in without_issues:
                return f"Ok#System without any issues contains {parameter}+{full_path}"
            else:
                return f"Not ok#System without any issues does not contain {parameter}+{full_path}"

        else:
            return f"Not ok#Unknown section: {section}+{full_path}"

    # except Exception as e:
    #     # ---------------- Global safety net ----------------
    #     return f"Not ok#Unexpected error: {str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Get_Vehicle_Health_Status_Text(input, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    
# init_driver()
# print(Get_Vehicle_Health_Status_Text("System with issues:airbag,10"))

# def Compare_Screen_By_Text_Optional(input):
#     param1, param2 = input.split(",")
#     timeout=int(param2)
#     sleep(timeout)
#     Valid_text = param1.strip().lower()

#     elements = driver.find_elements(
#         AppiumBy.CLASS_NAME,
#         "android.widget.TextView"
#     )

#     texts = []
#     for element in elements:
#         if element.text:  # safety check
#             texts.append(element.text.lower())
#     texts=str(texts).encode("utf-8", errors="ignore").decode()

#     print(texts)


#     if Valid_text in texts:
#         return f"Ok#{Valid_text} text is found on screen"
#     else:
#         return f"Not ok#{Valid_text} text is not found on screen"

# def Compare_Screen_By_Text_Optional(input,_retry=0):
#     try:
#         param1, param2 = input.split(",")
#         timeout = int(param2)
#         sleep(timeout)

#         Valid_text = param1.strip().lower()

#         elements = driver.find_elements(
#             AppiumBy.CLASS_NAME,
#             "android.widget.TextView"
#         )

#         texts = []
#         for element in elements:
#             try:
#                 if element.text:  # safety check
#                     texts.append(element.text.lower())
#             except Exception:
#                 # Skip problematic element
#                 continue

#         # Unicode-safe conversion
#         texts = str(texts).encode("utf-8", errors="ignore").decode()

#         print(texts)

#         if Valid_text in texts:
#             return f"Ok#{Valid_text} text is found on screen"
#         else:
#             return f"Not Ok#{Valid_text} text is not found on screen"

#     except ValueError:
#         return "Not ok#Invalid input format. Expected: text,timeout"

#     except Exception as e:

#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         if is_uia2_socket_error(e):
#             if _retry < 2:
#                 safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
#                 recover_uia2_session()
#                 sleep(1)
#                 return Compare_Screen_By_Text_Optional(input, _retry=_retry + 1)

#             return "Not ok# UIA2 session recovery failed after retries"

#         return f"Not ok# {str(e)}"


def Compare_Screen_By_Text_Optional(input, _retry=0):
    try:
        # -------------------------
        # Parse input
        # -------------------------
        param1, param2 = input.split(",")
        timeout = float(param2.strip())
        search_text = param1.strip().lower()

        # -------------------------
        # Smart short wait (non-blocking style)
        # Instead of long sleep, small polling
        # -------------------------
        end_time = time.time() + timeout

        while time.time() < end_time:

            # 🔥 SINGLE FAST DEVICE-SIDE QUERY
            elements = driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().textMatches("(?i).*{search_text}.*")'
            )

            if elements:
                return f"Ok#{search_text} text is found on screen"
            


            sleep(0.15)  # very small polling delay
        if search_text=="sierra":
            ## Screenshot ##
            capture_screenshot(temp_path)
            curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"screenshot_{timestamp}.png"
            full_path = os.path.join(Screenshot_path, save_path)

            cv2.imwrite(full_path, curr_img)
            return f"Not ok#TD is down+{full_path}"
        else:
            return f"Not ok#{search_text} text is not found on screen"

    except ValueError:
        return "Not ok#Invalid input format. Expected: text,timeout"

    except WebDriverException as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                sleep(0.5)
                return Compare_Screen_By_Text_Optional(input, _retry=_retry + 1)

            return "Not ok#UIA2 session recovery failed after retries"

        return f"Not ok#{str(e)}"

    except Exception as e:
        return f"Not ok#{str(e)}"

# init_driver()
# print(Compare_Screen_By_Text_Optional("Km/h,10"))

def BadRequest_Validation_Text(input_str, lang="eng"):
    """
    LabVIEW-friendly OCR validation function

    Input  : "expected_text,timeout"
    Output : "Ok#<message>+<image_path>"
             "Not ok#<message>+<image_path>"
             "Not ok#<error_reason>"
    """

    try:
        # ------------------ INPUT PARSING ------------------
        parts = input_str.split(",", 1)
        if len(parts) != 2:
            return "Not ok#Invalid input format. Expected: text,timeout"

        valtext = parts[0].strip().lower()
        timeout = parts[1].strip()  # kept for compatibility (not used here)

        # ------------------ IMAGE READ ------------------
        if not os.path.exists(Common_Ref_Img_Path):
            return "Not ok#Image path does not exist"

        img = cv2.imread(Common_Ref_Img_Path)
        if img is None:
            return "Not ok#Image could not be read"

        # ------------------ PREPROCESS ------------------
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]

        # ------------------ OCR ------------------
        raw_text = pytesseract.image_to_string(
            gray,
            lang=lang,
            config="--psm 6"
        )

        # ------------------ TEXT CLEANING ------------------
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

        clean_text = " ".join(lines)
        clean_text = re.sub(r"\s+", " ", clean_text).lower().strip()

        # ------------------ SAVE TIMESTAMP IMAGE ------------------
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, filename)

        cv2.imwrite(full_path, gray)

        # ------------------ VALIDATION ------------------
        if valtext in clean_text:
            return f"Ok#Error occurred+{full_path}"
        else:
            return f"Not ok#Operation executed properly+{full_path}"

    except Exception as e:
        return f"Not ok#Exception:{str(e)}"
    
def clean_text(text):
    """
    Removes emojis, symbols, and extra spaces.
    Keeps only a-z, 0-9 and space.
    """
    # Remove non-ASCII characters (emojis, icons)
    text = text.encode("ascii", "ignore").decode()

    # Remove special characters (keep letters, numbers, spaces)
    text = re.sub(r'[^a-zA-Z0-9 ]+', ' ', text)

    # Normalize spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text.lower()


# def Com_Screen_By_Text_Optional(input):
#     param1, param2 = input.split(",")
#     timeout = int(param2)
#     sleep(timeout)

#     Valid_text = clean_text(param1)

#     elements = driver.find_elements(
#         AppiumBy.CLASS_NAME,
#         "android.widget.TextView"
#     )

#     texts = []
#     for element in elements:
#         if element.text:
#             cleaned = clean_text(element.text)
#             if cleaned:
#                 texts.append(cleaned)

#     # Safe print (no Unicode crash, no symbols)
#     print(texts)

#     if Valid_text in texts:
#         return f"Ok#{Valid_text} text is found on screen"
#     else:
#         return f"Not ok#{Valid_text} text is not found on screen"

def Com_Screen_By_Text_Optional(input,_retry=0):
    try:
        param1, param2 = input.split(",")
        timeout = int(param2)
        sleep(timeout)

        Valid_text = clean_text(param1)

        elements = driver.find_elements(
            AppiumBy.CLASS_NAME,
            "android.widget.TextView"
        )

        texts = []
        for element in elements:
            try:
                if element.text:
                    cleaned = clean_text(element.text)
                    if cleaned:
                        texts.append(cleaned)
            except Exception:
                # Ignore single element failure
                continue

        # Safe print (no Unicode crash, no symbols)
        print(texts)

        if Valid_text in texts:
            return f"Ok#{Valid_text} text is found on screen"
        else:
            return f"Not Ok#{Valid_text} text is not found on screen"

    except ValueError:
        return "Not ok#Invalid input format. Expected: text,timeout"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Com_Screen_By_Text_Optional(input, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"


# init_driver()
# print(Com_Screen_By_Text_Optional("Sierra,10"))
#print(Get_Vehicle_Health_Status_Text("Systems without any issues:Intrusion Alert,10"))



#############################################################################################################
                                                #NEW FEATURE END#
#############################################################################################################


#################################################### Format ############################################################
def format_result(status: str, message: str, screenshot_path: str = None) -> str:
    """
    Generic result formatter for validation output.

    Args:
        status (str): PASS / FAIL / ERROR
        message (str): What happened (details)
        screenshot_path (str, optional): Path to screenshot, if available

    Returns:
        str: Multi-line result string for LabVIEW or logs
    """
    # Ensure status is always uppercase
    status = status.upper()

    # If screenshot not provided, mark it
    if not screenshot_path or not os.path.exists(screenshot_path):
        screenshot_path = "Screenshot not available"

    result = f"STATUS: {status}\tMESSAGE: {message}\tSCREENSHOT: {screenshot_path}"
    return result

#################################################### Common Def for image related function ###################################

def screenshot_to_cv_image(screenshot_base64):
    nparr = np.frombuffer(base64.b64decode(screenshot_base64), np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def take_screenshot(driver):
    return screenshot_to_cv_image(driver.get_screenshot_as_base64())

def load_reference_image(path, grayscale=False):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR)
    if img is None:
        safe_print(f"[ERROR] Failed to load image: {path}")
        raise FileNotFoundError(f"Image not found: {path}")
    return img

def find_template_in_screenshot(screenshot_cv, template_cv, threshold=0.8):
    screenshot_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)
    template_gray = template_cv if len(template_cv.shape) == 2 else cv2.cvtColor(template_cv, cv2.COLOR_BGR2GRAY)

    # Optional: Gaussian blur to reduce noise
    screenshot_gray = cv2.GaussianBlur(screenshot_gray, (3, 3), 0)
    template_gray = cv2.GaussianBlur(template_gray, (3, 3), 0)

    for scale in np.linspace(0.7, 1.3, 25)[::-1]:
        resized_template = cv2.resize(template_gray, (0, 0), fx=scale, fy=scale)
        if resized_template.shape[0] > screenshot_gray.shape[0] or resized_template.shape[1] > screenshot_gray.shape[1]:
            continue
        res = cv2.matchTemplate(screenshot_gray, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        safe_print(f"[MATCH] Scale={scale:.2f}, Score={max_val:.3f}")

        if max_val >= threshold:
            h, w = resized_template.shape[:2]

            # Debug: draw bounding box and save screenshot
            debug_img = screenshot_cv.copy()
            cv2.rectangle(debug_img, max_loc, (max_loc[0] + w, max_loc[1] + h), (0, 255, 0), 2)
            cv2.imwrite("C:/temp/debug_matched_area.png", debug_img)

            return (max_loc[0] + w // 2, max_loc[1] + h // 2)

    return None





################################################### Check notification ##########################################################

def Check_Notification(text,_retry=0):
    """
    Open notifications, wait for timeout, then close the panel.

    Args:
        text (str): Input format "<any_text>,<timeout_in_sec>"

    Returns:
        str: "Ok# Notification panel checked" on success
             "Not Ok# <reason>" if failed
             "ERROR: <exception details>" for unexpected errors
    """
    try:
        param1, param2 = text.split(",", 1)
        timeout = int(param2)

        driver.open_notifications()
        sleep(timeout)
        driver.press_keycode(4)

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        return "Ok# Notification panel checked"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
    #     return f"Not ok: {str(e)}\n"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Check_Notification(text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

# init_driver()
# Check_Notification("hi,1")

def Open_Notification_Panel(text,_retry=0):
    """
    Open notifications, wait for timeout, then close the panel.

    Args:
        text (str): Input format "<any_text>,<timeout_in_sec>"

    Returns:
        str: "Ok# Notification panel checked" on success
             "Not Ok# <reason>" if failed
             "ERROR: <exception details>" for unexpected errors
    """
    try:
        param1, param2 = text.split(",", 1)
        timeout = int(param2)

        driver.open_notifications()
        #sleep(timeout)
        #driver.press_keycode(4)

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        return "Ok# Notification panel opened"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
    #     return f"Not ok: {str(e)}\n"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Open_Notification_Panel(text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

# init_driver()
# Open_Notification_Panel("hi,1")

def Close_Notification_Panel(text,_retry=0):
    """
    Open notifications, wait for timeout, then close the panel.

    Args:
        text (str): Input format "<any_text>,<timeout_in_sec>"

    Returns:
        str: "Ok# Notification panel checked" on success
             "Not Ok# <reason>" if failed
             "ERROR: <exception details>" for unexpected errors
    """
    try:
        param1, param2 = text.split(",", 1)
        timeout = int(param2)

        #driver.open_notifications()
        #sleep(timeout)
        driver.press_keycode(4)

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        return "Ok# Notification panel closed"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
    #     return f"Not ok: {str(e)}\n"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Close_Notification_Panel(text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

# init_driver()
# Close_Notification_Panel("hi,1")
###################################################### Mobile Resolution ##########################################################

def get_resolution(device_input):
    try:
        # Extract device id (first value before comma)
        device_id = device_input.split(",")[0].strip()

        # Run adb command
        result = subprocess.check_output(
            ['adb', '-s', device_id, 'shell', 'wm', 'size'],
            encoding='utf-8'
        )

        # Example output: Physical size: 1080x2400
        match = re.search(r'Physical size:\s*(\d+)x(\d+)', result)

        if match:
            width, height = match.groups()
            return f"{width}x{height}"
        else:
            return "ERROR: Resolution not found"

    except subprocess.CalledProcessError:
        return "ERROR: ADB command failed"

    except Exception as e:
        return "ERROR: " + str(e)


def check_image_exists(path, threshold=0.8):
    """
    Check if an image exists on the screen by template matching.

    Args:
        path (str): Path to the reference image
        threshold (float): Matching threshold (default 0.8)

    Returns:
        str: "Ok# Image found <path>"
             "Not Ok# Image not found <path>"
             "ERROR: <exception details>"
    """
    try:
        threshold = float(threshold)

        if not init_driver():
            return "ERROR: Driver not initialized"

        template = load_reference_image(path)
        screenshot = take_screenshot(driver)

        # Debug: Save images
        cv2.imwrite("C:/temp/screenshot.png", screenshot)
        cv2.imwrite("C:/temp/template.png", template)

        pos = find_template_in_screenshot(screenshot, template, threshold)

        if pos:
            msg = f"Ok# Image found {path}"
        else:
            msg = f"Not Ok# Image not found {path}"

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        safe_print(msg)
        return msg

    except Exception as e:
        err = f"ERROR: check_image_exists failed: {str(e)}"
        safe_print(err)

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        return err

################################################## Wait Until Text Appear ######################################################

def Wait_Until_Text_Appears(visible_text, check_interval=2,_retry=0):
    """
    Hybrid wait until specified text appears on screen:
    1. Try find_element with case-insensitive XPath
    2. If not found within timeout, fallback to OCR check on screenshot

    Args:
        visible_text (str): "text_to_find,timeout"
        check_interval (int|float): Polling interval in seconds (default 2s)

    Returns:
        str: "Ok# Text '<text>' appeared"
             "Not Ok# Aborted by abort signal"
             "Not Ok# Text '<text>' not found within timeout (checked OCR too)"
             "ERROR: <exception details>"
    """
    try:
        # Parse input
        param1, param2 = visible_text.split(",", 1)
        search_str = param1.strip()
        timeout = float(param2)
        check_interval = float(check_interval)

        if not init_driver():
            return "ERROR: Driver not initialized"

        wait = WebDriverWait(driver, timeout, poll_frequency=check_interval)

        def condition(drv):
            # Abort signal check
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                raise TimeoutException("ABORT")

            try:
                # Case-insensitive XPath
                xpath = ("//*[translate(@text,"
                         "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')="
                         f"'{search_str.lower()}']")
                element = drv.find_element(By.XPATH, xpath)
                return element if element else False
            except NoSuchElementException:
                return False

        try:
            element = wait.until(condition)
            return f"Ok# Text '{search_str}' appeared"
        except TimeoutException as e:
            if "ABORT" in str(e):
                return "Not Ok# Aborted by abort signal"

            # Fallback to OCR
            capture_screenshot(temp_path)
            img = cv2.imread(temp_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            custom_config = r'--oem 3 --psm 6'
            extracted_text = pytesseract.image_to_string(thresh, config=custom_config, lang='eng')

            if search_str.lower() in extracted_text.lower():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"screenshot_ocr_found_{timestamp}.png"
                full_path = os.path.join(Screenshot_path, save_path)
                cv2.imwrite(full_path, img)
                return f"Ok# Text '{search_str}' appeared (via OCR)+{full_path}"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"screenshot_not_found_{timestamp}.png"
                full_path = os.path.join(Screenshot_path, save_path)
                cv2.imwrite(full_path, img)
                return f"Not Ok# Text '{search_str}' not found within timeout+{full_path}"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
    #     return f"Not ok: Wait_Until_Text_Appears failed: {str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Wait_Until_Text_Appears(visible_text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"


# init_driver()
# print(Wait_Until_Text_Appears("Enter your 4-digit security PIN,10"))

################################################## Wait Until Image Appear ######################################################
# Screenshot capture
def take_screenshot_cv(driver):
    screenshot_png = driver.get_screenshot_as_png()
    nparr = np.frombuffer(screenshot_png, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

# Load the reference image
def load_reference_image(path):
    return cv2.imread(path, cv2.IMREAD_COLOR)

# Compare images using template matching
def check_image_exists(path, threshold):
    try:
        template = load_reference_image(path)
        if template is None:
            return f"[ERROR] Unable to load reference image at {path}"

        screenshot = take_screenshot_cv(driver)
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        if max_val >= threshold:
            return f"[FOUND] Match {max_val:.2f}"
        else:
            return f"[NF] Match {max_val:.2f}"
    except Exception as e:
        return f"[ERROR] check_image_exists failed: {e}\n{traceback.format_exc()}"
    
def _preprocess_gray(img):
    """Convert to grayscale and apply CLAHE to normalize lighting."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    return clahe.apply(gray)

def _multi_scale_template_match(screen_gray, tpl_gray, scales=None):
    """
    Multi-scale normalized cross-correlation template matching.
    Returns (best_score, best_loc, best_scale, best_w, best_h)
    """
    sw, sh = screen_gray.shape[1], screen_gray.shape[0]
    tw, th = tpl_gray.shape[1], tpl_gray.shape[0]

    if scales is None:
        scales = np.linspace(0.5, 1.8, 26)  # covers smaller/larger variants

    best_score = -1.0
    best = (None, None, None, None, None)
    for scale in scales:
        nw, nh = int(tw * scale), int(th * scale)
        if nw < 8 or nh < 8:
            continue
        # template must be <= screen for matchTemplate; if bigger, skip
        if nw > sw or nh > sh:
            continue
        try:
            tpl_resized = cv2.resize(tpl_gray, (nw, nh), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(screen_gray, tpl_resized, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if max_val > best_score:
                best_score = max_val
                best = (max_val, max_loc, scale, nw, nh)
        except Exception:
            continue
    return best  # (score, loc, scale, w, h)

def _edge_template_match(screen_gray, tpl_gray):
    """Edge-based matching using Canny + matchTemplate (helps with contrast/format changes)."""
    edges_screen = cv2.Canny(screen_gray, 50, 150)
    edges_tpl = cv2.Canny(tpl_gray, 50, 150)
    return _multi_scale_template_match(edges_screen, edges_tpl, scales=np.linspace(0.6,1.4,16))

def _orb_feature_match(screen_gray, tpl_gray,
                       ratio_test=0.75, min_good_matches=10, ransac_thresh=5.0, min_inliers=8):
    """
    ORB feature matching + homography verification.
    Returns dict: {found:bool, inliers:int, good_matches:int, homography, corners_transformed, inlier_ratio:float}
    """
    orb = cv2.ORB_create(nfeatures=2000)

    kp1, des1 = orb.detectAndCompute(tpl_gray, None)
    kp2, des2 = orb.detectAndCompute(screen_gray, None)
    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        return {"found": False}

    # BFMatcher with Hamming for ORB
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(des1, des2, k=2)
    good = []
    for m_n in matches:
        if len(m_n) != 2:
            continue
        m, n = m_n
        if m.distance < ratio_test * n.distance:
            good.append(m)

    if len(good) < min_good_matches:
        return {"found": False, "good_matches": len(good)}

    pts_tpl = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1,1,2)
    pts_scr = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1,1,2)

    H, mask = cv2.findHomography(pts_tpl, pts_scr, cv2.RANSAC, ransac_thresh)
    if H is None or mask is None:
        return {"found": False, "good_matches": len(good)}

    inliers = int(mask.sum())
    inlier_ratio = inliers / max(1, len(good))

    # Map template corners to screen to measure coverage / sanity-check
    h_tpl, w_tpl = tpl_gray.shape[0], tpl_gray.shape[1]
    corners = np.float32([[0,0],[w_tpl,0],[w_tpl,h_tpl],[0,h_tpl]]).reshape(-1,1,2)
    try:
        corners_transformed = cv2.perspectiveTransform(corners, H)
        # compute area of mapped polygon (watch out for degenerate)
        poly = corners_transformed.reshape(-1,2)
        area = 0.5 * abs(np.dot(poly[:,0], np.roll(poly[:,1], 1)) - np.dot(poly[:,1], np.roll(poly[:,0], 1)))
    except Exception:
        corners_transformed = None
        area = 0

    return {
        "found": (inliers >= min_inliers and inlier_ratio >= 0.18),
        "inliers": inliers,
        "good_matches": len(good),
        "homography": H,
        "corners": corners_transformed,
        "inlier_ratio": inlier_ratio,
        "mapped_area": area
    }

def robust_check_image_exists(template_path, screen_bgr,
                              tm_threshold=0.86, tm_secondary=0.80, orb_min_matches=10,
                              debug=False):
    """
    Try multiple detection strategies on the provided screen image (BGR).
    Returns (True/False, details_dict)
    """
    if not os.path.exists(template_path):
        return False, {"error": "template_missing"}

    tpl_bgr = cv2.imread(template_path)
    if tpl_bgr is None:
        return False, {"error": "template_read_failed"}

    screen_gray = _preprocess_gray(screen_bgr)
    tpl_gray = _preprocess_gray(tpl_bgr)

    details = {}

    # 1) Fast multi-scale template matching
    score, loc, scale, w, h = _multi_scale_template_match(screen_gray, tpl_gray) or (-1, None, None, None, None)
    details['template_best_score'] = float(score) if score is not None else -1
    if score is not None and score >= tm_threshold:
        details['method'] = 'multi-scale-template'
        details['match_score'] = float(score)
        details['match_loc'] = loc
        details['match_scale'] = float(scale)
        return True, details

    # 2) Edge-based template matching (helps for icons, text, low-color changes)
    score_e, loc_e, scale_e, w_e, h_e = _edge_template_match(screen_gray, tpl_gray) or (-1, None, None, None, None)
    details['edge_best_score'] = float(score_e) if score_e is not None else -1
    if score_e is not None and score_e >= tm_secondary:
        details['method'] = 'edge-template'
        details['match_score'] = float(score_e)
        details['match_loc'] = loc_e
        details['match_scale'] = float(scale_e)
        return True, details

    # 3) Feature matching (ORB) + homography: best for scaling, small cropping and perspective
    orb_res = _orb_feature_match(screen_gray, tpl_gray, min_good_matches=orb_min_matches)
    details['orb'] = orb_res
    if orb_res.get("found", False):
        details['method'] = 'orb-homography'
        return True, details

    # Heuristic: if template match score is decent (>= tm_secondary) OR ORB has many good matches (even if not passing strict homography),
    # we might still accept when user wants tolerant detection — but be conservative to avoid false positives.
    if score is not None and score >= tm_secondary:
        details['method'] = 'multiscale-template-secondary'
        return True, details

    # No detection
    details['method'] = 'none'
    return False, details

def Wait_Until_Image_Appears(path_with_timeout, threshold=0.86, check_interval=1.0, timeout_message_screenshot=True, debug=False,_retry=0):
    """
    Robust wait until image appears. `path_with_timeout` -> "path,timeout_seconds"
    `threshold` is used as primary template matching score (0..1).
    Returns: same string-format as your original function.
    """
    try:
        # Parse input
        parts = path_with_timeout.split(",", 1)
        if len(parts) != 2:
            return "Not ok: Input format must be 'path,timeout'"

        path = parts[0].strip()
        timeout = float(parts[1].strip())
        threshold = float(threshold)
        check_interval = float(check_interval)
        filename = os.path.basename(path)

        if not init_driver():
            return "Not ok: Driver not initialized"

        start_time = time.time()

        while True:
            # Abort signal check (same behavior as your code)
            if os.path.exists(file_to_watch):
                try:
                    os.remove(file_to_watch)
                except Exception:
                    pass
                return "Not Ok# Aborted by abort signal"

            # Capture the current screen (use your capture_screenshot helper)
            capture_result = capture_screenshot(temp_path)
            if capture_result != "ok":
                # fallback: try to continue but log error
                safe_print(f"[WARN] capture_screenshot returned: {capture_result}")

            if not os.path.exists(temp_path):
                safe_print("[WARN] screenshot file not found after capture")
                sleep(check_interval)
                if time.time() - start_time > timeout:
                    break
                continue

            screen_bgr = cv2.imread(temp_path, cv2.IMREAD_COLOR)
            if screen_bgr is None:
                safe_print("[WARN] failed to read screenshot file")
                sleep(check_interval)
                if time.time() - start_time > timeout:
                    break
                continue

            found, details = robust_check_image_exists(path, screen_bgr, tm_threshold=threshold, debug=debug)
            print(details)
            if debug:
                safe_print(f"[DEBUG] detector details: {details}")

            if found:
                return f"Ok# Image '{filename}' appeared"

            # not found; check timeout
            if time.time() - start_time > timeout:
                # Save final failure screenshot (timestamped)
                try:
                    curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_path = f"screenshot_{timestamp}.png"
                    full_path = os.path.join(Screenshot_path, save_path)
                    cv2.imwrite(full_path, curr_img)
                except Exception as e:
                    safe_print(f"[ERROR] saving failure screenshot: {e}")
                    full_path = temp_path if os.path.exists(temp_path) else "screenshot_not_available"
                return f"Not Ok# Image '{filename}' not found+{full_path}"

            sleep(check_interval)

    # except Exception as e:
    #     # Ensure abort file cleaned up
    #     try:
    #         if os.path.exists(file_to_watch):
    #             os.remove(file_to_watch)
    #     except Exception:
    #         pass
    #     return f"Not ok: Wait_Until_Image_Appears failed: {str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Wait_Until_Image_Appears(path_with_timeout, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"


# init_driver()
# print(Wait_Until_Image_Appears("D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Disconnectivity.jpg,10"))
######################################################## Click Operation ###############################################

def Click_By_Text_old(visible_text):
    """
    Click on a UI element by its visible text (exact or partial).

    Args:
        visible_text (str): "text_to_click,timeout"

    Returns:
        str: "Ok# Clicked on '<text>'"
             "Not Ok# '<text>' not found within timeout"
             "Not Ok# Aborted by abort signal"
             "ERROR: <details>"
    """
    global Common_Ref_Img_Path
    try:
        param1, param2 = visible_text.split(",", 1)
        search_text = str(param1).strip()  # text to search
        timeout = int(param2)              # timeout in seconds

        for _ in range(timeout):
            # ✅ Abort check
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                return "Not Ok# Aborted by abort signal"

            try:
                # 🔍 Try exact match first
                el = None
                try:
                    el = driver.find_element(By.XPATH, f"//*[@text='{search_text}']")
                except NoSuchElementException:
                    # 🔍 Fallback: partial match (contains)
                    try:
                        el = driver.find_element(By.XPATH, f"//*[contains(@text, '{search_text}')]")
                    except NoSuchElementException:
                        pass

                if el:  # Found element
                    el.click()
                    sleep(1)
                    capture_screenshot(Ref_Img_Path)
                    curr_img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_path = f"Click_Operation_Ref_Screenshot.png"
                    full_path = os.path.join(Screenshot_path, save_path)
                    # Save the image
                    cv2.imwrite(full_path, curr_img)
                    Common_Ref_Img_Path=full_path
                    return f"Ok# Clicked on '{search_text}'"
            except Exception as inner:
                safe_print(f"[LOOP ERROR] {inner}")

            sleep(0.5)
        
         
        capture_screenshot(temp_path)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)

        return f"Not Ok# '{search_text}' not found+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"Not ok: Failed to click on '{visible_text}': {str(e)}"

# def Click_By_Text(visible_text, _retry=0):
#     """
#     Robust, dynamic and fail-safe text click handler.

#     Input:
#         "text_to_click,timeout"

#     Output:
#         Ok# Clicked on '<text>'
#         Not Ok# '<text>' not found + <screenshot_path>
#         Not Ok# Aborted by abort signal
#         ERROR# <details>
#     """

#     global Common_Ref_Img_Path

#     try:
#         # -----------------------------
#         # Parse input
#         # -----------------------------
#         raw_text, raw_timeout = visible_text.split(",", 1)
#         search_text = raw_text.lower().strip()
#         timeout = int(raw_timeout)

#         start_time = time.time()

#         # -----------------------------
#         # MAIN LOOP
#         # -----------------------------
#         while time.time() - start_time < timeout:

#             # 🔴 Abort handling
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Not Ok# Aborted by abort signal"

#             el = None

#             # -----------------------------
#             # 1️⃣ FAST: Case-insensitive XPath
#             # -----------------------------
#             fast_xpaths = [
#                 f"//*[translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='{search_text}']",
#                 f"//*[contains(translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{search_text}')]",
#                 f"//*[contains(translate(@content-desc,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{search_text}')]"
#             ]

#             for xp in fast_xpaths:
#                 try:
#                     el = driver.find_element(By.XPATH, xp)
#                     if el:
#                         break
#                 except:
#                     pass

#             # -----------------------------
#             # 2️⃣ MEDIUM: Visible element scan
#             # -----------------------------
#             if not el:
#                 try:
#                     elements = driver.find_elements(By.XPATH, "//*")
#                     for e in elements:
#                         try:
#                             combined_text = (
#                                 (e.text or "") + " " +
#                                 (e.get_attribute("content-desc") or "")
#                             ).lower().strip()

#                             if search_text in combined_text:
#                                 el = e
#                                 break
#                         except:
#                             continue
#                 except:
#                     pass

#             # -----------------------------
#             # 3️⃣ CLICK IF FOUND
#             # -----------------------------
#             if el:
#                 try:
#                     el.click()
#                     sleep(0.8)

#                     # 📸 Capture success reference
#                     capture_screenshot(Ref_Img_Path)
#                     img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)

#                     save_path = os.path.join(
#                         Screenshot_path,
#                         "Click_Operation_Ref_Screenshot.png"
#                     )
#                     cv2.imwrite(save_path, img)

#                     Common_Ref_Img_Path = save_path
#                     return f"Ok# Clicked on '{raw_text.strip()}'"

#                 except Exception as click_err:
#                     safe_print(f"[CLICK FAILED] {click_err}")

#             sleep(0.5)

#         # -----------------------------
#         # ❌ FINAL FAILURE → Screenshot
#         # -----------------------------
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         temp_path = os.path.join(Screenshot_path, f"NotFound_{timestamp}.png")

#         capture_screenshot(temp_path)
#         img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#         cv2.imwrite(temp_path, img)
#         if _retry<2:
#             Click_By_Text(visible_text,_retry = _retry + 1)
#         else:
#             return f"Not Ok# '{raw_text.strip()}' not found + {temp_path}"

#     # except Exception as e:
#     #     if os.path.exists(file_to_watch):
#     #         os.remove(file_to_watch)

#     #     if is_uia2_socket_error(e):
#     #         recover_uia2_session()
#     #         return Click_By_Text(visible_text)
        
#     #     return f"Not ok#{str(e)}"
#     except Exception as e:

#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         if is_uia2_socket_error(e):
#             if _retry < 2:
#                 safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
#                 recover_uia2_session()
#                 sleep(1)
#                 return Click_By_Text(visible_text, _retry=_retry + 1)

#             return "Not ok# UIA2 session recovery failed after retries"

#         return f"Not ok# {str(e)}"


# def Click_By_Image(path, threshold=0.86, check_interval=1.0, debug=False, _retry=0):
#     """
#     Robustly click on a UI element by matching an image on the screen.

#     Handles low-texture icons (e.g., toggles) with fallback multi-scale matching.

#     Args:
#         path (str): "image_path,timeout"
#         threshold (float): Matching threshold (default 0.86)
#         check_interval (float): Polling interval in seconds (default 1.0)
#         debug (bool): Enable detailed debug logging.

#     Returns:
#         str: "Ok# Clicked on image '<path>' at (x,y)"
#              "Not Ok# Image '<path>' not found within timeout"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <details>"
#     """
#     try:
#         # Parse inputs
#         parts = path.split(",", 1)
#         if len(parts) != 2:
#             return "Not ok: Input format must be 'image_path,timeout'"

#         img_path = parts[0].strip()
#         timeout = float(parts[1].strip())
#         file_name = os.path.basename(img_path).strip()
        
#         p = Path(img_path)

#         if app_evpv == 1:
#             img_path = str(p.with_name("EV_" + p.name))

#         if not os.path.exists(img_path):
#             return f"Not ok: Reference image not found: {img_path}"

#         if not init_driver():
#             return "Not ok: Appium driver not initialized"

#         start_time = time.time()

#         while True:
#             # Abort check
#             if os.path.exists(file_to_watch):
#                 try:
#                     os.remove(file_to_watch)
#                 except Exception:
#                     pass
#                 return "Not Ok# Aborted by abort signal"

#             # Capture screenshot
#             capture_result = capture_screenshot(temp_path)
#             if not capture_result or not os.path.exists(capture_result):
#                 safe_print(f"[WARN] Screenshot failed: {capture_result}")
#                 sleep(check_interval)
#                 if time.time() - start_time > timeout:
#                     break
#                 continue

#             screen_bgr = cv2.imread(temp_path, cv2.IMREAD_COLOR)
#             if screen_bgr is None:
#                 safe_print("[WARN] Failed to read screenshot file")
#                 sleep(check_interval)
#                 if time.time() - start_time > timeout:
#                     break
#                 continue

#             # 🔍 Primary robust image detection
#             found, details = robust_check_image_exists(
#                 img_path, screen_bgr, tm_threshold=threshold, debug=debug
#             )

#             if debug:
#                 safe_print(f"[DEBUG] Detection details: {details}")

#             click_x, click_y = None, None

#             if found:
#                 method = details.get("method", "unknown")

#                 # --- Template or Edge-based Match ---
#                 if method in ["multi-scale-template", "edge-template", "multiscale-template-secondary"]:
#                     match_loc = details.get("match_loc")
#                     if match_loc:
#                         (mx, my) = match_loc
#                         scale = details.get("match_scale", 1.0)
#                         tpl = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
#                         if tpl is not None:
#                             th, tw = tpl.shape[:2]
#                             click_x = int(mx + tw * scale / 2)
#                             click_y = int(my + th * scale / 2)
#                     else:
#                         safe_print("[WARN] match_loc missing, attempting fallback detection...")
#                         found, (click_x, click_y) = multi_scale_fallback(img_path, screen_bgr, threshold, debug)

#                 # --- ORB / Feature-based Match ---
#                 elif method == "orb-homography" and details.get("corners") is not None:
#                     poly = details["corners"].reshape(-1, 2)
#                     M = cv2.moments(poly)
#                     if M["m00"] != 0:
#                         click_x = int(M["m10"] / M["m00"])
#                         click_y = int(M["m01"] / M["m00"])
#                 else:
#                     # --- Unknown method fallback ---
#                     safe_print("[INFO] Unknown detection method, triggering multi-scale fallback...")
#                     found, (click_x, click_y) = multi_scale_fallback(img_path, screen_bgr, threshold, debug)

#                 # --- Perform Click if Coordinates Found ---
#                 if click_x is not None and click_y is not None:
#                     driver.execute_script("mobile: clickGesture", {"x": click_x, "y": click_y})
#                     return f"Ok# Clicked on image '{os.path.basename(img_path)}' at ({click_x},{click_y})"

#                 else:
#                     safe_print("[WARN] Could not compute click coordinates even though match was found")

#             # Timeout check
#             if time.time() - start_time > timeout:
#                 try:
#                     curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#                     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                     save_path = f"screenshot_{timestamp}.png"
#                     full_path = os.path.join(Screenshot_path, save_path)
#                     cv2.imwrite(full_path, curr_img)
#                 except Exception as e:
#                     safe_print(f"[ERROR] saving timeout screenshot: {e}")
#                     full_path = temp_path if os.path.exists(temp_path) else "screenshot_not_available"

#                 if _retry<2:
#                     Click_By_Image(path,_retry = _retry + 1)
#                 else:
#                     return f"Not Ok# Image '{os.path.basename(img_path)}' not found.+ {full_path}"

#             sleep(check_interval)

#     # except Exception as e:
#     #     try:
#     #         if os.path.exists(file_to_watch):
#     #             os.remove(file_to_watch)
#     #     except Exception:
#     #         pass
#     #     return f"Not ok: Click_By_Image failed for '{path}': {str(e)}"
#     except Exception as e:

#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         if is_uia2_socket_error(e):
#             if _retry < 2:
#                 safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
#                 recover_uia2_session()
#                 sleep(1)
#                 return Click_By_Image(path, _retry=_retry + 1)

#             return "Not ok# UIA2 session recovery failed after retries"

#         return f"Not ok# {str(e)}"

def Click_By_Image(path, threshold=0.86, check_interval=1.0, debug=False):
    """
    Robustly click on a UI element by matching an image on the screen.

    Input:
        "image_path,timeout"

    Output:
        Ok# Clicked on image '<path>' at (x,y)
        Not Ok# Image '<path>' not found within timeout
        Not Ok# Aborted by abort signal
        ERROR# <details>
    """

    MAX_RETRY = 2
    retry_count = 0

    while retry_count <= MAX_RETRY:

        try:

            # -----------------------------
            # Parse Input
            # -----------------------------
            parts = path.split(",", 1)

            if len(parts) != 2:
                return "Not ok# Input format must be 'image_path,timeout'"

            img_path = parts[0].strip()
            timeout = float(parts[1].strip())

            p = Path(img_path)

            if app_evpv == 1:
                img_path = str(p.with_name("EV_" + p.name))

            if not os.path.exists(img_path):
                return f"Not ok# Reference image not found: {img_path}"

            # -----------------------------
            # Initialize Driver
            # -----------------------------
            if not init_driver():
                return "Not ok# Appium driver not initialized"

            start_time = time.time()

            # -----------------------------
            # Main Detection Loop
            # -----------------------------
            while time.time() - start_time < timeout:

                # Abort signal check
                if os.path.exists(file_to_watch):
                    try:
                        os.remove(file_to_watch)
                    except Exception:
                        pass
                    return "Not Ok# Aborted by abort signal"

                # -----------------------------
                # Capture Screenshot
                # -----------------------------
                capture_result = capture_screenshot(temp_path)

                if not capture_result or not os.path.exists(capture_result):
                    safe_print("[WARN] Screenshot failed")
                    sleep(check_interval)
                    continue

                screen_bgr = cv2.imread(temp_path, cv2.IMREAD_COLOR)

                if screen_bgr is None:
                    safe_print("[WARN] Screenshot read failed")
                    sleep(check_interval)
                    continue

                # -----------------------------
                # Image Detection
                # -----------------------------
                found, details = robust_check_image_exists(
                    img_path,
                    screen_bgr,
                    tm_threshold=threshold,
                    debug=debug
                )

                if debug:
                    safe_print(f"[DEBUG] Detection details: {details}")

                click_x, click_y = None, None

                if found:

                    method = details.get("method", "unknown")

                    # -----------------------------
                    # Template Matching
                    # -----------------------------
                    if method in [
                        "multi-scale-template",
                        "edge-template",
                        "multiscale-template-secondary"
                    ]:

                        match_loc = details.get("match_loc")

                        if match_loc:

                            mx, my = match_loc
                            scale = details.get("match_scale", 1.0)

                            tpl = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

                            if tpl is not None:

                                th, tw = tpl.shape[:2]

                                click_x = int(mx + (tw * scale) / 2)
                                click_y = int(my + (th * scale) / 2)

                        else:

                            safe_print("[WARN] match_loc missing → fallback")

                            found, (click_x, click_y) = multi_scale_fallback(
                                img_path,
                                screen_bgr,
                                threshold,
                                debug
                            )

                    # -----------------------------
                    # ORB Feature Matching
                    # -----------------------------
                    elif method == "orb-homography":

                        corners = details.get("corners")

                        if corners is not None:

                            poly = corners.reshape(-1, 2)

                            M = cv2.moments(poly)

                            if M["m00"] != 0:

                                click_x = int(M["m10"] / M["m00"])
                                click_y = int(M["m01"] / M["m00"])

                    # -----------------------------
                    # Unknown Method → Fallback
                    # -----------------------------
                    else:

                        safe_print("[INFO] Unknown method → fallback")

                        found, (click_x, click_y) = multi_scale_fallback(
                            img_path,
                            screen_bgr,
                            threshold,
                            debug
                        )

                    # -----------------------------
                    # Perform Click
                    # -----------------------------
                    if click_x is not None and click_y is not None:

                        driver.execute_script(
                            "mobile: clickGesture",
                            {"x": click_x, "y": click_y}
                        )

                        return f"Ok# Clicked on image '{os.path.basename(img_path)}' at ({click_x},{click_y})"

                sleep(check_interval)

            # -----------------------------
            # Timeout Handling
            # -----------------------------
            try:

                curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                save_path = f"screenshot_{timestamp}.png"

                full_path = os.path.join(Screenshot_path, save_path)

                cv2.imwrite(full_path, curr_img)

            except Exception as e:

                safe_print(f"[ERROR] saving timeout screenshot: {e}")

                full_path = temp_path if os.path.exists(temp_path) else "screenshot_not_available"

            retry_count += 1

            if retry_count > MAX_RETRY:
                return f"Not Ok# Image '{os.path.basename(img_path)}' not found + {full_path}"

            safe_print(f"[RETRY] Click_By_Image retry {retry_count}")

        # -----------------------------
        # Exception Handling
        # -----------------------------
        except Exception as e:

            if os.path.exists(file_to_watch):
                try:
                    os.remove(file_to_watch)
                except Exception:
                    pass

            if is_uia2_socket_error(e):

                retry_count += 1

                if retry_count <= MAX_RETRY:

                    safe_print(f"[UIA2 RECOVERY] Retry {retry_count}")

                    recover_uia2_session()

                    sleep(1)

                    continue

                return "Not Ok# UIA2 session recovery failed"

            return f"Not Ok# {str(e)}"

# init_driver()
# print(Click_By_Image("C:\\Users\\yuvraj.s.MTPA332-L\\Documents\\stealthmode.png,10"))

# =================================================
# ---------------- ADB UTILITIES ------------------
# =================================================
def adb_screenshot():
    """Ultra-fast screenshot using ADB (no Appium)"""
    proc = subprocess.Popen(
        ["adb", "exec-out", "screencap", "-p"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    img_bytes = proc.stdout.read()
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    return img


def adb_tap(x, y):
    """Ultra-fast tap using ADB"""
    subprocess.run(
        ["adb", "shell", "input", "tap", str(x), str(y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


# =================================================
# ------------- CLICK BY IMAGE (FAST) -------------
# =================================================
def Click_By_Image_new(path, threshold=0.86, check_interval=0.03, debug=False,_retry=0):
    """
    FAST Hybrid Image Click using ADB + OpenCV

    Input:
        path = "image_path,timeout"

    Output:
        Ok# Clicked on image 'x.png' at (x,y)
        Not Ok# Image 'x.png' not found
        Not Ok# Aborted
        ERROR: reason
    """
    try:
        global DEBUG
        DEBUG = debug

        # ---------- Parse input ----------
        parts = path.split(",", 1)
        if len(parts) != 2:
            return "Not ok# Input must be 'image_path,timeout'"

        img_path = parts[0].strip()
        timeout = float(parts[1].strip())

        if not os.path.exists(img_path):
            return f"Not ok#Image not found: {img_path}"

        if not init_driver():
            return "Not ok#Driver init failed"

        # ---------- Load template ONCE ----------
        tpl_gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if tpl_gray is None:
            return "Not ok#Failed to load image"

        th, tw = tpl_gray.shape[:2]

        start_time = time.time()

        # ---------- Main FAST loop ----------
        while True:
            # Abort support
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                return "Not ok# Aborted"

            # Ultra-fast screenshot
            screen = adb_screenshot()
            if screen is None:
                continue

            gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

            # Fast template matching
            res = cv2.matchTemplate(gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if DEBUG:
                print(f"[DEBUG] Match confidence: {max_val:.3f}")

            if max_val >= threshold:
                cx = max_loc[0] + tw // 2
                cy = max_loc[1] + th // 2

                adb_tap(cx, cy)

                return f"Ok# Clicked on image '{os.path.basename(img_path)}' at ({cx},{cy})"

            if time.time() - start_time > timeout:
                return f"Not ok# Image '{os.path.basename(img_path)}' not found"

            time.sleep(check_interval)

    # except Exception as e:
    #     return f"Not{str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Click_By_Image_new(path, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

# --- Fallback Multi-scale Template Matching ---
def multi_scale_fallback(img_path, screen_bgr, threshold=0.85, debug=False):
    try:
        gray_screen = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        tpl = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            return False, (None, None)

        best_val, best_loc, best_size = 0, None, (0, 0)

        for scale in [0.8, 0.9, 1.0, 1.1, 1.2]:
            resized_tpl = cv2.resize(tpl, (0, 0), fx=scale, fy=scale)
            result = cv2.matchTemplate(gray_screen, resized_tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best_val:
                best_val, best_loc, best_size = max_val, max_loc, resized_tpl.shape[::-1]

        if debug:
            safe_print(f"[DEBUG] Fallback multi-scale match value: {best_val:.3f}")

        if best_val >= threshold and best_loc:
            (tw, th) = best_size
            (mx, my) = best_loc
            click_x = int(mx + tw / 2)
            click_y = int(my + th / 2)
            return True, (click_x, click_y)
        else:
            return False, (None, None)

    except Exception as e:
        safe_print(f"[ERROR] Fallback matching failed: {e}")
        return False, (None, None)
    
##########################################  DTC Check #######################################
def Check_DTE_Status_Text(input):
    try:
        c1=0
        c2=0
        count=0
        cond=0
        param,timeout=input.split(",")
        param=param.lower()

        if re.search(r"km", param, re.IGNORECASE):
            cond = 1
            param = re.sub(r"(\d)(km)\b", r"\1 \2", param, flags=re.IGNORECASE)

        if re.search(r"%", param):
            param = re.sub(r"%", "", param).strip()

        elements = driver.find_elements(
            AppiumBy.XPATH,
            "//android.widget.TextView"
        )

        for i in elements:
            
            print(i.text)
            if i.text.lower() == "fuel" or i.text.lower() == "recharge" or i.text.lower() == "charge":
                c1=count+1
            if i.text.lower() == " %":
                c2=count-1
            count+=1
        
        print(f"c1:{c1} c2:{c2}")
        # Range = driver.find_element(AppiumBy.XPATH, "(//android.widget.TextView)[18]").text.lower()
        # percentage = driver.find_element(AppiumBy.XPATH, "(//android.widget.TextView)[19]").text.lower()
        Range=elements[c1].text
        percentage=elements[c2].text
        
        print(Range)
        print(percentage)
        
        capture_screenshot(temp_path)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)

        if cond==1:
            if param == Range:
                return f"Ok#DTC for {param} successfully updated on mobile+{full_path}"
            else:
                return f"Not ok#DTC for {param} is not successfully updated on mobile+{full_path}"
        else:
            if param == percentage:
                return f"Ok#DTC {param}% successfully updated on mobile+{full_path}"
            else:
                return f"Not ok#DTC {param}% is not successfully updated on mobile+{full_path}"
          
    except Exception as e:
        return f"Not ok#{str(e)}"

# init_driver()
# print(Check_DTE_Status_Text("130km,10"))

###########################################################  Compare Operation ######################################

# def Compare_Screen_By_Text(input_text, base_dir=Screenshot_path,_retry=0):
#     """
#     Take screenshot, extract text via OCR, and check if a given text is present.
#     """
#     try:
#         # Split input into text and timeout
#         param1, param2 = input_text.split(",", 1)
#         search_str = param1.strip()
#         timeout = int(param2.strip())

#         if not os.path.exists(base_dir):
#             os.makedirs(base_dir)

#         start_time = time.time()   # ✅ correct usage
#         screenshot_path = None

#         while time.time() - start_time < timeout:
#             # Screenshot captured in memory
#             png = driver.get_screenshot_as_png()
#             np_img = np.frombuffer(png, np.uint8)
#             image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

#             # Preprocessing for OCR
#             gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#             _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

#             # OCR
#             custom_config = r'--oem 3 --psm 6'
#             text = pytesseract.image_to_string(thresh, lang='eng')
           

            

    
#             # Clean OCR text
#             clean_text = re.sub(r'\s+', ' ', text)  # remove line breaks
#             clean_text = clean_text.strip()
#             print(clean_text)
#             print(search_str)

#             if search_str.lower() in clean_text.lower():
#                 print("True")

#                 # Save only when found
#                 timestamp = time.strftime("%Y%m%d_%H%M%S")
#                 screenshot_path = os.path.join(base_dir, f"screen_found_{timestamp}.png")

#                 with open(screenshot_path, "wb") as f:
#                     f.write(png)

#                 return f"Ok# Text '{search_str}' is present on screen.+{screenshot_path}"

#             sleep(0.5)

#         # Timeout reached → save last screenshot
#         timestamp = time.strftime("%Y%m%d_%H%M%S")
#         screenshot_path = os.path.join(base_dir, f"screen_timeout_{timestamp}.png")
#         driver.save_screenshot(screenshot_path)
#         if _retry <2:
#             Compare_Screen_By_Text(input_text,_retry = _retry + 1) 
#         else:
#             return f"Not Ok# Text '{search_str}' not found.+{screenshot_path}"
    
#     except Exception as e:

#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         if is_uia2_socket_error(e):
#             if _retry < 2:
#                 safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
#                 recover_uia2_session()
#                 sleep(1)
#                 return Compare_Screen_By_Text(input_text, _retry=_retry + 1)

#             return "Not ok# UIA2 session recovery failed after retries"

#         return f"Not ok# {str(e)}"

def Compare_Screen_By_Text(input_text, base_dir=Screenshot_path, _retry=0):
    """
    Take screenshot, extract text via OCR, and check if a given text is present.
    Input: "text,timeout"
    Output:
        Ok# Text '<text>' is present.+<screenshot_path>
        Not Ok# Text '<text>' not found.+<screenshot_path>
    """

    try:
        # Split input
        param1, param2 = input_text.split(",", 1)
        search_str = param1.strip()
        timeout = int(param2.strip())

        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        start_time = time.time()
        screenshot_path = None

        while time.time() - start_time < timeout:

            # Screenshot
            png = driver.get_screenshot_as_png()
            np_img = np.frombuffer(png, np.uint8)
            image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

            # OCR preprocessing
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # OCR
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(thresh, config=custom_config)
            print(text)

            # Clean OCR text
            clean_text = re.sub(r'[^\w\s]', ' ', text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

            # print("OCR:", clean_text)
            # print("Search:", search_str)

            if search_str.lower() in clean_text.lower():
                print("True")

                timestamp = time.strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(base_dir, f"screen_found_{timestamp}.png")

                with open(screenshot_path, "wb") as f:
                    f.write(png)

                return f"Ok# Text '{search_str}' is present on screen.+{screenshot_path}"

            sleep(0.5)

        # Timeout case
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(base_dir, f"screen_timeout_{timestamp}.png")
        driver.save_screenshot(screenshot_path)

        if _retry < 2:
            return Compare_Screen_By_Text(input_text, base_dir, _retry=_retry + 1)

        return f"Not Ok# Text '{search_str}' not found.+{screenshot_path}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):

            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                sleep(1)
                return Compare_Screen_By_Text(input_text, base_dir, _retry=_retry + 1)

            return "Not Ok# UIA2 session recovery failed after retries"

        return f"Not Ok# {str(e)}"    
# init_driver()
# print(Compare_Screen_By_Text("km/h,10"))

def Compare_Screen_By_Image(input_str, threshold=0.90, timeout=5, retries=3, scales=(1.0, 0.9, 1.1),_retry=0):
    """
    Robustly check if a reference image exists in the current screen.
    Uses multi-scale template matching and ORB feature matching for maximum accuracy.

    Args:
        input_str (str): "ref_image_path,timeout"
        threshold (float): Template matching threshold
        timeout (int): Time to wait before screenshot
        retries (int): Number of retries per scale
        scales (tuple): Scale factors for template matching

    Returns:
        str: Result message
    """
    

    try:
        # Parse input
        ref_path, t = input_str.split(",", 1)
        ref_path = ref_path.strip()
        timeout = int(t.strip())
        file_name = os.path.basename(ref_path).strip()
        
        new_path = str(Path(ref_path).with_name("newimage.jpg"))
        if file_name == "Connectivity.jpg":
            if app_evpv == 1:
                ref_path = str(Path(ref_path).with_name("EV_Connectivity.jpg"))


        if not init_driver():
            return "ERROR: Driver not initialized"

        # Wait for UI to stabilize
        time.sleep(timeout)

        # Capture current screenshot
        result = capture_screenshot(temp_path)
        if isinstance(result, str) and result.lower().startswith("error"):
            return f"Not ok: Failed to capture screenshot -> {result}"

        # Load images in grayscale
        ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        if ref_img is None:
            return f"Not ok: Reference image not found -> {ref_path}"
        if curr_img is None:
            return f"Not ok: Screenshot image not found -> {temp_path}"

        # Save screenshot for debug
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(Screenshot_path, f"screenshot_{timestamp}.png")
        cv2.imwrite(save_path, curr_img)

        # Check abort signal
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        # -------------------------
        # 1️⃣ Multi-scale template matching
        # -------------------------
        found = False
        max_confidence = 0
        for scale in scales:
            scaled_ref = cv2.resize(ref_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            for _ in range(retries):
                res = cv2.matchTemplate(curr_img, scaled_ref, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                max_confidence = max(max_confidence, max_val)
                if max_val >= threshold:
                    found = True
                    break
            if found:
                break

        # -------------------------
        # 2️⃣ Fallback: ORB feature matching
        # -------------------------
        if not found:
            orb = cv2.ORB_create(nfeatures=1000)
            kp1, des1 = orb.detectAndCompute(ref_img, None)
            kp2, des2 = orb.detectAndCompute(curr_img, None)
            if des1 is not None and des2 is not None:
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                matches = bf.match(des1, des2)
                matches = sorted(matches, key=lambda x: x.distance)
                good_matches = [m for m in matches if m.distance < 50]
                match_ratio = len(good_matches) / max(len(kp1), 1)
                print(f"DEBUG: ORB feature match ratio = {match_ratio:.4f}")
                if match_ratio > 0.1:  # adjustable threshold
                    found = True

        # -------------------------
        # 3️⃣ Return final result
        # -------------------------
        filename = os.path.basename(ref_path).lower()
        if filename == "connectivity.jpg" or filename == "ev_connectivity.jpg":
            return f"{'Ok# Vehicle connectivity is TRUE' if found else 'Not Ok# Vehicle connectivity is FALSE'}.+{save_path}"
        else:
            return f"{'Ok# Reference image found on screen' if found else 'Not Ok# Reference image NOT found on screen'}.+{save_path}"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
    #     return f"Not ok: Compare_Screen_By_Image failed: {str(e)}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Compare_Screen_By_Image(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"




################################################################ Scrolling Operation #######################################################################

def finger_swipe(driver, start_x, start_y, end_x, end_y, duration=800):
    """
    Perform a smooth swipe from (start_x, start_y) to (end_x, end_y)
    duration in milliseconds
    """
    try:
        driver.execute_script("mobile: swipeGesture", {
            "left": min(start_x, end_x),
            "top": min(start_y, end_y),
            "width": abs(end_x - start_x),
            "height": abs(end_y - start_y),
            "direction": "up" if end_y < start_y else "down",
            "percent": 1.0,
            "speed": duration
        })
        sleep(0.5)
    except Exception as e:
        safe_print(f"[ERROR] Finger swipe failed: {e}")


def scroll_down_continuous(driver):
    size = driver.get_window_size()
    start_x = size['width'] // 2
    start_y = int(size['height'] * 0.8)
    end_y = int(size['height'] * 0.2)
    finger_swipe(driver, start_x, start_y, start_x, end_y, duration=1000)



def take_screenshot_cv(driver):
    try:
        screenshot_base64 = driver.get_screenshot_as_base64()
        nparr = np.frombuffer(base64.b64decode(screenshot_base64), np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        safe_print(f"[ERROR] Screenshot failed: {e}")
        raise

# Scroll detection using SSIM
def is_end_of_scroll(driver, prev_screenshot, threshold=0.98):
    new_screenshot = take_screenshot_cv(driver)
    if prev_screenshot.shape != new_screenshot.shape:
        new_screenshot = cv2.resize(new_screenshot, (prev_screenshot.shape[1], prev_screenshot.shape[0]))
    grayA = cv2.cvtColor(prev_screenshot, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(new_screenshot, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(grayA, grayB, full=True)
    safe_print(f"[SSIM] Score: {score:.4f}")
    return score > threshold, new_screenshot

# Perform upward scroll
def scroll_down(driver):
    window = driver.get_window_size()
    left = window['width'] // 2
    start_y = int(window['height'] * 0.8)
    end_y = int(window['height'] * 0.3)
    driver.execute_script("mobile: swipeGesture", {
        "left": left,
        "top": end_y,
        "width": 0,
        "height": start_y - end_y,
        "direction": "up",
        "percent": 1.0
    })
    sleep(0.7)

def find_text_on_screen(driver, target_text):
    try:
        elements = driver.find_elements("xpath", "//*")
        for elem in elements:
            visible_text = elem.text.strip()
            if visible_text and target_text.lower() in visible_text.lower():
                print(f"[FOUND] '{visible_text}' contains '{target_text}'")
                return elem
        print(f"[INFO] '{target_text}' not found on current screen")
        return None
    except Exception as e:
        print(f"[ERROR] find_text_on_screen: {e}")
        return None

                                                                ############## Scroll and click by image ############

def Scroll_and_Click_Text(text_maxScrolls, threshold=0.98, scroll_pause=0.5, retry=2, debug=False,_retry=0):
    """
    Scroll and click on text element, with high confidence and low false positives.

    Args:
        text_maxScrolls (str): "target_text,max_scrolls"
        threshold (float): SSIM / similarity threshold
        scroll_pause (float): seconds to wait after each scroll
        retry (int): number of retries per scroll for detection
        debug (bool): enable debug logging

    Returns:
        str: Status + screenshot path if failed
    """
    try:

        parts = text_maxScrolls.split(",", 1)
        if len(parts) != 2:
            return "[ERROR] Input must be 'text,max_scrolls'"

        target_text = parts[0].strip()
        max_scrolls = int(parts[1].strip())

        if not init_driver():
            return "[ERROR] Appium driver initialization failed"

        prev_screenshot = take_screenshot_cv(driver)
        scroll_count = 0

        while scroll_count < max_scrolls:
            scroll_count += 1
            if debug: safe_print(f"[SCROLL] Attempt #{scroll_count}")

            for attempt in range(retry):
                elements = driver.find_elements("xpath", f"//*[@text='{target_text}']")
                best_el = None
                max_conf = 0.0

                for el in elements:
                    # Optional: measure confidence with OCR + element text
                    conf = 1.0 if el.text.strip().lower() == target_text.lower() else 0.0
                    if conf > max_conf:
                        max_conf = conf
                        best_el = el

                if best_el and max_conf >= 1.0:  # exact match
                    try:
                        best_el.click()
                        # Optional: verify click success via expected UI change
                        sleep(0.3)
                        safe_print(f"[SUCCESS] Clicked '{target_text}' after {scroll_count} scroll(s)")
                        return f"Ok# Scrolled and clicked on text '{target_text}'"
                    except Exception as click_err:
                        safe_print(f"[RETRY] Click failed: {click_err}")

                sleep(0.2)

            # Scroll down
            scroll_down_continuous(driver)
            sleep(scroll_pause)

            # Check if end of scroll reached
            end_reached, new_screenshot = is_end_of_scroll(driver, prev_screenshot, threshold)
            if debug: safe_print(f"[SSIM] Scroll#{scroll_count} EndReached: {end_reached}")
            if end_reached:
                #screenshot_path = save_screenshot("scroll_end")
                capture_screenshot(temp_path)
                curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"screenshot_{timestamp}.png"
                full_path = os.path.join(Screenshot_path, save_path)
               # Save the image
                cv2.imwrite(full_path, curr_img)
                return f"Not Ok# Text '{target_text}' not found.+{full_path}"

            prev_screenshot = new_screenshot

            # Abort check
            if os.path.exists(file_to_watch):
                try: os.remove(file_to_watch)
                except: pass
                return f"Not Ok# Aborted by abort signal"
            
        
         #screenshot_path = save_screenshot("scroll_end")
        capture_screenshot(temp_path)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)

        # screenshot_path = save_screenshot("scroll_max")
        return f"Not Ok# Text '{target_text}' not found after {max_scrolls} scrolls.+{full_path}"

    # except Exception as e:
    #     if os.path.exists(file_to_watch): 
    #         try: os.remove(file_to_watch)
    #         except: pass
    #     err_msg = f"Not ok#[ERROR] Scroll_and_Click_Text failed: {e}\n{traceback.format_exc()}"
    #     safe_print(err_msg)
    #     return err_msg

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Scroll_and_Click_Text(text_maxScrolls, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

def take_screenshot_cv_safe(driver):
    try:
        return take_screenshot_cv(driver)
    except Exception as e:
        safe_print(f"[WARN] Screenshot failed: {e}")
        return None
    

def is_end_of_scroll_safe(driver, prev_screenshot, threshold):
    try:
        if prev_screenshot is None:
            prev_screenshot = take_screenshot_cv_safe(driver)
        new_screenshot = take_screenshot_cv_safe(driver)
        if new_screenshot is None or prev_screenshot is None:
            return False, prev_screenshot
        return is_end_of_scroll(driver, prev_screenshot, threshold)
    except Exception as e:
        safe_print(f"[WARN] SSIM check failed: {e}")
        return False, prev_screenshot

def save_failed_screenshot(driver, scroll_count, label="text"):
    try:
        screenshot = take_screenshot_cv_safe(driver)
        if screenshot is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"screenshot_failed_{label}_scroll{scroll_count}_{timestamp}.png"
            full_path = os.path.join(Screenshot_path, save_path)
            cv2.imwrite(full_path, cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY))
            safe_print(f"[INFO] Failure screenshot saved: {full_path}")
    except Exception as e:
        safe_print(f"[WARN] Could not save failure screenshot: {e}")
    
def Scroll_and_Click_Image(path_maxScroll, threshold=0.98,_retry=0):
    """
    Scroll until a target image is found and click it.

    Args:
        path_maxScroll (str): "image_path,max_scrolls"
        threshold (float): SSIM threshold for end-of-scroll detection

    Returns:
        str: Ok / Not Ok / Aborted / ERROR messages with screenshot path on failure
    """
    try:
        param1, param2 = path_maxScroll.split(",", 1)
        image_path = param1.strip()
        max_scrolls = int(param2.strip())

        if not os.path.exists(image_path):
            return f"Not ok: Reference image not found: {image_path}"

        if not init_driver():
            return "ERROR: Appium driver initialization failed"

        template = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if template is None:
            return f"Not ok: Failed to read reference image: {image_path}"

        prev_screenshot = take_screenshot_cv_safe(driver)
        scroll_count = 0

        while scroll_count < max_scrolls:
            scroll_count += 1
            safe_print(f"[SCROLL] Attempt #{scroll_count}")

            # Take current screenshot
            screenshot = take_screenshot_cv_safe(driver)
            if screenshot is None:
                safe_print("[WARN] Failed to capture screenshot, retrying scroll...")
                scroll_down_continuous(driver)
                sleep(0.5)
                continue

            # Try to find template
            pos = find_template_in_screenshot(screenshot, template, threshold)
            if pos:
                try:
                    driver.execute_script("mobile: clickGesture", {"x": pos[0], "y": pos[1]})
                    safe_print(f"[SUCCESS] Clicked on image after {scroll_count} scroll(s)")
                    return f"Ok# Clicked on target image after {scroll_count} scroll(s)"
                except Exception as click_err:
                    return f"Not ok: Click gesture failed on '{image_path}': {click_err}"

            # Scroll down
            scroll_down_continuous(driver)
            sleep(0.5)

            # Check if end of scroll is reached
            end_reached, new_screenshot = is_end_of_scroll_safe(driver, prev_screenshot, threshold)
            safe_print(f"[SSIM] Scroll#{scroll_count} EndReached: {end_reached}")
            if end_reached:
                save_failed_screenshot(driver, scroll_count, label="image")
                return f"Not Ok# Target image not found after {scroll_count} scroll(s)+screenshot_saved"

            prev_screenshot = new_screenshot

            # Abort check
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                save_failed_screenshot(driver, scroll_count, label="image")
                return f"Not Ok# Aborted by abort signal+screenshot_saved"

        save_failed_screenshot(driver, scroll_count, label="image")
        return f"Not Ok# Target image not found after {max_scrolls} scroll(s)+screenshot_saved"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
    #     return f"Not ok: Scroll_and_Click_Image failed: {str(e)}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Scroll_and_Click_Image(path_maxScroll, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

def Scroll(input_str):
    """
    LabVIEW-compatible single scroll function.
    Input: 'up', 'down', 'left', or 'right'
    Output: Single string with status
    """
    try:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        param1, param2 = input_str.split(",", 1)
        direction = param1.strip().lower()
        duration = 800  # default duration in ms

        if direction not in ['up', 'down', 'left', 'right']:
            return f"[ERROR] Invalid direction: {direction}"

        if not init_driver():
            return "[ERROR] Appium driver initialization failed"

        size = driver.get_window_size()
        width = size['width']
        height = size['height']

        if direction == 'up':
            start_x, start_y = width // 2, int(height * 0.8)
            end_x, end_y = start_x, int(height * 0.2)
        elif direction == 'down':
            start_x, start_y = width // 2, int(height * 0.2)
            end_x, end_y = start_x, int(height * 0.8)
        elif direction == 'left':
            start_x, start_y = int(width * 0.8), height // 2
            end_x, end_y = int(width * 0.2), start_y
        elif direction == 'right':
            start_x, start_y = int(width * 0.2), height // 2
            end_x, end_y = int(width * 0.8), start_y

        driver.execute_script("mobile: swipeGesture", {
            "left": min(start_x, end_x),
            "top": min(start_y, end_y),
            "width": abs(end_x - start_x) or 1,
            "height": abs(end_y - start_y) or 1,
            "direction": direction,
            "percent": 1.0,
            "speed": duration
        })
        sleep(0.5)
        return f"Ok#Scrolled"

    except Exception as e:
        return f"Not ok:scroll failed: {str(e)}"

############################################################ Tap using coordinates ########################################################

def Click_By_Coordinates(coord_string,_retry=0):
    """
    Clicks on the screen at specified coordinates.

    Args:
        coord_string (str): "x_y,timeout" (timeout is ignored but parsed for consistency)

    Returns:
        str: "Ok# Clicked at coordinates (x, y)"
             "Not Ok# Invalid input or driver not initialized"
             "Not Ok# Aborted by abort signal"
             "Not ok# <details>"
    """
    try:
        param1, param2 = coord_string.split(",", 1)  # timeout ignored for now

        # Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        # Attempt driver recovery if needed
        if driver is None or not is_driver_alive():
            init_result = init_driver()
            if not init_result.startswith("PASS"):
                return "Not Ok# Driver not initialized"

        # Parse input coordinates: "x_y"
        parts = param1.split('_')
        if len(parts) != 2:
            return "Not Ok# Invalid coordinate format"

        x = int(parts[0].strip())
        y = int(parts[1].strip())

        driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
        return f"Ok# Clicked at coordinates ({x}, {y})"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
    #     return f"Not ok: Click_By_Coordinate failed: {str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Click_By_Coordinates(coord_string, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    

def Click_By_Coordinates_new(coord_string,_retry=0):
    """
    Robust & fail-safe coordinate click.

    Input:
        "x_y,timeout"

    Output:
        Ok# Clicked at coordinates (x, y)
        Not Ok# Aborted by abort signal
        Not Ok# Invalid coordinate input
        Not Ok# Driver not initialized
        ERROR# <details>
    """

    try:
        # -----------------------------
        # Abort check (early exit)
        # -----------------------------
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        # -----------------------------
        # Input parsing (safe)
        # -----------------------------
        try:
            coord_part, _ = coord_string.split(",", 1)
            x_str, y_str = coord_part.split("_", 1)
            x = int(x_str.strip())
            y = int(y_str.strip())
        except:
            return "Not Ok# Invalid coordinate input"

        # -----------------------------
        # Driver recovery
        # -----------------------------
        try:
            if driver is None or not is_driver_alive():
                init_result = init_driver()
                if not str(init_result).startswith("PASS"):
                    return "Not Ok# Driver not initialized"
        except:
            return "Not Ok# Driver not initialized"

        # -----------------------------
        # Screen bounds protection
        # -----------------------------
        try:
            size = driver.get_window_size()
            max_x = size.get("width", 0) - 1
            max_y = size.get("height", 0) - 1

            # Clamp coordinates
            x = max(0, min(x, max_x))
            y = max(0, min(y, max_y))
        except:
            pass  # Never fail because of screen info

        # -----------------------------
        # Abort check (before action)
        # -----------------------------
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        # -----------------------------
        # PRIMARY CLICK (W3C action)
        # -----------------------------
        try:
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput

            finger = PointerInput(PointerInput.TOUCH, "finger")
            actions = ActionBuilder(driver, mouse=finger)
            actions.pointer_action.move_to_location(x, y)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pointer_up()
            actions.perform()

            return f"Ok# Clicked at coordinates ({x}, {y})"

        except Exception as w3c_err:
            safe_print(f"[W3C CLICK FAILED] {w3c_err}")

        # -----------------------------
        # FALLBACK 1️⃣ Appium mobile gesture
        # -----------------------------
        try:
            driver.execute_script(
                "mobile: clickGesture",
                {"x": x, "y": y}
            )
            return f"Ok# Clicked at coordinates ({x}, {y})"
        except Exception as mobile_err:
            safe_print(f"[MOBILE CLICK FAILED] {mobile_err}")

        # -----------------------------
        # FALLBACK 2️⃣ TouchAction (legacy)
        # -----------------------------
        try:
            from appium.webdriver.common.touch_action import TouchAction
            TouchAction(driver).tap(x=x, y=y).perform()
            return f"Ok# Clicked at coordinates ({x}, {y})"
        except Exception as touch_err:
            safe_print(f"[TOUCH ACTION FAILED] {touch_err}")

        # -----------------------------
        # FINAL FAILURE
        # -----------------------------
        return f"Not Ok# Unable to click at ({x}, {y})"

    # except Exception as e:
    #     # Absolute safety net
    #     try:
    #         if os.path.exists(file_to_watch):
    #             os.remove(file_to_watch)
    #     except:
    #         pass
    #     return f"ERROR# Click_By_Coordinates failed: {str(e)}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Click_By_Coordinates_new(coord_string, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    
def Detect_Date_Time_No_Text():
    """
    Dynamically detects Date & Time input fields even if '/' or ':' is NOT visible.

    Detection logic:
    - Clickable containers
    - content-desc / resource-id keywords
    - Icon proximity
    - Screen order (top → bottom)

    Returns:
        list of dicts:
        [
          {"type": "date", "x": x, "y": y},
          {"type": "time", "x": x, "y": y}
        ]
        OR {"ERROR": "<reason>"}
    """

    results = []

    try:
        elements = driver.find_elements(By.XPATH, "//*")
        candidates = []

        for el in elements:
            try:
                rect = el.rect
                if rect["width"] <= 0 or rect["height"] <= 0:
                    continue

                x = rect["x"] + rect["width"] // 2
                y = rect["y"] + rect["height"] // 2

                text = (el.text or "").lower()
                desc = (el.get_attribute("content-desc") or "").lower()
                res_id = (el.get_attribute("resource-id") or "").lower()
                clickable = el.get_attribute("clickable") == "true"

                combined = f"{text} {desc} {res_id}"

                # -----------------------------
                # DATE detection
                # -----------------------------
                if clickable and any(k in combined for k in ["date", "calendar"]):
                    candidates.append({
                        "type": "date",
                        "x": x,
                        "y": y
                    })
                    continue

                # -----------------------------
                # TIME detection
                # -----------------------------
                if clickable and any(k in combined for k in ["time", "clock"]):
                    candidates.append({
                        "type": "time",
                        "x": x,
                        "y": y
                    })
                    continue

            except:
                continue

        # -----------------------------
        # Sort top → bottom
        # -----------------------------
        candidates.sort(key=lambda i: i["y"])

        if not candidates:
            return {"ERROR": "No date/time inputs detected"}

        return candidates

    except Exception as e:
        return {"ERROR": f"Detect_Date_Time_No_Text failed: {str(e)}"}
    
def Click_Date_Time_By_Index_Text(input,_retry=0):
    """
    Clicks a dynamically detected Date/Time input field by index.

    Detection:
        Uses Detect_Date_Time_No_Text() (top → bottom order)

    Indexing:
        0 -> first detected (topmost)
        1 -> second detected
        ...

    Returns:
        Ok# Clicked <type> at (x, y)
        Not Ok# Invalid index
        Not Ok# Detection failed
        Not Ok# Aborted by abort signal
        ERROR# <details>
    """

    try:
        index,timeout=input.split(",")
        index=int(index)
        # -----------------------------
        # Abort check
        # -----------------------------
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        # -----------------------------
        # Detect date/time dynamically
        # -----------------------------
        detected = Detect_Date_Time_No_Text()

        if isinstance(detected, dict) and "ERROR" in detected:
            return f"Not Ok# Detection failed: {detected['ERROR']}"

        if not isinstance(detected, list) or not detected:
            return "Not Ok# No date/time inputs detected"

        # -----------------------------
        # Index validation
        # -----------------------------
        if index < 0 or index >= len(detected):
            return f"Not Ok# Invalid index {index}"

        # -----------------------------
        # Get coordinates
        # -----------------------------
        target = detected[index]
        x = target.get("x")
        y = target.get("y")
        field_type = target.get("type", "unknown")

        if x is None or y is None:
            return "Not Ok# Invalid coordinates"

        # -----------------------------
        # Click by coordinates (your existing function)
        # -----------------------------
        result = Click_By_Coordinates(f"{x}_{y},5")

        if result.startswith("Ok"):
            return f"Ok# Clicked {field_type} input at ({x}, {y})"

        return result

    # except Exception as e:
    #     try:
    #         if os.path.exists(file_to_watch):
    #             os.remove(file_to_watch)
    #     except:
    #         pass
    #     return f"ERROR# Click_Date_Time_By_Index failed: {str(e)}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Click_Date_Time_By_Index_Text(input, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"



# init_driver()
# print(Click_Date_Time_By_Index_Text("0,10"))
# init_driver()
# print(Click_By_Coordinates("540_897,10"))
# init_driver()
# print(Click_By_Coordinates("854_219,10"))

def Click_Dynamically_By_Index_Text(coord_string,_retry=0):
    """
    Clicks on the screen at specified coordinates.

    Args:
        coord_string (str): "x_y,timeout" (timeout is ignored but parsed for consistency)

    Returns:
        str: "Ok# Clicked at coordinates (x, y)"
             "Not Ok# Invalid input or driver not initialized"
             "Not Ok# Aborted by abort signal"
             "Not ok# <details>"
    """
    try:
        index, param2 = coord_string.split(",", 1)  # timeout ignored for now
        index=int(index)

        # Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        # Attempt driver recovery if needed
        if driver is None or not is_driver_alive():
            init_result = init_driver()
            if not init_result.startswith("PASS"):
                return "Not Ok# Driver not initialized"

        # Parse input coordinates: "x_y"

        # parts = param1.split('_')
        # if len(parts) != 2:
        #     return "Not Ok# Invalid coordinate format"

        # x = int(parts[0].strip())
        # y = int(parts[1].strip())
        coordinates=get_date_time_points()
        print(coordinates)
        x=int(coordinates[index][0])
        y=int(coordinates[index][1])
        print(x)
        print(y)

        driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
        return f"Ok# Clicked at coordinates ({x}, {y})"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Click_Dynamically_By_Index_Text(coord_string, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

# init_driver()
# # print(Click_Dynamically_By_Index_Text("2,10"))
# print(get_all_field_centers())


                                                    ######### Realtime coordinates ############


def get_touch_range():
    output = subprocess.check_output(['adb', 'shell', 'getevent', '-p'], universal_newlines=True)
    x_range = y_range = None
    for line in output.splitlines():
        if 'ABS_MT_POSITION_X' in line or '0035' in line:
            x_range = list(map(int, re.findall(r'min (\b+)y max (\d+)', line)[0]))
        elif 'ABS_MT_POSITION_Y' in line or '0036' in line:
            y_range = list(map(int, re.findall(r'min (\d+), max (\d+)', line)[0]))
    return x_range, y_range

def get_screen_resolution():
    output = subprocess.check_output(['adb', 'shell', 'wm', 'size'], universal_newlines=True)
    match = re.search(r'Physical size: (\d+)x(\d+)', output)
    return int(match.group(1)), int(match.group(2))

def map_raw_to_pixel(raw_x, raw_y, x_range, y_range, screen_width, screen_height):
    min_x, max_x = x_range
    min_y, max_y = y_range
    pixel_x = int((raw_x - min_x) / (max_x - min_x) * screen_width)
    pixel_y = int((raw_y - min_y) / (max_y - min_y) * screen_height)
    return pixel_x, pixel_y

def start_touch_logger(file_path="touch_coordinates.txt"):
    x_range, y_range = get_touch_range()
    screen_width, screen_height = get_screen_resolution()
    print(f"[INFO] Logging to {file_path}...")

    process = subprocess.Popen(['adb', 'shell', 'getevent', '-lt'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    x = y = None
    try:
        for line in process.stdout:
            match_x = re.search(r'(ABS_MT_POSITION_X|0035)\s+([0-9a-fA-F]+)', line)
            match_y = re.search(r'(ABS_MT_POSITION_Y|0036)\s+([0-9a-fA-F]+)', line)

            if match_x:
                x = int(match_x.group(2), 16)
            if match_y:
                y = int(match_y.group(2), 16)

            if x is not None and y is not None:
                px, py = map_raw_to_pixel(x, y, x_range, y_range, screen_width, screen_height)
                timestamp = datetime.now().strftime('%H:%M:%S')
                with open(file_path, "w") as f:
                    f.write(f"{px},{py},{timestamp}")
                x = y = None
    except KeyboardInterrupt:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        print("[STOPPED] Touch listener stopped.")
    finally:
        process.terminate()

def get_version():
    return sys.version

############################################### Input Operation ###################################################


def Send_Inputs_Old(text,_retry=0):
    """
    Sends input text to the appropriate EditText field(s) on the screen.

    Args:
        text (str): "key:value,timeout" or just "value,timeout" if only one input field

    Returns:
        str: "Ok# Input sent successfully"
             "Not Ok# Input field not found within timeout"
             "Not Ok# Aborted by abort signal"
             "Not ok# <details>"
    """
    try:
         
        # Extract params
        parts = text.split(",", 1)
        if len(parts) == 2:
            param, timeout = parts[0].strip(), int(parts[1].strip())
        else:
            param, timeout = parts[0].strip(), 10  # default timeout

        key, value = (None, None)
        if ":" in param:
            key, value = param.split(":", 1)
            key, value = key.strip(), value.strip()
        else:
            value = param  # only value case

        # Ensure driver is ready
        if not init_driver():
            return "Not ok# Driver not initialized"

        start_time = time.time()
        while time.time() - start_time < timeout:
            # ✅ Abort check
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                return "Not Ok# Aborted by abort signal"

            try:
                input_fields = driver.find_elements("xpath", "//android.widget.EditText")

                # Case 1: Only one input field
                if len(input_fields) == 1 and value:
                    el = input_fields[0]
                    el.clear()
                    el.send_keys(value)
                    return f"Ok# Input '{value}' sent to the only input field"

                # Case 2: Multiple input fields with key
                if key:
                    try:
                        el = driver.find_element("accessibility id", key)
                    except:
                        try:
                            el = driver.find_element("id", key)
                        except:
                            try:
                                el = driver.find_element(
                                    "xpath", f"//android.widget.EditText[@text='{key}']"
                                )
                            except:
                                el = None

                    if el:
                        el.clear()
                        el.send_keys(value)
                        return f"Ok# Input '{value}' sent to field '{key}'"

            except Exception as inner:
                safe_print(f"[LOOP ERROR] {inner}")

            sleep(1)
        
        capture_screenshot(temp_path)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)

        # Timeout reached
        if _retry<2:
            Send_Inputs(text,_retry=_retry + 1)
        else:
            return f"Not Ok# Input field not found+{full_path}"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
    #     return f"Not ok: Send_Inputs failed: {str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Send_Inputs(text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"


# def Send_Inputs(text,_retry=0):
#     """
#     Sends input text to the appropriate EditText field(s) on the screen.

#     Args:
#         text (str): "key:value,timeout" or just "value,timeout" if only one input field

#     Returns:
#         str: "Ok# Input sent successfully"
#              "Not Ok# Input field not found within timeout"
#              "Not Ok# Aborted by abort signal"
#              "Not ok# <details>"
#     """
#     try:
         
#         # Extract params
#         parts = text.split(",", 1)
#         if len(parts) == 2:
#             param, timeout = parts[0].strip(), int(parts[1].strip())
#         else:
#             param, timeout = parts[0].strip(), 10  # default timeout

#         key, value = (None, None)
#         if ":" in param:
#             key, value = param.split(":", 1)
#             key, value = key.strip(), value.strip()
#         else:
#             value = param  # only value case

#         # Ensure driver is ready
#         if not init_driver():
#             return "Not ok# Driver not initialized"
        
#         # input_fields = driver.find_elements("xpath", "//android.widget.EditText")
#         input_fields = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
    

#         start_time = time.time()
#         while time.time() - start_time < timeout:
#             # ✅ Abort check
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Not Ok# Aborted by abort signal"

#             try:
#                 print(len(input_fields))

#                 # Case 1: Only one input field
#                 if len(input_fields) == 1 and value:
#                     el = input_fields[0]
#                     el.clear()
#                     el.send_keys(value)
#                     return f"Ok# Input '{value}' sent to the only input field"

#                 # Case 2: Multiple input fields with key
#                 if key:
#                     try:
#                         el = driver.find_element("accessibility id", key)
#                     except:
#                         try:
#                             el = driver.find_element("id", key)
#                         except:
#                             try:
#                                 el = driver.find_element(
#                                     "xpath", f"//android.widget.EditText[@text='{key}']"
#                                 )
#                             except:
#                                 el = None

#                     if el:
#                         el.clear()
#                         el.send_keys(value)
#                         return f"Ok# Input '{value}' sent to field '{key}'"

#             except Exception as inner:
#                 safe_print(f"[LOOP ERROR] {inner}")

#             sleep(0.2)
        


#         # Timeout reached
#         if _retry<2:
#             Send_Inputs(text,_retry=_retry + 1)
#         else:
#             capture_screenshot(temp_path)
#             curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             save_path = f"screenshot_{timestamp}.png"
#             full_path = os.path.join(Screenshot_path, save_path)
#             # Save the image
#             cv2.imwrite(full_path, curr_img)

#             return f"Not Ok# Input field not found+{full_path}"

#     # except Exception as e:
#     #     if os.path.exists(file_to_watch):
#     #         os.remove(file_to_watch)
#     #     return f"Not ok: Send_Inputs failed: {str(e)}"
#     except Exception as e:

#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         if is_uia2_socket_error(e):
#             if _retry < 2:
#                 safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
#                 recover_uia2_session()
#                 sleep(1)
#                 return Send_Inputs(text, _retry=_retry + 1)

#             return "Not ok# UIA2 session recovery failed after retries"

#         return f"Not ok# {str(e)}"
    

def Send_Inputs(text, _retry=0):
    try:
        # Extract params
        parts = text.split(",", 1)
        if len(parts) == 2:
            param, timeout = parts[0].strip(), int(parts[1].strip())
        else:
            param, timeout = parts[0].strip(), 10

        key, value = (None, None)
        if ":" in param:
            key, value = param.split(":", 1)
            key, value = key.strip(), value.strip()
        else:
            value = param

        if not init_driver():
            return "Not ok# Driver not initialized"

        start_time = time.time()

        while time.time() - start_time < timeout:

            # Abort check
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                return "Not Ok# Aborted by abort signal"

            try:
                # 🔴 Fetch elements INSIDE loop
                input_fields = driver.find_elements(
                    AppiumBy.CLASS_NAME, "android.widget.EditText"
                )

                print("Input fields found:", len(input_fields))

                # Case 1: Single field
                if len(input_fields) == 1 and value:
                    print("Hello")
                    el = input_fields[0]
                    el.clear()
                    el.send_keys(value)
                    return f"Ok# Input '{value}' sent to the only input field"

                # Case 2: Multiple fields with key
                if key:
                    el = None

                    try:
                        el = driver.find_element("accessibility id", key)
                    except:
                        try:
                            el = driver.find_element("id", key)
                        except:
                            try:
                                el = driver.find_element(
                                    "xpath",
                                    f"//android.widget.EditText[@text='{key}']",
                                )
                            except:
                                pass

                    if el:
                        el.clear()
                        el.send_keys(value)
                        return f"Ok# Input '{value}' sent to field '{key}'"

            except Exception as inner:
                safe_print(f"[LOOP ERROR] {inner}")

            sleep(0.3)

        # Timeout reached
        if _retry < 2:
            return Send_Inputs(text, _retry=_retry + 1)

        capture_screenshot(temp_path)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)

        cv2.imwrite(full_path, curr_img)

        return f"Not Ok# Input field not found+{full_path}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                sleep(1)
                return Send_Inputs(text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    
# init_driver()
# print(Send_Inputs("Mobile number:2580,10"))

# init_driver()
# for i in range(30):
#     Swipe_From_Right_Edge("dummy")
#     Send_Inputs("Mobile number:2580,10")

########################################### Swipe Operation ##############################################

def Swipe_From_Left_Edge(text,_retry=0):
    """
    Performs a left-edge swipe to the right.

    Args:
        text (str): "param,timeout" format (timeout is ignored here)

    Returns:
        str: "Ok" / "Not Ok# Aborted by abort signal" / "Not ok# <details>"
    """
    try:
        # Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        param1, _ = text.split(",", 1)

        # Get screen dimensions
        size = driver.get_window_size()
        width = size["width"]
        height = size["height"]

        # Edge swipe parameters (left edge swipe right)
        start_x = 5
        end_x = int(width * 0.2)
        y = int(height / 2)

        # Perform swipe gesture
        driver.execute_script("mobile: swipeGesture", {
            "left": start_x,
            "top": y - 50,
            "width": end_x - start_x,
            "height": 100,
            "direction": "right",
            "percent": 0.75
        })

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        return "Ok#Swiped from left edge"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
    #     return f"Not ok: Swipe_From_Left_Edge failed: {str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Swipe_From_Left_Edge(text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"



def Swipe_From_Right_Edge(text,_retry=0):
    try:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        param1, param2 = text.split(",", 1)
        # Get screen dimensions
        size = driver.get_window_size()
        width = size["width"]
        height = size["height"]

        # Edge swipe from right to left
        start_x = int(width * 0.8)  # Near right edge
        end_x = width - 5           # Very right edge
        y = int(height / 2)

        # Perform swipe gesture
        driver.execute_script("mobile: swipeGesture", {
            "left": start_x,
            "top": y - 50,
            "width": end_x - start_x,
            "height": 100,
            "direction": "left",
            "percent": 0.75
        })

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            

        return "Ok#Swiped from right edge"

    # except Exception as e:
    #     if os.path.exists(file_to_watch):
    #         os.remove(file_to_watch)
            
    #     return f"Not ok:Swipe from right edge failed: {str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Swipe_From_Right_Edge(text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

# init_driver()
# Swipe_From_Right_Edge("text,1")


# print(init_driver())
# for i in range(30):
#     Restart_App_Package_Name_Text("tata motors ira 2.0,10")
#     Send_Inputs("Mobile number:1234,10")
#     sleep(5)

################################################# SCREENSHOT ############################################



def NSS(path):
    
    try:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        param1, param2 = path.split(",", 1)
        filepath = param1
        if driver is None:
            return "Not ok# Driver is not initialized"

        if is_flag_secure():
            return "SKIPPED: FLAG_SECURE screen blocks screenshot"
        
        driver.open_notifications()
        print("Opened notification.....")
        sleep(3)
        

        # Step 1: Save PNG
        png_path = filepath.replace(".jpg", ".png")
        driver.get_screenshot_as_file(png_path)
        print("Screenshot taken.....")
        driver.press_keycode(4)

        # Step 2: Convert to JPG
        Image.open(png_path).convert("RGB").save(filepath, "JPEG")
        print("Convert.....")
        # Step 3: Remove PNG
        os.remove(png_path)
        print("Image removed.....")

        return filepath

    except WebDriverException as e:
        return f"Not ok: Screenshot error\n{str(e)}"
    except Exception:
        return f"Not ok: Unknown error\n{traceback.format_exc()}"


def SS(path):
    
    try:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        param1, param2 = path.split(",", 1)
        filepath = param1
        if driver is None:
            return "Not ok#Driver is not initialized"

        if is_flag_secure():
            return "Not ok#FLAG_SECURE screen blocks screenshot"

        # Step 1: Save PNG
        png_path = filepath.replace(".jpg", ".png")
        driver.get_screenshot_as_file(png_path)
        #print("Screenshot taken.....")

        # Step 2: Convert to JPG
        Image.open(png_path).convert("RGB").save(filepath, "JPEG")
        print("Convert.....")
        # Step 3: Remove PNG
        os.remove(png_path)
        print("Image removed.....")

        return filepath

    except WebDriverException as e:
        return f"Not ok: Screenshot error\n{str(e)}"
    except Exception:
        return f"Not ok: Unknown error\n{traceback.format_exc()}"

# init_driver()
# print(SS("D:\\MEP00179\Sourcecode-09-06-2025\\Sourcecode\\Configuration_Files\\Appium\\Test Screenshots\\Test_05_09_25__19_56_54\\ss.png,10"))

def safe_screenshot(filepath):
    global driver
    try:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if driver is None:
            init_result = init_driver()
            if not init_result.startswith("PASS"):
                return init_result

        if is_flag_secure():
            return "Not ok#FLAG_SECURE screen blocks screenshot"

        # Step 1: Save temporary PNG
        png_path = filepath.replace(".jpg", ".png")
        driver.get_screenshot_as_file(png_path)

        # Step 2: Convert to JPG
        image = Image.open(png_path).convert("RGB")
        image.save(filepath, "JPEG")

        # Step 3: Optionally remove the PNG
        os.remove(png_path)

        return filepath  # return JPG path
    except WebDriverException as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if "instrumentation" in str(e) or "proxy" in str(e) or "socket hang up" in str(e):
            restart_result = restart_everything()
            if not restart_result.startswith("PASS"):
                return f"Not ok: Restart failed\n{restart_result}"
            try:
                if is_flag_secure():
                    return "Not ok#FLAG_SECURE after restart"

                # Same logic after restart
                png_path = filepath.replace(".jpg", ".png")
                driver.get_screenshot_as_file(png_path)
                image = Image.open(png_path).convert("RGB")
                image.save(filepath, "JPEG")
                os.remove(png_path)

                return filepath
            except Exception as retry_error:
                return f"Not ok#Retry failed\n{str(retry_error)}"
        return f"Not ok#Screenshot error\n{str(e)}"
    except Exception as ex:
        return f"Not ok#Unknown error\n{traceback.format_exc()}"


##########################################################################################################

# def Swipe_Up(input,_retry=0):
#     """
#     Perform a single swipe up gesture.

#     Args:
#         duration (int): Duration of the swipe in ms (default 800)

#     Returns:
#         str: "Ok# Swiped up"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <details>"
#     """
#     try:
#         # ✅ Abort check
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#             return "Not Ok# Aborted by abort signal"

#         size = driver.get_window_size()
#         width, height = size["width"], size["height"]

#         start_x = width // 2
#         start_y = int(height * 0.90)  # bottom
#         end_y   = int(height * 0.60)  # drag up

#         driver.swipe(start_x, start_y, start_x, end_y, 800)
#         return "Ok#Swiped up"

#     except Exception as e:

#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         if is_uia2_socket_error(e):
#             if _retry < 2:
#                 safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
#                 recover_uia2_session()
#                 sleep(1)
#                 return Swipe_Up(input, _retry=_retry + 1)

#             return "Not ok# UIA2 session recovery failed after retries"

#         return f"Not ok# {str(e)}"





def _get_page_signature():
    """
    Create a lightweight signature of current screen state.
    Used to detect whether swipe caused any UI movement.
    """
    try:
        src = driver.page_source
        return hashlib.md5(src.encode("utf-8")).hexdigest()
    except Exception:
        return None


def _abort_requested():
    try:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return True
    except Exception:
        pass
    return False


def _safe_window_size():
    size = driver.get_window_size()
    return size["width"], size["height"]


def _perform_swipe_w3c(start_x, start_y, end_x, end_y, duration_ms=500):
    """
    Perform swipe using W3C actions.
    More reliable than legacy driver.swipe().
    """

    finger = PointerInput(interaction.POINTER_TOUCH, "finger")
    actions = ActionBuilder(driver, mouse=finger)
    pa = actions.pointer_action

    pa.move_to_location(start_x, start_y)
    pa.pointer_down()
    pa.pause(duration_ms / 1000.0)
    pa.move_to_location(end_x, end_y)
    pa.release()

    actions.perform()


def _perform_swipe_mobile(start_x, start_y, end_x, end_y, duration_ms=500):
    """
    Fallback using Appium mobile gesture.
    """
    driver.execute_script("mobile: swipeGesture", {
        "left": min(start_x, end_x),
        "top": min(start_y, end_y),
        "width": abs(end_x - start_x) or 5,
        "height": abs(end_y - start_y) or 5,
        "direction": "up",
        "percent": 0.75
    })


def _perform_swipe_legacy(start_x, start_y, end_x, end_y, duration_ms=500):
    """
    Last fallback.
    """
    driver.swipe(start_x, start_y, end_x, end_y, duration_ms)


def _do_single_swipe(start_x, start_y, end_x, end_y, duration_ms=500):
    """
    Try best swipe method first, then fall back.
    """
    last_error = None

    # 1) W3C action
    try:
        _perform_swipe_w3c(start_x, start_y, end_x, end_y, duration_ms)
        return True, "W3C swipe success"
    except Exception as e:
        last_error = e

    # 2) mobile: swipeGesture
    try:
        _perform_swipe_mobile(start_x, start_y, end_x, end_y, duration_ms)
        return True, "mobile:swipeGesture success"
    except Exception as e:
        last_error = e

    # 3) legacy swipe
    try:
        _perform_swipe_legacy(start_x, start_y, end_x, end_y, duration_ms)
        return True, "legacy swipe success"
    except Exception as e:
        last_error = e

    return False, str(last_error)


def Swipe_Up(input="", _retry=0, verify_change=True):
    """
    Robust swipe up that works across different screen types.

    Returns:
        Ok#Swiped up
        Ok#Swiped up (page changed)
        Not Ok# Aborted by abort signal
        Not Ok# Swipe executed but no visible movement detected
        Not Ok# UIA2 session recovery failed after retries
        Not Ok# <error>
    """
    try:
        # Abort
        if _abort_requested():
            return "Not Ok# Aborted by abort signal"

        width, height = _safe_window_size()
        center_x = width // 2

        before_sig = _get_page_signature() if verify_change else None

        """
        Multiple swipe profiles:
        - conservative: avoids system gesture regions
        - medium: general purpose
        - aggressive: stronger upward scroll
        - left/right variants: useful when center is blocked
        """
        swipe_profiles = [
            # ultra small center swipe (primary)
            (center_x, int(height * 0.78), center_x, int(height * 0.84), 180),

            # even smaller (micro control)
            (center_x, int(height * 0.76), center_x, int(height * 0.83), 160),

            # tiny flick (fast)
            (center_x, int(height * 0.75), center_x, int(height * 0.82), 140),

            # left side micro swipe
            (int(width * 0.40), int(height * 0.78), int(width * 0.40), int(height * 0.74), 180),

            # right side micro swipe
            (int(width * 0.60), int(height * 0.78), int(width * 0.60), int(height * 0.74), 180),
        ]

        last_reason = "Swipe not attempted"

        for idx, (sx, sy, ex, ey, dur) in enumerate(swipe_profiles, start=1):
            if _abort_requested():
                return "Not Ok# Aborted by abort signal"

            try:
                ok, reason = _do_single_swipe(sx, sy, ex, ey, dur)
                last_reason = f"Profile {idx}: {reason}"

                if not ok:
                    continue

                time.sleep(0.8)

                if verify_change:
                    after_sig = _get_page_signature()
                    if before_sig is None or after_sig is None:
                        return f"Ok#Swiped up ({reason})"

                    if after_sig != before_sig:
                        return f"Ok#Swiped up ({reason}, page changed)"

                    # If no change, try next profile
                else:
                    return f"Ok#Swiped up ({reason})"

            except Exception as inner_e:
                last_reason = f"Profile {idx} failed: {str(inner_e)}"

                if is_uia2_socket_error(inner_e):
                    if _retry < 2:
                        safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                        recover_uia2_session()
                        time.sleep(1)
                        return Swipe_Up(input=input, _retry=_retry + 1, verify_change=verify_change)

                    return "Not Ok# UIA2 session recovery failed after retries"

        return f"Not Ok# Swipe executed but no visible movement detected. Last attempt: {last_reason}"

    except Exception as e:
        if _abort_requested():
            return "Not Ok# Aborted by abort signal"

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                time.sleep(1)
                return Swipe_Up(input=input, _retry=_retry + 1, verify_change=verify_change)

            return "Not Ok# UIA2 session recovery failed after retries"

        return f"Not Ok# {str(e)}"



def Swipe_Down(input):
    """
    Perform a single swipe down gesture.

    Args:
        duration (int): Duration of the swipe in ms (default 800)

    Returns:
        str: "Ok# Swiped down"
             "Not Ok# Aborted by abort signal"
             "ERROR: <details>"
    """
    try:
        # ✅ Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        size = driver.get_window_size()
        width, height = size["width"], size["height"]

        start_x = width // 2
        start_y = int(height * 0.85)  # higher up .60
        end_y   = int(height * 0.15)  # bottom .90

        driver.swipe(start_x, start_y, start_x, end_y, 800)
        return "Ok#Swiped down"

    except Exception as e:
        return f"Not ok#{str(e)}"
    
# def swipe_up():
#     size = driver.get_window_size()
#     x = size["width"] // 2
#     driver.execute_script(
#         "mobile: dragGesture",
#         {
#             "startX": x,
#             "startY": int(size["height"] * 0.85),
#             "endX": x,
#             "endY": int(size["height"] * 0.15),
#             "duration": 400
#         }
#     )
#     return "Ok#Swipe up performed"
def Click_Text_And_Swipe_up(input_str):
    try:
        # Parse input
        text, timeout = input_str.split(",")
        text = text.strip()
        timeout = int(timeout)

        end_time = time.time() + timeout
        el = None

        # Try finding element with scroll
        while time.time() < end_time:
            try:
                el = driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().textContains("{text}")'
                )
                break
            except:
                # Scroll up if not found
                driver.execute_script(
                    "mobile: swipeGesture",
                    {
                        "left": 100,
                        "top": 800,
                        "width": 500,
                        "height": 800,
                        "direction": "up",
                        "percent": 0.6
                    }
                )
                time.sleep(0.5)

        if el is None:
            return f"Not ok#Text not found: {text}"

        # Get element center
        rect = el.rect
        start_x = rect["x"] + rect["width"] // 2
        start_y = rect["y"] + rect["height"] // 2

        # Click
        driver.execute_script(
            "mobile: clickGesture",
            {"x": start_x, "y": start_y}
        )

        time.sleep(0.2)

        # Swipe up from element
        end_y = int(start_y * 0.3)

        driver.execute_script(
            "mobile: dragGesture",
            {
                "startX": start_x,
                "startY": start_y,
                "endX": start_x,
                "endY": end_y,
                "duration": 400
            }
        )

        return "Ok#Clicked text and swiped up"

    except Exception as e:
        return f"Not ok#{str(e)}"


# init_driver()
# Click_Text_And_Swipe_up("Set duration,10")

def extract_status(text: str) -> str:
    """
    Clean unwanted junk, remove short words (<=2 chars) except status/units,
    and extract generic <Name>: <Status/Value> pairs.
    """
    # Define valid statuses
    valid_statuses = ["On", "Off", "Open", "Closed", "HIGH", "LOW", "Normal"]

    # Step 1: remove junk chars
    clean_text = re.sub(r"[^\w\s\.\-]", " ", text)

    # Step 2: normalize spaces
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # Step 3: regex for either status OR numeric + unit
    matches = re.findall(
        r"([A-Za-z ]+?)\s+((?:\d+(?:\.\d+)?\s*\w+)|(?:On|Off|Open|Closed|HIGH|LOW|Normal))",
        clean_text,
        flags=re.I,
    )

    # Step 4: clean names (remove words <=2 chars, keep statuses/values intact)
    cleaned = []
    for name, status in matches:
        words = [w for w in name.split() if len(w) > 2]  # drop short words
        cleaned_name = " ".join(words)
        cleaned.append(f"{cleaned_name.strip()} {status.strip()}")

    # Step 5: return result
    return "\n".join(cleaned)


def capture_and_read_text():
    """
    Takes screenshot in memory, extracts text using OCR, and returns it.

    Args:
        driver: Appium webdriver instance

    Returns:
        str: Extracted text from screenshot
    """
    try:
        # 1. Take screenshot as base64
        screenshot_base64 = driver.get_screenshot_as_base64()

        # 2. Decode to bytes → numpy array
        screenshot_bytes = base64.b64decode(screenshot_base64)
        nparr = np.frombuffer(screenshot_bytes, np.uint8)

        # 3. Decode image
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 4. Extract text using OCR
        text = pytesseract.image_to_string(image)
        text = extract_status(text)

        return text.strip()

    except Exception as e:
        return f"Not ok#{str(e)}"

# init_driver()
# print(capture_and_read_text())

def text_extractor():
    # 1. Take screenshot as base64
    screenshot_base64 = driver.get_screenshot_as_base64()

    # 2. Decode to bytes → numpy array
    screenshot_bytes = base64.b64decode(screenshot_base64)
    nparr = np.frombuffer(screenshot_bytes, np.uint8)

        # 3. Decode image
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 4. Extract text using OCR
    text = pytesseract.image_to_string(image)
    #text = extract_status(text)
    return text



def extract_notifications(raw_text):
    # Generic regex: detects lines with "something + time marker"
    header_pattern = re.compile(r"^(.*?)(?:•|-|\*).*?(\d+[mhds])")
    
    lines = raw_text.splitlines()
    notifications = []
    current = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match header with relative time (e.g., 19m, 2h, 1d)
        match = header_pattern.search(line)
        if match:
            # Save previous notification
            if current:
                notifications.append(current)

            app_title = match.group(1).strip()
            time = match.group(2)

            # Clean symbols from app name
            app_title = re.sub(r"[^\w\s&]", "", app_title)

            current = {
                "header": app_title,
                "time": time,
                "content": []
            }
        else:
            # Add line as content if inside a notification
            if current and not re.search(r"\d+[mhds]", line):
                current["content"].append(line)

    # Add the last notification
    if current:
        notifications.append(current)

    return notifications

def Compare_Screen_By_Multiple_Texts(input_text, scroll_distance=100,_retry=0):
    """
    Compare multiple texts on screen using native TextView (NO OCR).
    Ignores last word of each input text.

    Args:
        input_text (str): "front driver open:rear passenger close,10"
    """
    try:
        # Parse input
        param1, param2 = input_text.split(",", 1)
        timeout = int(param2.strip())

        raw_list = [x.strip().lower() for x in param1.split(":") if x.strip()]
        search_list = [" ".join(x.split()[:-1]) for x in raw_list]

        found = set()
        start_time = time.time()

        window = driver.get_window_size()
        width, height = window["width"], window["height"]

        # def swipe_up(d):
        #     driver.swipe(width // 2, height // 2, width // 2, height // 2 - d, 300)

        # def swipe_down(d):
        #     driver.swipe(width // 2, height // 2, width // 2, height // 2 + d, 300)

        while time.time() - start_time < timeout:

            # 🔹 Native text capture (NO OCR)
            elements = driver.find_elements(
                AppiumBy.CLASS_NAME,
                "android.widget.TextView"
            )

            all_texts = ""
            for element in elements:
                if element.text:
                    all_texts += element.text.lower() + " "

            screen_text = all_texts.strip()
            print("[SCREEN TEXT]:", screen_text)

            # Compare base text
            for s in search_list:
                if s in screen_text:
                    found.add(s)

            if len(found) == len(search_list):
                return "Ok# Status found on screen: " + ", ".join(found)

            missing = [s for s in search_list if s not in found]

            # # Scroll logic
            # if missing:
            #     if missing[0] == search_list[0]:
            #         swipe_up(scroll_distance)
            #     elif missing[-1] == search_list[-1]:
            #         swipe_down(scroll_distance)

            sleep(0.5)

        # Timeout → capture screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(
            Screenshot_path, f"screenshot_{timestamp}.png"
        )
        driver.save_screenshot(save_path)

        return (
            "Not ok# Missing status on screen: "
            + ", ".join(missing)
            + "+"
            + save_path
        )

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Compare_Screen_By_Multiple_Texts(input_text, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

def Validate_Status(input_str,_retry=0):
    """
    Validate each feature (all words except last) against expected status (last word).

    Args:
        input_str (str): "Front Driver Closed:Rear Passenger Open,10"
                         (multiple items separated by ":" and timeout after comma)

    Returns:
        str: "Ok# ..." with PASS/FAIL results or "ERROR"
    """
    try:
        # Split into parameters
        param1, param2 = input_str.split(",", 1)
        timeout = int(param2)
        Status_Arr = param1.split(":")   # multiple status strings like ["Front Driver Closed", "Rear Passenger Open"]

        # Screenshot directory
        base_dir = PROJECT_ROOT / "Appium" / "Validation Screenshots"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        count = 0
        status_log = ""
        itr = 0
        output = ""
        sleep(timeout)
        for item in Status_Arr:
            
            #print(item)

            # 1. Take screenshot with current date & time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(base_dir, f"status_{timestamp}.png")
            driver.save_screenshot(screenshot_path)
            
            elements = driver.find_elements(
                AppiumBy.CLASS_NAME,
                "android.widget.TextView"
            )

            all_texts = ""   # string instead of list

            for element in elements:
                if element.text:
                    all_texts += element.text.lower() + " "

            text = all_texts.strip()
            print(text)


            # 4. Compare expected with OCR text
            bolleasn_op = "Not ok"
            if item.lower() in text.lower():
                count += 1
                status_log += f"Result: Pass,Status: {item} is updated on mobile.+{screenshot_path}"
            else:
                status_log += f"Result: Fail,Status: {item} is not updated on mobile.+{screenshot_path}"

            if itr < (len(Status_Arr) - 1):
                status_log += ", \n"
            itr += 1

            # 5. Abort check (LabVIEW abort file)
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                break

        # Final OK/Not ok
        if count == len(Status_Arr):
            bolleasn_op = "Ok"
        else:
            bolleasn_op = "Not ok"

        output = bolleasn_op + "#\n" + status_log
        return output

    # except Exception as e:
    #     print(f"Error: {e}")
    #     return f"Not ok#ERROR:{e}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Validate_Status(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"


# init_driver()
# print(Validate_Status(",10"))

def Validate_Alerts(search_str,_retry=0):
    """
    Open notifications, take screenshot, extract text,
    search for a string, clear notifications, and close panel.

    Args:
        search_str (str): String to search in notification text, format: "alert1:alert2:alert3,...timeout"

    Returns:
        str: "Ok# ..." with PASS/FAIL results or "ERROR"
    """
    try:
        param1, param2 = search_str.split(",", 1)
        Alerts, Expected=param1.split("$",1)
        Expected=Expected.lower().strip()
        
        timeout = float(param2)
        Alerts_Arr = Alerts.split(":")
        print(Alerts_Arr)

        Param1_len=len(param1)
        if Param1_len==0:
            return "Not ok#Input string is empty"

        # Screenshot directory
        base_dir = PROJECT_ROOT / "Appium" / "Validation Screenshots"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        driver.open_notifications()
        count = 0
        status = ""
        itr = 0

        poll_interval = 0.5  # seconds

        for alert_text in Alerts_Arr:
            found = False
            start_time = time.time()
            screenshot_path = None
            timestamp = time.strftime("%Y%m%d_%H%M%S")

            while True:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    break  # Time’s up

                # Take screenshot
                
                screenshot_path = os.path.join(base_dir, f"notification_{timestamp}.png")
                driver.save_screenshot(screenshot_path)

                # OCR extract text
                image = cv2.imread(screenshot_path)
                text = pytesseract.image_to_string(image)
                print(text)
                

                if alert_text.lower() in text.lower():
                    found = True
                    driver.save_screenshot(screenshot_path)
                    break

                if os.path.exists(file_to_watch):
                    os.remove(file_to_watch)
                    break

                # Calculate remaining time
                time_left = timeout - elapsed
                # Sleep either poll_interval or remaining time, whichever is smaller
                sleep(min(poll_interval, time_left))
            
            clean_alert = alert_text.replace('\n', ' ').replace('\r', ' ').strip()


            # if found:
            #     count += 1
            #     status += f"Result: Pass, Status: {clean_alert} is received on mobile.+{screenshot_path}"
            # else:
            #     screenshot_path = os.path.join(base_dir, f"notification_{timestamp}.png")
            #     driver.save_screenshot(screenshot_path)
            #     status += f"Result: Fail, Status: {clean_alert} is not received on mobile.+{screenshot_path}"
            
            
            if found and Expected == "received":
                count += 1
                status += f"{clean_alert} was received on mobile.+{screenshot_path}"
            elif found and Expected == "not received":
                status += f"{clean_alert} was received on mobile.+{screenshot_path}"
            elif not found and Expected == "not received":
                count += 1
                status += f"{clean_alert} was not received on mobile.+{screenshot_path}"
            else:
                screenshot_path = os.path.join(base_dir, f"notification_{timestamp}.png")
                driver.save_screenshot(screenshot_path)
                status += f"{clean_alert} was not received on mobile.+{screenshot_path}"
                

            if itr < (len(Alerts_Arr) - 1):
                status += ",\n"
            itr += 1

            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                break

        bolleasn_op = "Ok" if count == len(Alerts_Arr) else "Not ok"
        print(bolleasn_op)
        output = bolleasn_op + "#" + status

        if bolleasn_op=="Ok" or bolleasn_op=="Not ok":
            Click_By_Coordinates("581_2210,10")                   #Click_By_Text("Clear all,1")
            op=Compare_Screen_By_Text("Appium Settings,1")
            print(op)
            op1,op2=op.split("#",1)
            if op1 == "Ok":
                driver.back()

        else:
            driver.back()  # optional close notifications panel
       

        return output

    # except Exception as e:
    #     print(f"Not ok#Error: {e}")
    #     driver.back()
    #     return f"Not ok#ERROR:{e}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Validate_Alerts(search_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    
# init_driver()
# # driver.back()

# # # clear_btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Clear all")
# # # clear_btn.click()
# # # Click_By_Coordinates("581_2210,10")

# # print(Compare_Screen_By_Text("Appium Settings,1"))

# print(Validate_Alerts("Refuel$recieved,10"))

def Check_Remote_Command_Status(input_str,interval=0.2,_retry=0):
    """
    Check if remote command was executed successfully by scanning an existing image.
    """
    try:
        param1, param2 = input_str.split(",", 1)
        timeout = int(param2)

        # Load the image
        image = cv2.imread(Common_Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return f"Not ok: Could not load image from {Common_Ref_Img_Path}"

        # Optional crop: bottom 30% of image
        h, w = image.shape
        roi = image[int(h * 0.7):, :]

        # OCR configuration
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(roi, config=custom_config)
        print(f"OCR: {text} \n")

        # If successful, save a copy
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if "Successfully" in text or "Successful" in text:
            screenshot_path = os.path.join(Screenshot_path, f"success_{timestamp}.png")
            cv2.imwrite(screenshot_path, image)
            return f"Ok# Remote command executed successfully.+{screenshot_path}"
        else:
            screenshot_path = os.path.join(Screenshot_path, f"fail_{timestamp}.png")
            cv2.imwrite(screenshot_path, image)
            return f"Not ok# Remote command not executed successfully.+{screenshot_path}"

    # except Exception as e:
    #     return f"Not ok#{str(e)}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Check_Remote_Command_Status(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

# Common_Ref_Img_Path="C:\\Users\\TML PCV TCU HIL PXI\\Documents\\Ref_Screenshot.png"
def ocr_to_single_line(text):
    # remove newlines, tabs
    text = text.replace("\n", " ").replace("\t", " ")

    # remove extra spaces
    text = re.sub(r"\s+", " ", text)

    # strip junk dots / stray characters
    text = re.sub(r"[•·]", "", text)

    return text.strip()

# Common_Ref_Img_Path="C:\\MaxEye\\MEP00179\\Application\\Configuration_Files\\Appium\\Screenshots\\Error_Ref_Screenshot.png"

# import re

def normalize_ocr_text(text):
    """
    Normalize OCR text for reliable matching
    """
    text = text.lower()
    text = re.sub(r'[|]', ' ', text)      # replace | with space
    text = re.sub(r'[^a-z0-9 ]+', ' ', text)  # remove junk chars
    text = re.sub(r'\s+', ' ', text)      # collapse spaces
    return text.strip()


def Check_Display_Message_Text_old(input_str,interval=0.2,_retry=0):
    """
    Check if remote command was executed successfully by scanning an existing image.
    """
    try:
        param1, param2 = input_str.split(",", 1)
        Val_Text,Param=param1.split("_")
        Param=Param.strip().lower()
        param1=Val_Text.strip().lower()
        timeout = int(param2)

        # Load the image
        image = cv2.imread(Common_Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return f"Not ok: Could not load image from {Common_Ref_Img_Path}"

        # Optional crop: bottom 30% of image
        h, w = image.shape
        roi = image[int(h * 0.7):, :]

        # OCR configuration
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(roi, config=custom_config)
        text=text.lower()
        clean_text=ocr_to_single_line(text)
        text=normalize_ocr_text(clean_text)
        print(param1)
        print(text)
        
        print(f"OCR: {text} \n")
        # If successful, save a copy
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if param1 in text and Param == "received":
            screenshot_path = os.path.join(Screenshot_path, f"success_{timestamp}.png")
            cv2.imwrite(screenshot_path, image)
            Common_Ref_Img_Path=""
            return f"Ok# Remote command executed successfully.+{screenshot_path}"
        else:
            screenshot_path = os.path.join(Screenshot_path, f"fail_{timestamp}.png")
            cv2.imwrite(screenshot_path, image)
            Common_Ref_Img_Path=""
            return f"Not ok# Remote command not executed successfully.+{screenshot_path}"

    # except Exception as e:
    #     return f"Not ok#{str(e)}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Check_Display_Message_Text(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

# Common_Ref_Img_Path_List=["C:\MaxEye\MEP00179\Application\Configuration_Files\Appium\Screenshots\screen_timeout_20260307_130534.png"]

def Check_Display_Message_Text(input_str, interval=0.2, _retry=0):
    """
    Input format:
        "ExpectedText_received,10"

    Checks OCR text inside all reference images.
    If ANY image matches → success.
    """

    global Common_Ref_Img_Path_List

    try:
        param1, param2 = input_str.split(",", 1)
        Val_Text, Param = param1.split("_")

        expected_text = Val_Text.strip().lower()
        Param = Param.strip().lower()
        timeout = int(param2)

        if not Common_Ref_Img_Path_List:
            return "Not ok# Reference image list is empty"

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # 🔥 Loop through all reference images
        for img_path in Common_Ref_Img_Path_List:

            image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

            if image is None:
                print(f"Could not load {img_path}")
                continue

            # Optional crop: bottom 30%
            h, w = image.shape
            roi = image[int(h * 0.7):, :]

            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(roi, config=custom_config)
            text = text.lower()
            text = ocr_to_single_line(text)

            print(f"\nChecking Image: {img_path}")
            print(f"Expected: {expected_text}")
            print(f"OCR Text: {text}")

            # 🔥 FIXED condition (your old one was wrong)
            if expected_text in text and Param == "received":
                success_path = os.path.join(
                    Screenshot_path,
                    f"success_{timestamp}.png"
                )
                cv2.imwrite(success_path, image)
                
                for path in Common_Ref_Img_Path_List:
                    if os.path.exists(path):
                        os.remove(path)
                        print(f"Deleted: {path}")
                    else:
                        print(f"File not found: {path}")
                Common_Ref_Img_Path_List=[]
                return f"Ok# Remote command executed successfully.+{success_path}"
            elif expected_text not in text and Param != "received":
                success_path = os.path.join(
                    Screenshot_path,
                    f"success_{timestamp}.png"
                )
                cv2.imwrite(success_path, image)
                
                for path in Common_Ref_Img_Path_List:
                    if os.path.exists(path):
                        os.remove(path)
                        print(f"Deleted: {path}")
                    else:
                        print(f"File not found: {path}")
                Common_Ref_Img_Path_List=[]
                return f"Ok# Remote command executed successfully.+{success_path}"

        # 🔥 If none matched
        fail_path = os.path.join(
            Screenshot_path,
            f"fail_{timestamp}.png"
        )

        # Save last image for reference
        cv2.imwrite(fail_path, image)
        
        
        Op=Compare_Screen_By_Text("Unable to process the remote command,1")
        print(Op)
        
        Op,_=Op.split("#")
        Op=Op.strip().lower()
        print(Op)
        Common_Ref_Img_Path_List=Common_Ref_Img_Path_List[::-1]
        
        success_path=Common_Ref_Img_Path_List[0]
        if Op=="not ok":
            Common_Ref_Img_Path_List=[]
            return f"Ok# Remote command executed successfully.+{success_path}"
        Common_Ref_Img_Path_List=[]

        return f"Not ok# Remote command not executed successfully.+{fail_path}"

    except Exception as e:

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                sleep(1)
                return Check_Display_Message_Text(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    
# init_driver()

# print(Check_Display_Message_Text("Command executed successfully_received,1"))

def Check_Mode_Exe_Status_Text(input_str,interval=0.2,_retry=0):
    """
    Check if remote command was executed successfully by scanning an existing image.
    """
    try:
        param1, param2 = input_str.split(",", 1)
        
        param1=param1.strip().lower()
        
        timeout = int(param2)

        # Load the image
        image = cv2.imread(Common_Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return f"Not ok: Could not load image from {Common_Ref_Img_Path}"

        # Optional crop: bottom 30% of image
        h, w = image.shape
        roi = image[int(h * 0.7):, :]

        # OCR configuration
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(roi, config=custom_config)
        text=text.lower()
        clean_text=ocr_to_single_line(text)
        text=clean_text
        print(param1)
        print(text)
        
        print(f"OCR: {text} \n")
        # If successful, save a copy
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if param1 in text in text:
            screenshot_path = os.path.join(Screenshot_path, f"success_{timestamp}.png")
            cv2.imwrite(screenshot_path, image)
            return f"Ok# Executed sucessfully+{screenshot_path}"
        else:
            screenshot_path = os.path.join(Screenshot_path, f"fail_{timestamp}.png")
            cv2.imwrite(screenshot_path, image)
            return f"Not ok# Not executed successfully+{screenshot_path}"

    # except Exception as e:
    #     return f"Not ok#{str(e)}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Check_Mode_Exe_Status_Text(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

def Long_Press_Indirect_By_Image(image_path, duration=2000, threshold=0.85,_retry=0):
    """
    Long press on an element found by image reference using mobile: dragGesture.
    Works across all resolutions (scales coordinates). Also reports execution time.

    Args:
        image_path (str): "path_to_image,timeout"
        duration (int): Long press duration in ms
        threshold (float): Template matching threshold (default 0.85)

    Returns:
        str
    """
    start_time = time.perf_counter()  # ⏱ start

    try:
        param1, param2 = image_path.split(",", 1)
        img_path = param1.strip()
        timeout = int(param2)
        duration = timeout * 1000

        screenshot_file = os.path.join(Screenshot_path, "temp.png")
        driver.save_screenshot(screenshot_file)

        screen = cv2.imread(screenshot_file)
        template = cv2.imread(img_path)

        if screen is None or template is None:
            return "Not ok#Failed to read images"

        # Template matching
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            return f"Not Ok# Image '{image_path}' not found (max_val={max_val:.2f})"

        # Get match center (in screenshot coordinates)
        x = max_loc[0] + template.shape[1] // 2
        y = max_loc[1] + template.shape[0] // 2

        # Normalize → convert to device resolution
        screen_h, screen_w = screen.shape[:2]
        window_size = driver.get_window_size()
        dev_w, dev_h = window_size["width"], window_size["height"]

        norm_x = x / screen_w
        norm_y = y / screen_h
        dev_x = int(norm_x * dev_w)
        dev_y = int(norm_y * dev_h)

        # Extra validation (SSIM check on region to reduce false positives)
        try:
            matched_region = screen[y - template.shape[0]//2:y + template.shape[0]//2,
                                    x - template.shape[1]//2:x + template.shape[1]//2]
            if matched_region.shape[:2] == template.shape[:2]:
                from skimage.metrics import structural_similarity as ssim
                gray_ref = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                gray_crop = cv2.cvtColor(matched_region, cv2.COLOR_BGR2GRAY)
                score, _ = ssim(gray_ref, gray_crop, full=True)
                if score < 0.70:
                    return f"Not Ok# False match rejected (SSIM={score:.2f})"
        except Exception:
            pass

        # ✅ Use dragGesture for long press
        driver.execute_script(
            "mobile: dragGesture",
            {
                "startX": dev_x,
                "startY": dev_y,
                "endX": dev_x,
                "endY": dev_y,
                "duration": duration
            }
        )

        exec_time = (time.perf_counter() - start_time) * 1000  # ms
        return f"Ok# Long pressed on image '{image_path}' at ({dev_x},{dev_y}) | ExecTime={exec_time:.2f}ms"

    # except Exception as e:
    #     exec_time = (time.perf_counter() - start_time) * 1000  # ms
    #     return f"Not ok#Long_Press_Indirect_By_Image failed: {str(e)} | ExecTime={exec_time:.2f}ms"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Long_Press_Indirect_By_Image(image_path, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"



# init_driver()
# print(Long_Press_Indirect_By_Image("D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\Operational Images\\VID.jpg,10"))
#print(Long_Press_Indirect_By_Image("C:\\Users\\panch\\OneDrive - Maxeye Technologies Pvt Ltd\\Documents\\VID.jpg,2000"))

# print(Scroll_and_Click_Text("87a8aab6-aab6-48aab6f45a-88aab6f45aadc-adc4e8=7498347036,10"))



# init_driver()
# print(Validate_Alerts("a1:a2:a3,10"))
    
############################################## Logcat ################################################

def log_handler(cmd):
    global log_process, temp_log_fullpath

    try:
        param1, param2 = cmd.split(",", 1)
        command = param1.strip().lower()
    except ValueError:
        return "ERROR: Invalid command format. Use 'start,<filename>' or 'stop,<filename>'"

    if command == "start":
        try:
            # Make log directory if not exists
            os.makedirs(temp_logfilepath, exist_ok=True)

            # Define temporary log path
            temp_log_fullpath = os.path.join(temp_logfilepath, "temp_log.log")

            # Remove old temp log
            if os.path.exists(temp_log_fullpath):
                os.remove(temp_log_fullpath)

            # Start ADB logcat process
            log_process = subprocess.Popen(
                ["adb", "logcat", "-v", "time"],
                stdout=open(temp_log_fullpath, "w"),
                stderr=subprocess.STDOUT
            )
            return "LOGGING STARTED"
        except Exception as e:
            return f"Not ok#Failed to start logging - {e}"

    elif command == "stop":
        try:
            if log_process:
                log_process.terminate()
                log_process.wait()
                log_process = None

                # Rename with timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                final_filename = f"mobile_log_{timestamp}.log"
                final_filepath = os.path.join(temp_logfilepath, final_filename)

                os.rename(temp_log_fullpath, final_filepath)

                return f"LOGGING STOPPED: {final_filename}"
            else:
                return "WARNING: No log process was running"
        except Exception as e:
            return f"Not ok: Failed to stop logging - {e}"

    else:
        return "Not ok#Unknown command. Use 'start' or 'stop'"
    
    
# init_driver()

# print(log_handler("start,1"))
# print(log_handler("stop,1"))

def Wait_Until_Text_Disappears_Old(text_to_watch,_retry=0):
    """
    Wait until a given text disappears from the screen.
    Halts until text disappears, or saves screenshot on failure.
    """
    global Common_Ref_Img_Path
    try:
        param1,param2=text_to_watch.split(",")
        timeout=int(param2)
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{param1}")')
            )
        )
        # sleep(1)
        capture_screenshot(Ref_Img_Path)
        curr_img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"Error_Ref_Screenshot.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)
        Common_Ref_Img_Path=full_path
        print(Common_Ref_Img_Path)
        
        return "Ok# Screen got changed"
    
    # except Exception:
    #     # Take screenshot directly
    #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #     full_path = os.path.join(
    #         Screenshot_path, f"screenshot_{timestamp}.png"
    #     )
    #     driver.get_screenshot_as_file(full_path)
    #     return f"Not Ok# Text '{param1}' still present after {timeout} sec+{full_path}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Wait_Until_Text_Disappears(text_to_watch, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"


def Wait_Until_Text_Disappears(text_to_watch, _retry=0):
    """
    Input Format:
        "text,timeout"

    Example:
        "Loading,15"

    Output:
        Ok# 4 Reference Screens Captured
        Not ok# <reason>
    """

    global Common_Ref_Img_Path_List

    try:
        param1, param2 = text_to_watch.split(",")
        text_value = param1.strip()
        timeout = int(param2.strip())

        # 🔥 Wait until text disappears
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR,
                 f'new UiSelector().text("{text_value}")')
            )
        )

        # Small delay to allow popup rendering
        # sleep(0.1)

        image_paths = []
        os.makedirs(Screenshot_path, exist_ok=True)

        # 🔥 Capture 4 fast frames (in-memory → faster than disk screenshot)
        for i in range(5):
            start_time = time.time()

            png = driver.get_screenshot_as_png()
            img_array = np.frombuffer(png, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"Ref_{i+1}.png"
            full_path = os.path.join(Screenshot_path, filename)

            cv2.imwrite(full_path, img)
            image_paths.append(full_path)

            end_time = time.time()
            print(f"[Frame {i+1}] Capture Time: {end_time - start_time:.3f} sec")

            sleep(0.3)  # allow popup animation transition

        Common_Ref_Img_Path_List = image_paths
        print(Common_Ref_Img_Path_List)

        print("Captured 4 Reference Images:")
        for path in image_paths:
            print(path)

        return "Ok# 4 Reference Screens Captured"

    except Exception as e:

        # 🔥 UIA2 Recovery Block (Your Framework Style)
        if is_uia2_socket_error(e):
            if _retry < 2:
                print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                sleep(1)
                return Wait_Until_Text_Disappears(text_to_watch, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"

    
    
def Wait_Until_Image_Disappears(input,_retry=0):
    """
    input format:
    image_path,timeout

    example:
    icons/loading.png,10
    """

    global Common_Ref_Img_Path

    try:
        image_path, timeout = input.split(",")
        timeout = int(timeout)

        end_time = time.time() + timeout
        template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if template is None:
            return f"Not Ok# Image not found at path: {image_path}"

        h, w = template.shape

        while time.time() < end_time:
            # Capture screenshot
            capture_screenshot(Ref_Img_Path)
            screen = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)

            res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)

            # If image NOT found → success
            if max_val < 0.85:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"Ref_Screenshot.png"
                full_path = os.path.join(Screenshot_path, save_path)

                cv2.imwrite(full_path, screen)
                Common_Ref_Img_Path = full_path
                print(Common_Ref_Img_Path)

                return "Ok# Screen got changed"

            sleep(0.5)

        # Timeout → image still present
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_path = os.path.join(
            Screenshot_path, f"screenshot_{timestamp}.png"
        )
        driver.get_screenshot_as_file(full_path)

        return f"Not Ok# Image still present after {timeout} sec+{full_path}"

    # except Exception as e:
    #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #     full_path = os.path.join(
    #         Screenshot_path, f"error_{timestamp}.png"
    #     )
    #     driver.get_screenshot_as_file(full_path)

    #     return f"Not Ok# Exception occurred: {str(e)}+{full_path}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Wait_Until_Image_Disappears(input, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    
# init_driver()
# Send_Inputs("2580,10")
# Wait_Text("5,10")
# print(Wait_Until_Image_Disappears("C:\\Users\\TML PCV TCU HIL PXI\\Documents\\loading.png,10"))
# print(Check_Mode_Exe_Status_Text(",10"))
    
def Result_Text(input):
    param1,param2=input.split(",")
    capture_screenshot(Ref_Img_Path)
    curr_img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = f"Ref_Screenshot_{timestamp}.png"
    full_path = os.path.join(Screenshot_path, save_path)
    # Save the image
    cv2.imwrite(full_path, curr_img)
    return f"{param1}+{full_path}"

def Check_ODO_Status_Text(input,_retry=0):
    try:
        param1, param2 = input.split(",")
        timeout = int(param2.strip())
        sleep(timeout)

        expected_text = param1.strip().lower()
        capture = False
        odo_parts = []

        elements = driver.find_elements(
            AppiumBy.CLASS_NAME,
            "android.widget.TextView"
        )

        for element in elements:
            text = element.text.strip()
            if not text:
                continue

            text_lower = text.lower()

            # Start capture when ODO is found
            if text_lower == "odo":
                capture = True
                continue
            # Stop capture after km
            if text_lower == "km" and capture:
                break

            if capture:
                odo_parts.append(text)

        odo_string = "".join(odo_parts).lower()
        Int_String = int(odo_string)
        odo_string = str(Int_String)
        print("Extracted ODO String:", odo_string)
        
        capture_screenshot(Ref_Img_Path)
        curr_img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_path = os.path.join(
            Screenshot_path, f"screenshot_{timestamp}.png"
        )
        # Save the image
        cv2.imwrite(full_path, curr_img)

        if odo_string == expected_text:
            return f"Ok#{expected_text} is successfully updated in mobile application+{full_path}"
        else:
            return f"Not ok#{expected_text} is not successfully updated in mobile application+{full_path}"

    # except Exception as e:
    #     return f"Not ok#ODO validation failed due to {str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Check_ODO_Status_Text(input, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

#         return f"Not ok# {str(e)}"


# def extract_charging_data():
#     """
#     Extract charging health pattern data and charging cycle data
#     from Android TextView elements.

#     Returns:
#         tuple: (charging_health_pattern_data, charging_cycle_data)
#     """

#     charging_health_pattern_data = []
#     charging_cycle_data = []

#     cycle = 0
#     chrg_cycle = 0

#     try:
#         elements = driver.find_elements(
#             AppiumBy.CLASS_NAME,
#             "android.widget.TextView"
#         )

#         for element in elements:
#             try:
#                 text = element.text.strip()

#                 # Reset conditions
#                 if "recommendation" in text.lower():
#                     cycle = 0

#                 if text.lower() == "latest":
#                     chrg_cycle = 0

#                 # Store data
#                 if cycle > 0:
#                     charging_health_pattern_data.append(text)

#                 if chrg_cycle > 0:
#                     charging_cycle_data.append(text)

#                 # Start capture conditions
#                 if "Number of Slow (AC)" in text:
#                     cycle += 1

#                 if "This shows last 4 charging cycle data" in text:
#                     chrg_cycle += 1

#             except Exception as element_error:
#                 print(f"Error while processing element: {element_error}")

#         return charging_health_pattern_data, charging_cycle_data

#     except Exception as e:
#         print(f"Error while extracting charging data: {e}")
#         return [], []



def format_charging_health_pattern(data):
    """
    Convert charging health pattern list into readable string.
    """

    labels = ["Green", "Lime", "Yellow", "Red"]

    try:
        formatted_data = []

        for label, value in zip(labels, data):
            formatted_data.append(f"{label}: {value}")

        return ", ".join(formatted_data)

    except Exception as e:
        return f"Error while formatting charging health pattern data: {str(e)}"

def extract_charging_health_pattern_data():
    """
    Extract charging health pattern data, charging cycle data,
    and recommendation data from Android TextView elements.

    Returns:
        str
    """

    charging_health_pattern_data = []
    charging_cycle_data = []
    recommendation = ""

    cycle = 0
    chrg_cycle = 0
    rec_count = 0

    try:
        elements = driver.find_elements(
            AppiumBy.CLASS_NAME,
            "android.widget.TextView"
        )

        for element in elements:
            try:

                text = element.text.strip()

                # Stop recommendation capture
                if "charging cycle" in text.lower():
                    rec_count = 0

                # Capture recommendation text
                if rec_count > 0 and text:
                    recommendation = text

                # Reset conditions
                if "recommendation" in text.lower():
                    rec_count = 1
                    cycle = 0

                if text.lower() == "latest":
                    chrg_cycle = 0

                # Store data
                if cycle > 0:
                    charging_health_pattern_data.append(text)

                if chrg_cycle > 0:
                    charging_cycle_data.append(text)

                # Start capture conditions
                if "Number of Slow (AC)" in text:
                    cycle += 1

                if "This shows last 4 charging cycle data" in text:
                    chrg_cycle += 1

            except Exception as element_error:
                print(f"Error while processing element: {str(element_error)}")

        formatted_health_pattern = format_charging_health_pattern(
            charging_health_pattern_data
        )

        # Final Output
        result = (
            f"OK# Charging health pattern data: "
            f"{formatted_health_pattern}"
        )

        if charging_cycle_data:
            result += (
                f" | Charging cycle data: "
                f"{', '.join(charging_cycle_data)}"
            )

        if recommendation:
            result += (
                f" | Recommendation data: "
                f"{recommendation}"
            )

        return result

    except Exception as e:
        return f"FAIL# Error while extracting charging data: {str(e)}"

# init_driver()
# print(extract_charging_health_pattern_data())
# print(Check_ODO_Status_Text("10,10"))

TEMPLATE_CACHE = {}
ABORT_FILE = "abort.txt"
LABVIEW_MODE = True


# ---------- TEMPLATE CACHE ----------
def get_template_gray(path):
    if path not in TEMPLATE_CACHE:
        tpl = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            return None
        TEMPLATE_CACHE[path] = tpl
    return TEMPLATE_CACHE[path]


# ---------- MEMORY SCREENSHOT ----------
def get_screen_bgr():
    png = driver.get_screenshot_as_png()
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)


# ---------- MULTI-SCALE MATCH ----------
def multi_scale_match(template, screen_gray, threshold):
    th, tw = template.shape[:2]

    # ---- 1️⃣ Normal template match ----
    for scale in np.linspace(0.6, 1.5, 19):
        resized = cv2.resize(template, (int(tw * scale), int(th * scale)))
        if resized.shape[0] > screen_gray.shape[0] or resized.shape[1] > screen_gray.shape[1]:
            continue

        res = cv2.matchTemplate(screen_gray, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            x = int(max_loc[0] + resized.shape[1] / 2)
            y = int(max_loc[1] + resized.shape[0] / 2)
            return True, (x, y)

    # ---- 2️⃣ EDGE fallback (THIS is why old code worked) ----
    tpl_edge = cv2.Canny(template, 50, 150)
    scr_edge = cv2.Canny(screen_gray, 50, 150)

    for scale in np.linspace(0.6, 1.5, 19):
        resized = cv2.resize(tpl_edge, (int(tw * scale), int(th * scale)))
        if resized.shape[0] > scr_edge.shape[0] or resized.shape[1] > scr_edge.shape[1]:
            continue

        res = cv2.matchTemplate(scr_edge, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold - 0.1:  # slightly relaxed
            x = int(max_loc[0] + resized.shape[1] / 2)
            y = int(max_loc[1] + resized.shape[0] / 2)
            return True, (x, y)

    return False, (None, None)

# ================= CLICK BY IMAGE =================
def Click_By_Image_Fast(input_str, threshold=0.86, check_interval=0.2, _retry=0):
    """
    INPUT  : "image_path,timeout"
    OUTPUT : "Ok# Clicked at (x,y)"
             "Not Ok# Image not found"
             "Not Ok# Aborted"
    """
    try:
        # ---- Parse input ----
        parts = input_str.split(",", 1)
        if len(parts) != 2:
            return "Not Ok# Invalid input format"

        img_path = parts[0].strip()
        timeout = float(parts[1].strip())

        if not os.path.exists(img_path):
            return f"Not Ok# Image not found: {img_path}"

        # 🚫 init_driver REMOVED — driver must already exist
        if driver is None:
            return "Not Ok# Driver not initialized"

        template = get_template_gray(img_path)
        if template is None:
            return "Not Ok# Template load failed"

        start = time.time()

        # ---- Loop ----
        while True:

            # Abort
            if os.path.exists(ABORT_FILE):
                try:
                    os.remove(ABORT_FILE)
                except Exception:
                    pass
                return "Not Ok# Aborted"

            # Timeout
            if time.time() - start > timeout:
                if _retry<2:
                    Click_By_Image_Fast(input_str,_retry = _retry + 1)
                else:
                    return f"Not Ok# Image '{os.path.basename(img_path)}' not found"

            # Screenshot (memory)
            screen = get_screen_bgr()
            if screen is None:
                time.sleep(check_interval)
                continue

            gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

            found, (x, y) = multi_scale_match(template, gray, threshold)

            if found:
                driver.execute_script(
                    "mobile: clickGesture",
                    {"x": int(x), "y": int(y)}
                )
                return f"Ok# Clicked on image '{os.path.basename(img_path)}' at ({x},{y})"

            time.sleep(check_interval)

    # except Exception as e:
    #     return f"Not Ok# ERROR: {str(e)}"
    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Click_By_Image_Fast(input_str, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    
# def Set_Speed_Limit_Using_Text(input,_retry=0):
#     """
#     input format:
#     target_value,timeout

#     example:
#     20,5
#     """

#     try:
#         param1, param2 = input.split(",")
#         target = int(param1.strip())
#         timeout = int(param2.strip())

#         driver.implicitly_wait(0)
#         end_time = time.time() + timeout

#         def get_current_value():
#             elements = driver.find_elements(
#                 AppiumBy.CLASS_NAME,
#                 "android.widget.TextView"
#             )
#             for element in elements:
#                 text = element.text.strip()
#                 if text.isdigit():   # <-- THIS is key
#                     return int(text)
#             return None
        
#         # def get_current_value():
#         #     """
#         #     Fast OCR-based number reading from speed limit circle.
#         #     """
#         #     try:
#         #         # 1️⃣ Take screenshot via Appium
#         #         png = driver.get_screenshot_as_png()
#         #         screen = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)

#         #         # 2️⃣ Convert to grayscale
#         #         gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
#         #         h, w = gray.shape

#         #         # 3️⃣ Crop around center circle (adjust percentages if needed)
#         #         crop = gray[int(0.3*h):int(0.7*h), int(0.3*w):int(0.7*w)]

#         #         # 4️⃣ Threshold to make digits pop
#         #         _, thresh = cv2.threshold(crop, 150, 255, cv2.THRESH_BINARY_INV)

#         #         # 5️⃣ OCR digits only
#         #         config = "--psm 6 -c tessedit_char_whitelist=0123456789"
#         #         text = pytesseract.image_to_string(thresh, config=config)
#         #         # print(text)

#         #         digits = "".join(c for c in text if c.isdigit())
#         #         return int(digits) if digits else None

#         #     except Exception:
#         #         return None

#         while time.time() < end_time:
#             current = get_current_value()

#             if current is None:
#                 sleep(0.1)
#                 continue

#             print(f"Current Speed Limit: {current}")

#             if current == target:
#                 return f"Ok#Speed limit set to {current} km/h"

#             if current < target:
#                 # driver.find_element(
#                 #     AppiumBy.XPATH,
#                 #     "//android.widget.Button[@text='+']"
#                 # ).click()
#                 if app_evpv == 0:
#                     print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Plus.png,10"))
#                 else:
#                     print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\EV_Plus.png,10"))
#             else:
#                 # driver.find_element(
#                 #     AppiumBy.XPATH,
#                 #     "//android.widget.Button[@text='-']"
#                 # ).click()
#                 if app_evpv == 0:
#                     print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Minus.png,10"))
#                 else:
#                     print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\EV_Minus.png,10"))

#             sleep(0.2)  # allow UI to update

#         return f"Not ok#Timeout reached. Last value: {get_current_value()}"

#     except Exception as e:

#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         if is_uia2_socket_error(e):
#             if _retry < 2:
#                 safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
#                 recover_uia2_session()
#                 sleep(1)
#                 return Set_Speed_Limit_Using_Text(input, _retry=_retry + 1)

#             return "Not ok# UIA2 session recovery failed after retries"

#         return f"Not ok# {str(e)}"


def extract_center(bounds):
    nums = list(map(int, re.findall(r'\d+', bounds)))
    x1, y1, x2, y2 = nums
    return ((x1 + x2) // 2, (y1 + y2) // 2, x2 - x1, y2 - y1)


def get_plus_minus_coordinates():
    try:
        page_source = driver.page_source
        screen_height = driver.get_window_size()["height"]

        bounds_list = re.findall(r'bounds="\[.*?\]"', page_source)

        buttons = []

        for b in bounds_list:
            cx, cy, w, h = extract_center(b)

            # Filter bottom half + square buttons
            if (
                40 < w < 150 and
                40 < h < 150 and
                cy > screen_height * 0.5 and
                abs(w - h) < 20   # square-like
            ):
                buttons.append((b, cx, cy, w, h))

        if len(buttons) < 2:
            return "FAIL"

        # 🔥 Find best matching pair (same size + same Y)
        best_pair = None
        min_y_diff = float("inf")

        for i in range(len(buttons)):
            for j in range(i+1, len(buttons)):
                _, cx1, cy1, w1, h1 = buttons[i]
                _, cx2, cy2, w2, h2 = buttons[j]

                if abs(w1 - w2) < 15 and abs(h1 - h2) < 15:
                    y_diff = abs(cy1 - cy2)
                    if y_diff < min_y_diff:
                        min_y_diff = y_diff
                        best_pair = (buttons[i], buttons[j])

        if not best_pair:
            return "FAIL"

        # Sort left → right
        pair_sorted = sorted(best_pair, key=lambda x: x[1])

        minus = pair_sorted[0]
        plus  = pair_sorted[1]

        return f"{minus[1]},{minus[2]};{plus[1]},{plus[2]}"

    except:
        return "ERROR"
def Set_Speed_Limit_Using_Text(input,_retry=0):
    """
    input format:
    target_value,timeout

    example:
    20,5
    """

    try:
        param1, param2 = input.split(",")
        target = int(param1.strip())
        timeout = int(param2.strip())

        driver.implicitly_wait(0)
        end_time = time.time() + timeout

        def get_current_value():
            elements = driver.find_elements(
                AppiumBy.CLASS_NAME,
                "android.widget.TextView"
            )
            for element in elements:
                text = element.text.strip()
                if text.isdigit():   # <-- THIS is key
                    return int(text)
            return None
        
        # def get_current_value():
        #     """
        #     Fast OCR-based number reading from speed limit circle.
        #     """
        #     try:
        #         # 1️⃣ Take screenshot via Appium
        #         png = driver.get_screenshot_as_png()
        #         screen = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)

        #         # 2️⃣ Convert to grayscale
        #         gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        #         h, w = gray.shape

        #         # 3️⃣ Crop around center circle (adjust percentages if needed)
        #         crop = gray[int(0.3*h):int(0.7*h), int(0.3*w):int(0.7*w)]

        #         # 4️⃣ Threshold to make digits pop
        #         _, thresh = cv2.threshold(crop, 150, 255, cv2.THRESH_BINARY_INV)

        #         # 5️⃣ OCR digits only
        #         config = "--psm 6 -c tessedit_char_whitelist=0123456789"
        #         text = pytesseract.image_to_string(thresh, config=config)
        #         # print(text)

        #         digits = "".join(c for c in text if c.isdigit())
        #         return int(digits) if digits else None

        #     except Exception:
        #         return None

        coordinates=get_plus_minus_coordinates()
        print(coordinates)
        x,y=coordinates.split(";")
        x=x.replace(",","_").strip()
        y=y.replace(",","_").strip()
        print(x)
        print(y)

        while time.time() < end_time:
            current = get_current_value()

            if current is None:
                sleep(0.1)
                continue

            print(f"Current Speed Limit: {current}")

            if current == target:
                return f"Ok#Speed limit set to {current} km/h"
            


            print(target)

            if current < target:
                # driver.find_element(
                #     AppiumBy.XPATH,
                #     "//android.widget.Button[@text='+']"
                # ).click()

                ip=f"{y},10"
                print(ip)
                Click_By_Coordinates(ip)

                # if app_evpv == 0:

                #     print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Plus.jpg,10"))
                # else:
                #     print(Click_By_Image_Fast("D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\EV_Plus.jpg,10"))
            else:

                ip=f"{x},10"
                print(ip)
                Click_By_Coordinates(ip)

                # if app_evpv == 0:
                #     print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Minus.jpg,10"))
                # else:
                #     print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\EV_Minus.jpg,10"))

            # sleep(0.2)  # allow UI to update

        return f"Not ok#Timeout reached. Last value: {get_current_value()}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Set_Speed_Limit_Using_Text(input, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"


######################## Climate Validationn ######################

def Set_Limit_Using_Text(input,_retry=0):
    """
    input format:
    target_value,timeout

    example:
    20,5
    """

    try:
        param1, param2 = input.split(",")
        if " " in param1:
            target,unit=param1.split(" ")
            target =float(target)
        else:
            target = float(param1.strip())
            unit=""
        timeout = int(param2.strip())

        driver.implicitly_wait(0)
        end_time = time.time() + timeout

        def get_current_value():
            elements = driver.find_elements(
                AppiumBy.CLASS_NAME,
                "android.widget.TextView"
            )
            for element in elements:
                raw_text = element.text.strip()

                match = re.search(r"\d+\.?\d*", raw_text)
                if match:
                    value = float(match.group())   # ✅ extract actual number
                    print(value)
                    return value
            return None

        coordinates=get_plus_minus_coordinates()
        print(coordinates)
        x,y=coordinates.split(";")
        x=x.replace(",","_").strip()
        y=y.replace(",","_").strip()
        print(x)
        print(y)

        while time.time() < end_time:
            current = get_current_value()

            if current is None:
                sleep(0.1)
                continue

            print(f"Current Limit: {current}")

            if current == target:
                if unit:
                    return f"Ok#limit set to {current} {unit}"
                else:
                    return f"Ok#limit set to {current}"
        
            print(target)

            if current < target:

                ip=f"{y},10"
                print(ip)
                Click_By_Coordinates(ip)

            else:

                ip=f"{x},10"
                print(ip)
                Click_By_Coordinates(ip)
                
                
        if unit:
            return f"Not ok#Timeout reached. Last value: {get_current_value()} {unit}"
        else:
            return f"Not ok#Timeout reached. Last value: {get_current_value()}"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {     + 1}")
                recover_uia2_session()
                sleep(1)
                return Set_Limit_Using_Text(input, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    

# init_driver()
# print(Set_Limit_Using_Text("20 degree,10"))
    
##################### Trip #####################

def Check_Privious_Trip_Count(params, _retry=0):
    global Trip_Count, Trips

    try:
        Trips = []
        insert = False
        params=""

        elements = driver.find_elements(
            AppiumBy.XPATH,
            "//android.widget.TextView"
        )

        date_str = datetime.now().strftime("%b %d, %Y")
        print(date_str)
        # date_str = "Mar 31,2026"

        for i in elements:
            text = i.text.strip()

            print(text)

            if date_str.lower() in text.lower():
                insert = True
                print("Started")

            elif "na" == text.lower():
                insert = False

            elif insert and re.match(r"\d{2}:\d{2}", text):
                Trips.append(text)

            elif insert and re.match(r"[A-Za-z]{3} \d{1,2},\d{4}", text):
                break
        print(Trips)    

        if Trips:
            time_str = Trips[0]
        else:
            time_str=""
        
        if time_str:

            hours, minutes = map(int, time_str.split(":"))
            Trip_Count = hours * 3600 + minutes * 60
        else:
            Trip_Count=0
        

        print("Trips:", Trips)
        curr_trip=len(Trips)//2

        return f"Ok#Current trip count is {curr_trip}"

    except Exception as e:
        return f"Not ok#{str(e)}"
    

# init_driver()
# print(Check_Privious_Trip_Count("Hello"))
    
# Trip_Count=1
def Check_if_New_Trip_Generated(Input):
    global Trips
    try:
        Trips = []
        insert = False
        
        # Check_Privious_Trip_Count("input")

        elements = driver.find_elements(
            AppiumBy.XPATH,
            "//android.widget.TextView"
        )

        date_str = datetime.now().strftime("%b %d, %Y")
        # date_str = "Mar 12,2026"

        for i in elements:
            text = i.text.strip()

            print(text)

            if date_str.lower() in text.lower():
                insert = True
                print("Started")

            elif "na" == text.lower():
                insert = False

            elif insert and re.match(r"\d{2}:\d{2}", text):
                Trips.append(text)

            elif insert and re.match(r"[A-Za-z]{3} \d{1,2},\d{4}", text):
                break
        
        print(Trips)
        time_str = Trips[0]

        hours, minutes = map(int, time_str.split(":"))
        Trip_Count_New = hours * 3600 + minutes * 60

        # Trip_Count_New = len(Trips)//2
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(Screenshot_path, f"status_{timestamp}.png")
        driver.save_screenshot(screenshot_path)

        if Trip_Count_New>Trip_Count:

            return f"Ok#Trip is generated successfully+{screenshot_path}"
        else:
            return f"Not ok#Trip is not generated successfully and current trip count is {Trip_Count_New}+{screenshot_path}"
          
    except Exception as e:
        return f"Not ok#{str(e)}"
    
# init_driver()
# # Check_Privious_Trip_Count("Dummym,10")
# Trip_Count=0
# print(f"Trip count:{Trip_Count}")
# print(Check_if_New_Trip_Generated("Dummy,60"))
# print(f"Trip count:{Trip_Count}")

def Check_Trip_Details_Old(input):
    try:
        elements = driver.find_elements(
            AppiumBy.XPATH,
            "//android.widget.TextView"
        )

        Trip_timestamp = elements[3].text.strip()
        Start_Location = elements[4].text.strip()
        End_Location = elements[6].text.strip()
        result=f"Timestamp: {Trip_timestamp}\nStart_Location: {Start_Location}\nEnd_Location: {End_Location}"
        print(result)

        return f"Ok#{result}"
          
    except Exception as e:
        return f"Not ok#{str(e)}" 
    
def Check_Trip_Details(input):
    try:
        param,timestamp=input.split(",")
        loctation,address=param.split("$")
        location=location.lower().strip()
        address=address.lower().strip()
        
        elements = driver.find_elements(
            AppiumBy.XPATH,
            "//android.widget.TextView"
        )

        Trip_timestamp = elements[3].text.strip()
        Start_Location = elements[4].text.strip()
        End_Location = elements[6].text.strip()
        result=f"Timestamp: {Trip_timestamp}\nStart_Location: {Start_Location}\nEnd_Location: {End_Location}"
        
        if location == "start":
            if address==Start_Location:
                return f"Ok#Start location matched successfully, received start location is {Start_Location}"
            else:
                return f"Not ok#Start location is not matched successfully, received start location is {Start_Location}"

        if location == "end":
            if address==End_Location:
                return f"Ok#End location matched successfully, received start location is {Start_Location}"
            else:
                return f"Not ok#End location is not matched successfully, received start location is {Start_Location}"
            
        return f"Not ok#Input is incorect"
                    
    except Exception as e:
        return f"Not ok#{str(e)}" 


def Check_Trip_Score_Info_Text_Old(params, _retry=0):
    global Trip_Count

    try:
        target_text, param2 = params.split(",")
        target_text=target_text.lower().strip()
        Trips=[]
        insert=0

        elements = driver.find_elements(
            AppiumBy.XPATH,
            "//android.widget.TextView"
        )
        text_para = " ".join([el.text for el in elements if el.text])
        text_para=text_para.lower().strip()

        print(text_para)

        if target_text in text_para:
            return f"Ok#The required data {target_text} is updated on mobile phone successfully"
        
        return f"Not ok#The required data {target_text} is not updated on mobile phone successfully"
            
    except ValueError:
        return "Not ok#Invalid input format. Expected: param1,param2"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                sleep(1)
                return Check_Privious_Trip_Count(params, _retry=_retry + 1)

            return "Not ok#UIA2 session recovery failed after retries"

        return f"Not ok#{str(e)}"

def Check_Trip_Score_Overview_Text_Old(params, _retry=0):
    global Trip_Count

    try:
        target_text, param2 = params.split(",")
        target_text=target_text.lower().strip()
        Trips=[]
        insert=0

        elements = driver.find_elements(
            AppiumBy.XPATH,
            "//android.widget.TextView"
        )
        text_para = [el.text for el in elements if el.text]
        

        print(text_para)

        if target_text in text_para:
            return f"Ok#The required data {target_text} is updated on mobile phone successfully"
        
        return f"Not ok#The required data {target_text} is not updated on mobile phone successfully"
            
    except ValueError:
        return "Not ok#Invalid input format. Expected: param1,param2"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                sleep(1)
                return Check_Privious_Trip_Count(params, _retry=_retry + 1)

            return "Not ok#UIA2 session recovery failed after retries"

        return f"Not ok#{str(e)}"

def Click_on_latest_trip_generated(input):
    try:
        param1,param2=input.split(",")
        # ✅ Check if Trips list is empty or not
        if not Trips or len(Trips) == 0:
            return "Not ok#Trips list is empty"

        text = Trips[0]

        element = driver.find_element(AppiumBy.XPATH, f"//*[@text='{text}']")
        element.click()

        return "Ok#Clicked on latest trip"

    except Exception as e:
        return f"Not ok#{str(e)}"

# init_driver()
# print(Check_Privious_Trip_Count("Dummy,10"))
# print(Click_on_latest_trip_generated("Dummy,10"))

def Merge_N_Trips_text(input):
    try:
        n, timeout = input.split(",")
        n = int(n)
        timeout = int(timeout)

        for i in range(n):

            # Re-fetch checkboxes every iteration (avoids stale element)
            checkboxes = driver.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.CheckBox"
            )

            count = len(checkboxes)
            print(f"Total Checkboxes Found: {count}")

            if i < count:
                checkboxes[i].click()
            else:
                return f"Not ok: Only {count} checkboxes available"

            # sleep(timeout)

        return "Ok#Successfully selected the trips"

    except Exception as e:
        return f"Not ok: {str(e)}"
    
# init_driver()
# print(Compare_Screen_By_Text("Unable to process the remote command,10"))


############################### Trip END ##################################
    
################# Main Screen Vehicle Status #############
def Check_VehStatus_OnMainnScrn_Text(input):
    try:
        counter=0
        n=0
        param,_=input.split(",")
        valid,condition=param.split("_")
        elements = driver.find_elements(
            AppiumBy.XPATH,
            "//android.widget.TextView"
        )
        for i in elements:
            if i.text.lower().strip() =="vehicle status":
                n=counter
            counter+=1
            print(i.text)
            print(counter)
            
        print(n)
        
        status=elements[n+1].text.lower().strip()
        
        if valid.strip().lower()==status and condition=="received":
            return f"Ok#{valid} status is updated on mobile successfully"
        elif valid.strip().lower()==status and condition=="not received":
            return f"Not ok#{valid} status is updated on mobile successfully"
        else:
            return f"Not ok#{valid} status is not updated on mobile successfully"
          
    except Exception as e:
        return f"Not ok#{str(e)}" 
    
# def Check_Notification_InApp_Text(input):
#     try:
#         AlertTime = []
#         Alerts = []

#         param, _ = input.split(",")
#         valid, condition = param.split("_")

#         elements = driver.find_elements(
#             AppiumBy.XPATH,
#             "//android.widget.TextView"
#         )

#         for idx, el in enumerate(elements):
#             if "sierra" in el.text.lower().strip():
#                 AlertTime.append(elements[idx - 1].text)
#                 Alerts.append(el.text)

#         print(Alerts)
#         print(AlertTime)

#         for i, alert in enumerate(Alerts):

#             print(AlertTime[i])

#             # Extract number
#             result = int(re.search(r'\d+', AlertTime[i]).group())
#             print(result)

#             if valid.lower().strip() in alert.lower().strip():

#                 if "h" in AlertTime[i].lower():
#                     if result < 17 and condition.lower().strip() == "received":
#                         return f"Ok#{valid} alert received in mobile application"
#                     elif result < 17 and condition.lower().strip() == "not received":
#                         return f"Not ok#{valid} alert received in mobile application"

            
                

#         return f"Not ok#{valid} alert is not received in mobile application"

#     except Exception as e:
#         return f"Not ok#{str(e)}"

############################### In APP Notification Check ########################

def Check_Notification_InApp_Text(input):
    try:
        AlertTime = []
        Alerts = []

        param, timeout = input.split(",")
        valid, condition = param.split("$")
        timeout = int(timeout)
        valid = valid.lower().strip()
        condition = condition.lower().strip()

        for t in range(timeout):
            sleep(1)

            # Reset lists every retry
            Alerts.clear()
            AlertTime.clear()

            elements = driver.find_elements(
                AppiumBy.XPATH,
                "//android.widget.TextView"
            )

            # Extract alerts + time
            for idx, el in enumerate(elements):
                text = el.text.lower().strip()

                if "sierra" in text or "rowa" in text:
                    Alerts.append(el.text)
                    AlertTime.append(elements[idx-1].text if idx > 0 else "")

            print(Alerts)
            print(AlertTime)

            # Process extracted data
            for j, alert in enumerate(Alerts):
                alert_text = alert.lower().strip()
                time_text = AlertTime[j].lower().strip()

                print(alert_text)
                print(valid)

                if valid in alert_text:
                    capture_screenshot(Ref_Img_Path)
                    curr_img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_path = f"NotificatioInApp_Screenshot__{timestamp}.png"
                    full_path = os.path.join(Screenshot_path, save_path)
                    # Save the image
                    cv2.imwrite(full_path, curr_img)

                    # ✅ Case 1: immediate
                    if time_text in ["just now", "a min ago"]:
                        if condition == "received":
                            return f"Ok#{valid} alert received in mobile application+{full_path}"
                        else:
                            return f"Not ok#{valid} alert received in mobile application+{full_path}"

                    # ✅ Case 2: minutes
                    elif "mins" in time_text:
                        match = re.search(r'\d+', time_text)

                        if match:
                            result = int(match.group())

                            if result <= 1 and condition == "received":
                                return f"Ok#{valid} alert received in mobile application+{full_path}"
                            elif result <= 1 and condition == "not received":
                                return f"Not ok#{valid} alert received in mobile application+{full_path}"

                    # ✅ Case 3: hours
                    elif "h" in time_text:
                        if condition != "received":
                            return f"Ok#{valid} alert is not received in mobile application+{full_path}"
                        else:
                            return f"Not ok#{valid} alert is not received in mobile application+{full_path}"

                    
        capture_screenshot(Ref_Img_Path)
        curr_img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"NotoficationInApp_Screenshot__{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)
        
        if condition == "not received":
            return f"Ok#{valid} alert is not received in mobile application+{full_path}"
        else:
            return f"Not ok#{valid} alert is not received in mobile application+{full_path}"

    except Exception as e:
        return f"Not ok#{str(e)}"

# init_driver()
# print(Check_Notification_InApp_Text("Abrupt Charging Cut-off Alert$received,10"))
    
def Click_On_Notification_Icon(input):
    try:
        elements = driver.find_elements(AppiumBy.XPATH, "//android.widget.ImageView")

        for el in elements:
            loc = el.location
            size = driver.get_window_size()

            # Check if element is in top-right area
            if loc['x'] > size['width'] * 0.7 and loc['y'] < size['height'] * 0.2:
                el.click()
                return "Ok#Bell icon clicked"

        return "Not ok#Bell icon not found"

    except Exception as e:
        return f"Not ok#{str(e)}"
    
# init_driver()
# print(click_bell_by_nearby_element())
# print( Check_Notification_InApp_Text("Service-due alert_received,10"))


Vald_image_paths = [
    "C:\\MaxEye\\MEP00179\\Application\\Configuration_Files\\Appium\\Operational Images\\Approach_On_01.png",
    "C:\\MaxEye\\MEP00179\\Application\\Configuration_Files\\Appium\\Operational Images\\Hazard_On_01.png",
    "C:\\MaxEye\\MEP00179\\Application\\Configuration_Files\\Appium\\Operational Images\\Position_On_01.png"
]
Feature_name = [
    "Approach",
    "Hazard",
    "Position"
]

def Verify_Status_In_Diff_Sec_Text(input_str):
    """
    Input:
        "image_path,threshold"

    Example:
        "lock_glow.png,0.75"

    Output:
        Ok#PASS (Matched: 0.87)
        Not Ok#FAIL (Matched: 0.45)
    """

    try:
        parts = input_str.split(",")
        input=parts[0].strip()
        search,valid=input.split("_")

        if len(parts) < 2:
            return "Not Ok#Invalid input"
        
        index = next((i for i, val in enumerate(Feature_name) if val.lower() == search.lower()), -1)

        image_path = Vald_image_paths[index].strip()
        threshold = 0.9

        if not os.path.exists(image_path):
            return "Not Ok#Reference image not found"

        # 📸 Screenshot
        screenshot_base64 = driver.get_screenshot_as_base64()
        screenshot_bytes = base64.b64decode(screenshot_base64)

        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        screen_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        template = cv2.imread(image_path, cv2.IMREAD_COLOR)

        if template is None:
            return "Not Ok#Template load failed"

        best_score = 0

        # 🔥 MULTI-SCALE MATCHING (KEY IMPROVEMENT)
        for scale in np.linspace(0.6, 1.4, 15):
            resized = cv2.resize(template, None, fx=scale, fy=scale)

            h, w = resized.shape[:2]
            if h > screen_img.shape[0] or w > screen_img.shape[1]:
                continue

            result = cv2.matchTemplate(screen_img, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val > best_score:
                best_score = max_val

        print(f"Best Match Score: {best_score}")
        
        capture_screenshot(Ref_Img_Path)
        curr_img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"Ref_Screenshot__{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)
        
        #{round(best_score, 2)})

        if best_score >= threshold  and valid.lower().strip()=="on":
            return f"Ok#{search} status is updated in mobile app+{full_path}"
        elif best_score >= threshold  and valid.lower().strip()=="off":
            return f"Not ok#{search} status is updated in mobile app+{full_path}"
        else:
            return f"Not ok#{search} status is not updated in mobile app+{full_path}"
        
    except Exception as e:
        return f"Not ok#Error: {str(e)}"
    
# init_driver()
# print(Verify_Status_In_Diff_Sec_Text("Approach_On,10"))

def Swipe_Up_New(input, _retry=0):
    try:
        # ✅ Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        size = driver.get_window_size()
        width, height = size["width"], size["height"]

        start_x = width // 2

        # 🔥 Increase swipe distance (VERY IMPORTANT)
        start_y = int(height * 0.85)
        end_y   = int(height * 0.25)

        # 🔥 Capture screen before swipe
        before = driver.page_source

        driver.swipe(start_x, start_y, start_x, end_y, 800)

        time.sleep(1)  # allow UI to settle

        # 🔥 Verify scroll actually happened
        after = driver.page_source

        if before == after:
            safe_print("[WARN] Swipe executed but no UI change detected")

            # 👉 Retry with slightly different swipe
            if _retry < 2:
                safe_print(f"[RETRY] Adjusting swipe... Attempt {_retry+1}")

                start_y = int(height * 0.95)
                end_y   = int(height * 0.20)

                driver.swipe(start_x, start_y, start_x, end_y, 1000)
                time.sleep(1)

                return Swipe_Up_New(input, _retry=_retry + 1)

        return "Ok#Swiped up"

    except Exception as e:

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                sleep(1)
                return Swipe_Up_New(input, _retry=_retry + 1)

            return "Not ok# UIA2 session recovery failed after retries"

        return f"Not ok# {str(e)}"
    

    
###################################  Range validation Helper Function ####################################
    
def evaluate(value, operator, target):
    if operator == ">":
        return value > target
    elif operator == "<":
        return value < target
    elif operator == ">=":
        return value >= target
    elif operator == "<=":
        return value <= target
    elif operator == "==":
        return value == target
    return False

def parse_condition(cond):
    conditions = re.findall(r"(>=|<=|>|<|==)\s*([\d.]+)", cond)
    logic = re.findall(r"\b(and|or)\b", cond.lower())

    conditions = [(op, float(val)) for op, val in conditions]

    return conditions, logic

# print(parse_condition(">10 and <20"))
def validate(value, conditions, logic):
    if not conditions:
        return False   # safety check

    results = [evaluate(value, op, val) for op, val in conditions]

    # ✅ Single condition
    if len(conditions) == 1:
        return results[0]

    # ✅ Multiple conditions
    final = results[0]
    for i, op in enumerate(logic):
        if op == "and":
            final = final and results[i + 1]
        elif op == "or":
            final = final or results[i + 1]

    return final

###################### Monthly health report ##################

# def Check_Monthly_HealthReport_Text(input):

#     try:
#         # ===== INPUT PARSING =====
#         try:
#             validation_text, timeout = input.split(",")
#             validation_text = validation_text.lower().strip()
#             timeout = int(timeout)
#         except:
#             return "Not Ok# Invalid input format. Expected: text,timeout"

#         Scroll_Stopper = 0
#         data = []

#         summary = [
#             "drive time",
#             "distance",
#             "average speed",
#             "maximum speed",
#             "idling fuel",
#             "fuel economy"
#         ]

#         drive_info = [
#             "acceleration",
#             "deceleration",
#             "cruising",
#             "idling"
#         ]

#         score_section = [
#             "driving score",
#             "efficiency",
#             "safety",
#             "performance"
#         ]

#         output = ""
#         start_time = time.time()

#         # ===== MAIN LOOP =====
#         while Scroll_Stopper < 3:
#             Curr_Time=time.time() - start_time
#             # print(f"Current time{Curr_Time}")

#             # ⏱️ Timeout protection
#             if time.time() - start_time > timeout:
#                 return "Not Ok# Timeout exceeded while searching"

#             try:
#                 elements = driver.find_elements(AppiumBy.XPATH, "//android.widget.TextView")
#             except Exception as e:
#                 return f"Not Ok# Failed to fetch elements: {str(e)}"

#             for i, el in enumerate(elements):

#                 try:
#                     text = el.text.lower().strip()
#                 except:
#                     continue

#                 if not text:
#                     continue

#                 value = ""

#                 try:
#                     # ===== SUMMARY =====
#                     if text in summary:

#                         if i > 0 and elements[i - 1].text.strip():
#                             value = elements[i - 1].text.strip()
#                         elif i < len(elements) - 1:
#                             value = elements[i + 1].text.strip()

#                         output += f"{text} {value} | "
#                         Scroll_Stopper = max(Scroll_Stopper, 1)

#                     # ===== DRIVING =====
#                     elif text in drive_info:

#                         if i < len(elements) - 1 and elements[i + 1].text.strip():
#                             value = elements[i + 1].text.strip()
#                         elif i > 0:
#                             value = elements[i - 1].text.strip()

#                         output += f"{text} {value} | "
#                         Scroll_Stopper = max(Scroll_Stopper, 2)

#                     # ===== SCORE =====
#                     elif text in score_section:

#                         if i < len(elements) - 1 and elements[i + 1].text.strip():
#                             value = elements[i + 1].text.strip()
#                         elif i > 0:
#                             value = elements[i - 1].text.strip()

#                         output += f"{text} {value} | "
#                         Scroll_Stopper = 3
                        
                    
                     
#                     # print(f"Scrolling stopper:{Scroll_Stopper}")

#                 except Exception as inner_error:
#                     # Skip faulty element safely
#                     continue
                
#                 # print(output)

#                 # ===== VALIDATION =====
#                 if validation_text in output:
#                     return f"Ok#Required {validation_text} is updated on mobile screen successfully"
                
#                 # if Scroll_Stopper>2:
                    
#                 #         return f"Not Ok#Required {validation_text} is not updated on mobile screen successfully"

#             # ===== SCROLL =====
#             try:
#                 status = Swipe_Up_New("dummy,10")

#                 if "Not Ok" in status:
#                     return f"Not Ok# Scroll failed: {status}"

#             except Exception as scroll_error:
#                 return f"Not Ok# Scroll exception: {str(scroll_error)}"

#             print("Swipe........")
#             time.sleep(1)

#         # ===== FINAL CHECK =====
#         if validation_text in output:
#             return f"Ok#Required {validation_text} is updated on mobile screen successfully"
#         else:
#             return f"Not Ok#Required {validation_text} not found"

#     except Exception as e:
#         return f"Not Ok# Unexpected error: {str(e)}"



# ✅ CONFIG: Fixed tolerance
FIXED_TOLERANCE = 5

def convert_to_seconds(time_text):
    time_text = time_text.lower()

    hours = 0
    minutes = 0
    seconds = 0

    # Extract hours
    hr_match = re.search(r"(\d+)\s*hr", time_text)
    if hr_match:
        hours = int(hr_match.group(1))

    # Extract minutes
    min_match = re.search(r"(\d+)\s*min", time_text)
    if min_match:
        minutes = int(min_match.group(1))

    # Extract seconds (optional)
    sec_match = re.search(r"(\d+)\s*sec", time_text)
    if sec_match:
        seconds = int(sec_match.group(1))

    total_seconds = (hours * 3600) + (minutes * 60) + seconds
    return total_seconds

# -------------------------------
# Extract number from string
# -------------------------------
def extract_number(text):
    match = re.search(r"\d+\.?\d*", text)
    return float(match.group()) if match else None


# -------------------------------
# Parse validation input
# Example: "Distance 20 km"
# -------------------------------
def parse_validation_input(validation_text):
    text = validation_text.lower()

    # Extract number (expected value)
    value_match = re.search(r"\d+\.?\d*", text)
    expected_value = float(value_match.group()) if value_match else None

    # Remove number & common units → get metric
    metric = re.sub(r"\d+\.?\d*", "", text)
    metric = metric.replace("km", "").replace("%", "").replace("h", "").replace("/", "").strip()

    return metric, expected_value


# -------------------------------
# MAIN FUNCTION
# -------------------------------
def Check_Monthly_HealthReport_Text(input):

    try:
        # ===== INPUT PARSING =====
        try:
            validation_text, timeout = input.split(",")
            validation_text = validation_text.strip()
            timeout = int(timeout)
        except:
            return "Not Ok# Invalid input format. Expected: text,timeout", []

        Scroll_Stopper = 0

        summary = [
            "drive time",
            "distance",
            "average speed",
            "maximum speed",
            "idling fuel",
            "fuel economy"
        ]

        drive_info = [
            "acceleration",
            "deceleration",
            "cruising",
            "idling"
        ]

        score_section = [
            "driving score",
            "efficiency",
            "safety",
            "performance"
        ]

        # ✅ 2D ARRAY STORAGE
        data = []

        start_time = time.time()

        # ===== MAIN LOOP =====
        while Scroll_Stopper <= 3:

            # ⏱️ Timeout check
            if time.time() - start_time > timeout:
                return "Not Ok# Timeout exceeded", data

            try:
                elements = driver.find_elements(AppiumBy.XPATH, "//android.widget.TextView")
            except Exception as e:
                return f"Not Ok# Failed to fetch elements: {str(e)}", data

            for i, el in enumerate(elements):

                try:
                    text = el.text.lower().strip()
                except:
                    continue

                if not text:
                    continue

                value = ""
                # print(text)

                try:
                    print(text)
                    # ===== SUMMARY =====
                    if text in summary:

                        if i > 0 and elements[i - 1].text.strip():
                            value = elements[i - 1].text.strip()
                        elif i < len(elements) - 1:
                            value = elements[i + 1].text.strip()

                        if [text, value] not in data:
                            if text == "drive time":
                                numeric_value = convert_to_seconds(value)
                            else:
                                numeric_value = value
                            numeric_value=str(numeric_value)
                            data.append([text, numeric_value])

                        Scroll_Stopper = max(Scroll_Stopper, 1)
                        
                    

                    # ===== DRIVING INFO =====
                    elif text in drive_info:
                        print(text)

                        if i < len(elements) - 1 and elements[i + 1].text.strip():
                            value = elements[i + 1].text.strip()
                        elif i > 0:
                            value = elements[i - 1].text.strip()

                        if [text, value] not in data:
                            if text == "drive time":
                                numeric_value = convert_to_seconds(value)
                            else:
                                numeric_value = value

                            data.append([text, numeric_value])

                        Scroll_Stopper = max(Scroll_Stopper, 2)

                    # ===== SCORE SECTION =====
                    elif text in score_section:

                        if i < len(elements) - 1 and elements[i + 1].text.strip():
                            value = elements[i + 1].text.strip()
                        elif i > 0:
                            value = elements[i - 1].text.strip()

                        if [text, value] not in data:
                            data.append([text, value])

                        Scroll_Stopper = 3

                except:
                    continue

                # ===== VALIDATION =====
                metric, expected_value = parse_validation_input(validation_text)
                # print(f"metric:{metric}")
                # print(f"expected:{expected_value}")

                for row in data:
                    row_metric = row[0].lower()
                    row_value = extract_number(row[1])
                    # print(f"Row value:{row_value}")

                    if metric in row_metric and row_value is not None:

                        lower = expected_value - FIXED_TOLERANCE
                        upper = expected_value + FIXED_TOLERANCE

                        if lower <= row_value <= upper:
                            return f"Ok# {metric} within range [{lower} - {upper}], Got {row_value}"
                        else:
                            return f"Not Ok# {metric} out of range [{lower} - {upper}], Got {row_value}"

            # ===== SCROLL =====
            try:
                status = Swipe_Up_New("dummy,10")

                if "Not Ok" in status:
                    return f"Not Ok# Scroll failed: {status}"

            except Exception as scroll_error:
                return f"Not Ok# Scroll exception: {str(scroll_error)}"

            print("Swipe........")
            time.sleep(1)

        # ===== FINAL CHECK =====
        return f"Not Ok# {validation_text} not found"

    except Exception as e:
        return f"Not Ok# Unexpected error: {str(e)}"
    
    
############################# Check Trip Info #######################
# -------------------------------
# MAIN FUNCTION
# -------------------------------
def Check_Trip_Score_Overview_Text(input):

    try:
        # ===== INPUT PARSING =====
        try:
            validation_text, timeout = input.split(",")
            validation_text = validation_text.strip().lower()
            timeout = int(timeout)
        except:
            return "Not Ok# Invalid input format. Expected: text,timeout", []

        Scroll_Stopper = 0

        summary = [
            "drive time",
            "distance",
            "average speed",
            "maximum speed",
            "score"
        ]
        score_section = [
            "efficiency",
            "safety",
            "performance"
        ]

        # ✅ 2D ARRAY STORAGE
        data = []

        start_time = time.time()

        # ===== MAIN LOOP =====
        while time.time() - start_time < timeout:

            try:
                elements = driver.find_elements(AppiumBy.XPATH, "//android.widget.TextView")
            except Exception as e:
                return f"Not Ok# Failed to fetch elements: {str(e)}", data

            for i, el in enumerate(elements):

                try:
                    text = el.text.lower().strip()
                    print(text)
                except:
                    continue

                if not text:
                    continue

                value = ""
                # print(text)

                try:
                    print(text)
                    # ===== SUMMARY =====
                    if text in summary:

                        if i > 0 and elements[i + 1].text.strip():
                            value = elements[i + 1].text.strip()
                        elif i < len(elements) - 1:
                            value = elements[i + 1].text.strip()

                        if [text, value] not in data:
                            if text == "drive time":
                                numeric_value = convert_to_seconds(value)
                            else:
                                numeric_value = value
                            numeric_value=str(numeric_value)
                            data.append([text, numeric_value])

                    
                    # ===== SCORE SECTION =====
                    elif text in score_section:

                        if i < len(elements) - 1 and elements[i - 1].text.strip():
                            value = elements[i - 1].text.strip()
                        elif i > 0:
                            value = elements[i - 1].text.strip()

                        if [text, value] not in data:
                            data.append([text, value])

                        

                except:
                    continue

                # ===== VALIDATION =====
                metric, expected_value = parse_validation_input(validation_text)
                # print(f"metric:{metric}")
                # print(f"expected:{expected_value}")
                
                print(data)

                for row in data:
                    row_metric = row[0].lower()
                    row_value = extract_number(row[1])
                    # print(f"Row value:{row_value}")

                    if metric in row_metric and row_value is not None:

                        lower = expected_value - FIXED_TOLERANCE
                        upper = expected_value + FIXED_TOLERANCE
                        metric=metric.upper()
                    # 1. Take screenshot with current date & time
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        screenshot_path = os.path.join(Screenshot_path, f"status_{timestamp}.png")
                        driver.save_screenshot(screenshot_path)
                        
                        if lower <= row_value <= upper: 
                            return f"Ok# {metric} within range and CAN calculated value is {expected_value} and Got {row_value}+{screenshot_path}"
                        else:                      
                            return f"Not Ok# {metric} out of range and CAN calculated value is {expected_value}, Got {row_value}+{screenshot_path}"

            # ===== SCROLL =====
            # try:
            #     # status = Swipe_Up_New("dummy,10")

            #     if "Not Ok" in status:
            #         return f"Not Ok# Scroll failed: {status}"

            # except Exception as scroll_error:
            #     return f"Not Ok# Scroll exception: {str(scroll_error)}"

            print("Swipe........")
            time.sleep(1)
                        # ⏱️ Timeout check
        if time.time() - start_time > timeout:
            return "Not Ok# Timeout exceeded"
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(Screenshot_path, f"status_{timestamp}.png")
        driver.save_screenshot(screenshot_path)

        # ===== FINAL CHECK =====
        return f"Not Ok# {validation_text} is not in range+{screenshot_path}"
        

    except Exception as e:
        return f"Not Ok# Unexpected error: {str(e)}"

    
# init_driver()
# print(Check_Trip_Score_Overview_Text("Drive time 120,60"))

# result, data = Check_Monthly_HealthReport_Text("average speed 19.2km/h,6")
# print(result)
# print(data)
    

###################   Regen  #################
    
def Fetch_regen_history(input):
    condition, timeout = input.split(",")

    conditions, logic = parse_condition(condition)
    print(condition)
    print(logic)

    elements = driver.find_elements(
        AppiumBy.XPATH,
        "//android.widget.TextView"
    )

    output = []

    for ind, ele in enumerate(elements):
        text = ele.text.lower().strip()

        if text == "energy regeneration" or text == "range gained":
            if ind + 2 < len(elements):
                output.append(elements[ind + 2].text)

    numbers = [float(re.findall(r"[\d.]+", i)[0]) for i in output]
    # numbers=[10.4,10.9]

    print("Extracted:", numbers)

    # 🔥 Apply validation
    results = []
    for num in numbers:
        res = validate(num, conditions, logic)
        results.append(res)

    print("Validation:", results)

    # Final decision
    if all(results):
        return "Ok#All values passed"
    else:
        return "Not Ok#Condition failed"
    
def ClickOnFirstLocation(input):

    try:
        input=""
        elements = driver.find_elements(
            AppiumBy.XPATH,
            "//android.widget.TextView"
        )

        if not elements:
            return "Not ok# No elements found"

        index = -1

        for ind, ele in enumerate(elements):
            try:
                text = ele.text.lower().strip()
                print(text)

                if text == "results":
                    index = ind

            except Exception as e:
                continue

        # ❌ If "results" not found
        if index == -1:
            return "Not ok# 'results' text not found"

        # ❌ Prevent index out of range
        if index + 1 >= len(elements):
            return "Not ok# No location found after 'results'"

        try:
            next_text = elements[index + 1].text.strip()
        except Exception as e:
            return f"Not ok# Failed to read next element: {str(e)}"

        input = f"{next_text},10"

        try:
            result = Click_By_Text(input)
            print(result)
        except Exception as e:
            return f"Not ok# Click_By_Text failed: {str(e)}"

        return "Ok#Clicked on location successfully"

    except Exception as e:
        return f"Not ok# Unexpected error: {str(e)}"
    
# init_driver()
# print(ClickOnFirstLocation("dummy,10"))
    
    
########################### NEW ############################

def SendRmtCmd_VehStat_Screen(input):
    try:
        # input format: "hazard,10"
        try:
            label_name, timeout = input.split(",")
            label_name = label_name.strip().lower()
            timeout = int(timeout)
        except Exception:
            return "Not Ok#Invalid input format. Expected: label,timeout"

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Find all text views
                text_elements = driver.find_elements(AppiumBy.XPATH, "//android.widget.TextView")
            except Exception as e:
                return f"Not Ok#Unable to fetch text elements: {str(e)}"

            target_label = None

            # Step 1: find matching label
            for el in text_elements:
                try:
                    txt = el.text.strip().lower()
                    if label_name in txt:
                        target_label = el
                        print(f"Matched label: {txt}")
                        break
                except Exception:
                    continue

            if not target_label:
                time.sleep(1)
                continue

            try:
                label_loc = target_label.location
                label_size = target_label.size
                label_center_y = label_loc["y"] + (label_size["height"] / 2)
                label_right_x = label_loc["x"] + label_size["width"]
            except Exception as e:
                return f"Not Ok#Unable to read label position: {str(e)}"

            # Step 2: find all possible toggles/switches/checkable widgets
            toggle_xpaths = [
                "//android.widget.Switch",
                "//android.widget.ToggleButton",
                "//android.widget.CheckBox",
                "//*[@checkable='true']"
            ]

            toggle_candidates = []
            for xp in toggle_xpaths:
                try:
                    elems = driver.find_elements(AppiumBy.XPATH, xp)
                    for e in elems:
                        if e not in toggle_candidates:
                            toggle_candidates.append(e)
                except Exception:
                    pass

            if not toggle_candidates:
                return "Not Ok#No toggle candidates found"

            # Step 3: choose switch in same horizontal row
            best_toggle = None
            best_y_diff = float("inf")

            for toggle in toggle_candidates:
                try:
                    t_loc = toggle.location
                    t_size = toggle.size

                    toggle_center_y = t_loc["y"] + (t_size["height"] / 2)
                    toggle_left_x = t_loc["x"]

                    y_diff = abs(toggle_center_y - label_center_y)

                    # Must be to the right of label
                    if toggle_left_x <= label_right_x:
                        continue

                    # Threshold for same row, can tune this
                    if y_diff <= 40:
                        if y_diff < best_y_diff:
                            best_y_diff = y_diff
                            best_toggle = toggle

                except Exception:
                    continue

            if best_toggle:
                try:
                    best_toggle.click()
                    return f"Ok#Clicked toggle for {label_name}"
                except Exception as e:
                    return f"Not Ok#Toggle found but click failed: {str(e)}"

            time.sleep(1)

        return f"Not Ok#{label_name} label or matching toggle not found within timeout"

    except Exception as e:
        return f"Not Ok#{str(e)}"
    

def Click_Delete_Icon(input):
    try:
        param,timeout=input.split(",")

        timeout = int(str(timeout).strip())
        start_time = time.time()

        while time.time() - start_time < timeout:

            # 1. Try common direct locators first
            direct_locators = [
                (AppiumBy.ACCESSIBILITY_ID, "Delete"),
                (AppiumBy.ACCESSIBILITY_ID, "delete"),
                (AppiumBy.XPATH, "//*[@content-desc='Delete']"),
                (AppiumBy.XPATH, "//*[@content-desc='delete']"),
                (AppiumBy.XPATH, "//*[contains(@content-desc,'Delete')]"),
                (AppiumBy.XPATH, "//*[contains(@content-desc,'delete')]"),
                (AppiumBy.XPATH, "//*[contains(@resource-id,'delete')]"),
                (AppiumBy.XPATH, "//*[contains(@resource-id,'Delete')]"),
            ]

            for by, value in direct_locators:
                try:
                    ele = driver.find_element(by, value)
                    if ele.is_displayed():
                        ele.click()
                        return "Ok#Delete icon clicked"
                except:
                    pass

            # 2. Fallback: detect unique small clickable icon automatically
            candidates = []
            xpaths = [
                "//android.widget.ImageView",
                "//android.widget.ImageButton",
                "//*[@clickable='true']",
            ]

            for xp in xpaths:
                try:
                    elems = driver.find_elements(AppiumBy.XPATH, xp)
                    for e in elems:
                        if e not in candidates:
                            candidates.append(e)
                except:
                    pass

            valid_icons = []

            for e in candidates:
                try:
                    if not e.is_displayed():
                        continue

                    loc = e.location
                    size = e.size

                    x = loc.get("x", 0)
                    y = loc.get("y", 0)
                    w = size.get("width", 0)
                    h = size.get("height", 0)

                    # Skip huge containers / invisible-like elements
                    if w <= 0 or h <= 0:
                        continue
                    if w > 120 or h > 120:
                        continue

                    # Normally delete icon is a small tappable element
                    area = w * h
                    valid_icons.append((e, x, y, w, h, area))
                except:
                    continue

            if len(valid_icons) == 1:
                try:
                    valid_icons[0][0].click()
                    return "Ok#Delete icon clicked"
                except Exception as e:
                    return f"Not Ok#Delete icon found but click failed: {str(e)}"

            # 3. If multiple small icons found, prefer top-right one
            if len(valid_icons) > 1:
                try:
                    # choose rightmost, then upper one
                    valid_icons.sort(key=lambda item: (-item[1], item[2]))
                    valid_icons[0][0].click()
                    return "Ok#Delete icon clicked"
                except Exception as e:
                    return f"Not Ok#Delete icon candidate found but click failed: {str(e)}"

            time.sleep(1)

        return "Not Ok#Delete icon not found within timeout"

    except Exception as e:
        return f"Not Ok#{str(e)}"





#####################################################################################################
#################################### CHARGING ANALYTICS MAIN ########################################
#####################################################################################################


#************************************ CHARGING HEALTH PATTERN MAIN **********************************

import os
import cv2
import numpy as np
from datetime import datetime
from time import sleep

# scikit-image for skeletonization  (pip install scikit-image)
from skimage.morphology import skeletonize as ski_skeletonize

# Appium
from appium import webdriver as appium_webdriver
from appium.webdriver.common.appiumby import AppiumBy

# ---------------------------------------------------------------------------
#  YOUR EXISTING CONFIG — keep these as-is from your original file
# ---------------------------------------------------------------------------
# driver          = ...   (your Appium driver instance)
# temp_path       = ...   (temporary screenshot path)
# Screenshot_path = ...   (final screenshots folder)
# file_to_watch   = ...   (abort signal file path)
# ENABLE_TEXT_CROSSCHECK = ...
#
# safe_print(...)           — your thread-safe print wrapper
# init_driver()             — your driver initialisation
# recover_uia2_session()    — your UIA2 recovery helper
# is_uia2_socket_error(...) — your error classifier
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
#  Screenshot
# ---------------------------------------------------------------------------

def capture_screenshot(path):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        driver.save_screenshot(path)
        if not os.path.exists(path):
            return "Not ok#Screenshot file not created"
        return "Ok"
    except Exception as e:
        return f"Not ok#{e}"


# ---------------------------------------------------------------------------
#  GRAPH AREA DETECTION
#  Finds the bounding box of the line chart in physical pixels.
# ---------------------------------------------------------------------------

def _get_graph_bounds(img_h, img_w):
    """
    Ask Appium for the percentage label elements ("100%", "75%", etc.)
    to derive the chart's top and bottom Y in physical pixels.

    Returns (top_px, bottom_px, left_px, right_px).
    Falls back to a heuristic if elements are not found.

    Layout assumption (fallback):
        - Chart occupies roughly y: 20%–65% of screen height
        - Chart occupies roughly x: 5%–95% of screen width
    """
    scale = 1.0

    try:
        driver.implicitly_wait(2)
        win = driver.get_window_size()
        screen_h_logical = win["height"]
        scale = img_h / screen_h_logical
    except Exception:
        pass
    finally:
        driver.implicitly_wait(0.5)

    top_logical    = None
    bottom_logical = None

    label_candidates_top    = ["100%", "100 %"]
    label_candidates_bottom = ["25%", "0%", "25 %", "0 %", "25%\n", "0%\n"]

    try:
        driver.implicitly_wait(2)

        for lbl in label_candidates_top:
            els = driver.find_elements(
                AppiumBy.XPATH,
                f"//*[@text='{lbl}' or @content-desc='{lbl}']"
            )
            if els:
                loc = els[0].location
                sz  = els[0].size
                top_logical = loc["y"] + sz["height"] // 2
                safe_print(f"[GRAPH] Top anchor '{lbl}' at logical y={top_logical}")
                break

        for lbl in label_candidates_bottom:
            els = driver.find_elements(
                AppiumBy.XPATH,
                f"//*[@text='{lbl}' or @content-desc='{lbl}']"
            )
            if els:
                loc = els[0].location
                sz  = els[0].size
                bottom_logical = loc["y"] + sz["height"] // 2
                safe_print(f"[GRAPH] Bottom anchor '{lbl}' at logical y={bottom_logical}")
                break

        chart_left_logical  = None
        chart_right_logical = None
        card_els = driver.find_elements(
            AppiumBy.XPATH,
            "//*[contains(@resource-id,'chart') or contains(@resource-id,'graph')]"
        )
        if card_els:
            loc = card_els[0].location
            sz  = card_els[0].size
            chart_left_logical  = loc["x"]
            chart_right_logical = loc["x"] + sz["width"]

    except Exception as e:
        safe_print(f"[GRAPH] Anchor search failed: {e}")
    finally:
        driver.implicitly_wait(0.5)

    margin_v = int(10 * scale)
    margin_h = int(30 * scale)

    top    = int(top_logical    * scale) - margin_v if top_logical    else int(img_h * 0.20)
    bottom = int(bottom_logical * scale) + margin_v if bottom_logical else int(img_h * 0.55)
    left   = int(chart_left_logical  * scale) + margin_h if chart_left_logical  else int(img_w * 0.10)
    right  = int(chart_right_logical * scale) - margin_h if chart_right_logical else int(img_w * 0.95)

    # Hard cap: bottom must never exceed 62% of screen height
    hard_bottom_cap = int(img_h * 0.62)
    if bottom > hard_bottom_cap:
        safe_print(f"[GRAPH] Bottom clamped {bottom} → {hard_bottom_cap} (hard cap 62%)")
        bottom = hard_bottom_cap

    top    = max(0, min(top,    img_h - 1))
    bottom = max(top + 10, min(bottom, img_h))
    left   = max(0, min(left,  img_w - 1))
    right  = max(left + 10, min(right, img_w))

    safe_print(f"[GRAPH] Bounds (physical px): top={top}, bottom={bottom}, "
               f"left={left}, right={right}")
    return top, bottom, left, right


# ---------------------------------------------------------------------------
#  SKELETON UTILITIES
# ---------------------------------------------------------------------------

def _skeletonize_mask(binary_mask):
    """
    Thin a binary mask to a 1-pixel-wide skeleton using skimage.

    Parameters
    ----------
    binary_mask : uint8 ndarray, values 0 or 255

    Returns
    -------
    skeleton : uint8 ndarray, values 0 or 255
    """
    bool_mask = binary_mask > 0
    skel_bool = ski_skeletonize(bool_mask)
    return skel_bool.astype(np.uint8) * 255


def _sort_skeleton_pixels(skeleton):
    """
    Return skeleton pixels as an ordered list of (x, y) tuples,
    traversed left-to-right (primary) then top-to-bottom (secondary).

    For a multi-branch skeleton this gives a reasonable single-pass order.
    """
    ys, xs = np.where(skeleton > 0)
    if len(xs) == 0:
        return []
    pts = sorted(zip(xs.tolist(), ys.tolist()), key=lambda p: (p[0], p[1]))
    return pts


def _compute_direction(pts, idx, window):
    """
    Compute the 2-D direction vector at pts[idx] using a forward window.
    Returns (dx, dy) normalised, or None if out of range.
    """
    if idx + window >= len(pts):
        return None
    dx = pts[idx + window][0] - pts[idx][0]
    dy = pts[idx + window][1] - pts[idx][1]
    mag = np.hypot(dx, dy)
    if mag < 1e-6:
        return None
    return dx / mag, dy / mag


def _angle_between(v1, v2):
    """Angle in degrees between two unit vectors."""
    dot = np.clip(v1[0] * v2[0] + v1[1] * v2[1], -1.0, 1.0)
    return np.degrees(np.arccos(dot))


# ---------------------------------------------------------------------------
#  BEND DETECTION ON A SINGLE SKELETON BLOB
# ---------------------------------------------------------------------------

def _count_sessions_in_skeleton(skeleton,
                                 bend_angle_threshold=30,
                                 window=12,
                                 min_gap_between_bends=15):
    """
    Count sessions in ONE connected skeleton blob by detecting bend points.

    Algorithm
    ---------
    1. Sort skeleton pixels left-to-right.
    2. Slide a direction window along the path.
    3. Where the direction changes by more than `bend_angle_threshold` degrees
       that pixel is a bend point → starts a new session.
    4. Enforce a minimum pixel gap between consecutive bend detections to avoid
       double-counting the same bend.

    Parameters
    ----------
    skeleton               : uint8 ndarray — 1-px-wide skeleton of ONE blob
    bend_angle_threshold   : degrees — direction change > this = new session
                             30° works well for gentle charging curves;
                             lower = more sensitive, higher = less sensitive
    window                 : pixels ahead used to compute direction vector
                             larger = smoother, less noise-sensitive
    min_gap_between_bends  : minimum x-distance between two accepted bends

    Returns
    -------
    (session_count, bend_xy_list)
      session_count  : int  — number of sessions detected (≥1 if any pixels)
      bend_xy_list   : list of (x, y) tuples at each detected bend point
    """
    pts = _sort_skeleton_pixels(skeleton)
    if len(pts) < window * 2:
        # Too short to detect bends — treat as 1 session
        return (1 if len(pts) > 0 else 0), []

    sessions    = 1
    bend_points = []
    last_bend_x = pts[0][0] - min_gap_between_bends  # allow first bend anywhere

    for i in range(0, len(pts) - window, max(1, window // 2)):
        v1 = _compute_direction(pts, max(0, i - window), window)
        v2 = _compute_direction(pts, i, window)

        if v1 is None or v2 is None:
            continue

        angle = _angle_between(v1, v2)

        if angle > bend_angle_threshold:
            x, y = pts[i]
            if (x - last_bend_x) >= min_gap_between_bends:
                sessions += 1
                bend_points.append((x, y))
                last_bend_x = x
                safe_print(f"  [BEND] x={x} y={y}  angle={angle:.1f}°  → session {sessions}")

    return sessions, bend_points


# ---------------------------------------------------------------------------
#  FULL SESSION COUNTING: gaps + bends
# ---------------------------------------------------------------------------

# def _count_sessions_from_mask(mask,
#                                min_area=300,
#                                bend_angle_threshold=30,
#                                window=12,
#                                min_gap_between_bends=15):
#     """
#     Count total charging sessions in a colour mask.

#     Strategy
#     --------
#     1. Connected-component analysis — each disconnected blob is automatically
#        a separate group (gap in the line = different session group).
#     2. Within each blob, skeletonize and detect bends.
#        Each bend = another session boundary.
#     3. Sum across all blobs.

#     Parameters
#     ----------
#     mask                  : uint8 binary mask (255 = colour present)
#     min_area              : blobs smaller than this (px²) are treated as noise
#     bend_angle_threshold  : see _count_sessions_in_skeleton
#     window                : see _count_sessions_in_skeleton
#     min_gap_between_bends : see _count_sessions_in_skeleton

#     Returns
#     -------
#     (total_sessions, regions_list, all_bend_points)
#       regions_list    : list of dicts with blob bounding boxes + session count
#       all_bend_points : list of (x, y) for every detected bend (debug drawing)
#     """
#     # ── Morphological cleanup ─────────────────────────────────────────────
#     kernel  = np.ones((3, 3), np.uint8)
#     cleaned = cv2.morphologyEx(mask,    cv2.MORPH_CLOSE, kernel, iterations=1)
#     cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN,  kernel, iterations=1)

#     # ── Connected components ───────────────────────────────────────────────
#     num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
#         cleaned, connectivity=8
#     )

#     total_sessions  = 0
#     regions         = []
#     all_bend_points = []

#     for i in range(1, num_labels):   # 0 = background
#         area = stats[i, cv2.CC_STAT_AREA]
#         if area < min_area:
#             safe_print(f"[NOISE] Blob {i} area={area} < {min_area} → skipped")
#             continue

#         x = stats[i, cv2.CC_STAT_LEFT]
#         y = stats[i, cv2.CC_STAT_TOP]
#         w = stats[i, cv2.CC_STAT_WIDTH]
#         h = stats[i, cv2.CC_STAT_HEIGHT]

#         # ── Isolate this blob ──────────────────────────────────────────────
#         blob_mask = ((labels == i).astype(np.uint8) * 255)

#         # ── Skeletonize ────────────────────────────────────────────────────
#         skeleton = _skeletonize_mask(blob_mask)

#         # ── Bend detection ─────────────────────────────────────────────────
#         safe_print(f"[BLOB {i}] area={area}  bbox=({x},{y},{w},{h})")
#         blob_sessions, bend_pts = _count_sessions_in_skeleton(
#             skeleton,
#             bend_angle_threshold=bend_angle_threshold,
#             window=window,
#             min_gap_between_bends=min_gap_between_bends,
#         )

#         safe_print(f"[BLOB {i}] → {blob_sessions} session(s), "
#                    f"{len(bend_pts)} bend(s)")

#         total_sessions += blob_sessions
#         all_bend_points.extend(bend_pts)

#         regions.append({
#             "x":        x,
#             "y":        y,
#             "w":        w,
#             "h":        h,
#             "area":     int(area),
#             "sessions": blob_sessions,
#             "bends":    bend_pts,
#         })

#     return total_sessions, regions, all_bend_points

def _count_sessions_from_mask(
    mask,
    min_area=0,
    bend_angle_threshold=30,
    window=12,
    min_gap_between_bends=15
):
    """
    Count charging segments instead of skeleton bends.

    Logic:
    - Find connected colour blobs.
    - Ignore small blobs.
    - Each valid blob contributes ONE charging segment.
    - This matches the visible graph better than bend detection.
    """

    kernel = np.ones((3, 3), np.uint8)

    cleaned = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=1
    )

    cleaned = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_OPEN,
        kernel,
        iterations=1
    )

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        cleaned,
        connectivity=8
    )

    total_sessions = 0
    regions = []
    all_bend_points = []

    for i in range(1, num_labels):

        area = stats[i, cv2.CC_STAT_AREA]

        if area < min_area:
            safe_print(
                f"[NOISE] Blob {i} area={area} < {min_area} -> skipped"
            )
            continue

        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]

        # ONE visible blob = ONE graph segment
        blob_sessions = 1

        safe_print(
            f"[BLOB {i}] area={area} bbox=({x},{y},{w},{h}) "
            f"-> 1 visible segment"
        )

        total_sessions += blob_sessions

        regions.append({
            "x": int(x),
            "y": int(y),
            "w": int(w),
            "h": int(h),
            "area": int(area),
            "sessions": blob_sessions,
            "bends": []
        })

    return total_sessions, regions, all_bend_points


# ---------------------------------------------------------------------------
#  MAIN GRAPH ANALYSIS
# ---------------------------------------------------------------------------

def detect_sessions_from_graph(image_path):
    """
    Main graph analysis function.

    Steps
    -----
    1.  Load screenshot.
    2.  Locate graph bounds (Appium + fallback, hard-capped at 62% height).
    3.  Crop to graph area only.
    3b. Black-out bottom legend strip.
    4.  Black-out left Y-axis label strip.
    5.  Detect and SUBTRACT the white/grey usage line.
    6.  Detect and SUBTRACT the yellow V2L/V2V line.
    7.  HSV colour masks for RED (fast) and GREEN (slow).
    8.  Skeletonize + bend detection for session counting.
    9.  Save annotated debug image with bend points marked.

    Returns (result_dict, error_string | None)

    result_dict keys
    ----------------
    fast_sessions      : int
    slow_sessions      : int
    red_pixels         : int
    green_pixels       : int
    red_regions        : list of region dicts
    green_regions      : list of region dicts
    graph_top_px       : int
    graph_bottom_px    : int
    graph_left_px      : int
    graph_right_px     : int
    debug_image_path   : str | None
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return None, "Screenshot image not loaded"

    img_h, img_w = img.shape[:2]

    # ── 1. Get graph bounds ────────────────────────────────────────────────
    g_top, g_bottom, g_left, g_right = _get_graph_bounds(img_h, img_w)

    # ── 2. Crop to graph area ──────────────────────────────────────────────
    graph_crop = img[g_top:g_bottom, g_left:g_right].copy()
    crop_h, crop_w = graph_crop.shape[:2]

    if crop_h < 10 or crop_w < 10:
        return None, f"Graph crop too small: {crop_w}x{crop_h}"

    # ── 3. Black-out left Y-axis label strip (~8% of crop width) ──────────
    axis_strip = int(crop_w * 0.08)
    graph_crop[:, :axis_strip] = 0

    # ── 3b. Black-out bottom legend strip (~10% of crop height) ───────────
    legend_strip = int(crop_h * 0.10)
    graph_crop[crop_h - legend_strip:, :] = 0

    # ── 4. Convert to HSV ─────────────────────────────────────────────────
    hsv = cv2.cvtColor(graph_crop, cv2.COLOR_BGR2HSV)

    # ── 5. WHITE/GREY usage line mask ─────────────────────────────────────
    #    Sat < 35, Val > 180 → pure white or light grey
    #    Dilate 1 iter only — larger dilation eats adjacent green pixels
    white_mask = cv2.inRange(
        hsv,
        np.array([0,   0,   180]),
        np.array([180, 35,  255])
    )
    wk = np.ones((3, 3), np.uint8)
    white_mask_fat = cv2.dilate(white_mask, wk, iterations=1)

    # ── 6. YELLOW V2L/V2V line mask ───────────────────────────────────────
    #    Hue 20-35 (yellow/amber), high saturation
    yellow_mask = cv2.inRange(
        hsv,
        np.array([20, 100, 100]),
        np.array([35, 255, 255])
    )
    yellow_mask_fat = cv2.dilate(yellow_mask, wk, iterations=1)

    # Combined ignore mask
    ignore_mask = cv2.bitwise_or(white_mask_fat, yellow_mask_fat)

    # ── 7a. RED mask — fast charging ──────────────────────────────────────
    red_lo = cv2.inRange(hsv, np.array([0,   120, 80]), np.array([10,  255, 255]))
    red_hi = cv2.inRange(hsv, np.array([160, 120, 80]), np.array([180, 255, 255]))
    red_mask = cv2.bitwise_or(red_lo, red_hi)
    red_mask = cv2.bitwise_and(red_mask, cv2.bitwise_not(ignore_mask))

    # ── 7b. GREEN mask — slow charging ────────────────────────────────────
    green_mask = cv2.inRange(
        hsv,
        np.array([40, 80, 60]),
        np.array([85, 255, 255])
    )
    green_mask = cv2.bitwise_and(green_mask, cv2.bitwise_not(ignore_mask))

    red_pixels   = cv2.countNonZero(red_mask)
    green_pixels = cv2.countNonZero(green_mask)

    safe_print(f"[PIXELS] RedPx={red_pixels}  GreenPx={green_pixels}")

    # ── 8. Count sessions — skeleton + bend detection ─────────────────────
    #
    #  bend_angle_threshold = 30°
    #    Works for the gentle S-curve in the example graph.
    #    Raise to 40° if you get overcounting on smooth curves.
    #    Lower to 20° if a sharp bend is being missed.
    #
    #  window = 12 px
    #    Direction is estimated over a 12-pixel lookahead on the skeleton.
    #    Larger = smoother, less noise-sensitive.
    #
    #  min_gap_between_bends = 15 px
    #    Prevents the same bend being counted twice due to direction
    #    oscillation at the peak of a curve.
    #
    #  min_area = 300 px²
    #    Noise floor — anything smaller is a JPEG artefact or legend dot.

    fast_sessions, red_regions, red_bends = _count_sessions_from_mask(
        red_mask,
        min_area=0,
        bend_angle_threshold=30,
        window=12,
        min_gap_between_bends=15,
    )
    slow_sessions, green_regions, green_bends = _count_sessions_from_mask(
        green_mask,
        min_area=0,
        bend_angle_threshold=30,
        window=12,
        min_gap_between_bends=15,
    )

    safe_print(f"[GRAPH DETECT] FastSessions={fast_sessions}  "
               f"SlowSessions={slow_sessions}  "
               f"RedPx={red_pixels}  GreenPx={green_pixels}")

    # ── 9. Save annotated debug image ─────────────────────────────────────
    debug_path = None
    try:
        debug = graph_crop.copy()

        # Draw bounding box + label for each RED blob
        session_idx = 1
        for r in red_regions:
            for _ in range(r["sessions"]):
                cv2.rectangle(
                    debug,
                    (r["x"], r["y"]),
                    (r["x"] + r["w"], r["y"] + r["h"]),
                    (0, 0, 255), 2
                )
                cv2.putText(
                    debug, f"F{session_idx}",
                    (r["x"], max(0, r["y"] - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1
                )
                session_idx += 1

        # Draw bounding box + label for each GREEN blob
        session_idx = 1
        for r in green_regions:
            cv2.rectangle(
                debug,
                (r["x"], r["y"]),
                (r["x"] + r["w"], r["y"] + r["h"]),
                (0, 255, 0), 2
            )
            cv2.putText(
                debug, f"S{session_idx}~S{session_idx + r['sessions'] - 1}"
                       if r["sessions"] > 1 else f"S{session_idx}",
                (r["x"], max(0, r["y"] - 4)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1
            )
            session_idx += r["sessions"]

        # Draw CYAN circles at every GREEN bend point
        for bx, by in green_bends:
            cv2.circle(debug, (bx, by), 7, (0, 255, 255), 2)
            cv2.putText(debug, "B", (bx + 5, by - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)

        # Draw ORANGE circles at every RED bend point
        for bx, by in red_bends:
            cv2.circle(debug, (bx, by), 7, (0, 165, 255), 2)
            cv2.putText(debug, "B", (bx + 5, by - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 165, 255), 1)

        # Session count summary overlay
        cv2.putText(
            debug,
            f"Fast={fast_sessions}  Slow={slow_sessions}",
            (axis_strip + 4, 18),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
        )

        ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_path = os.path.join(Screenshot_path, f"graph_debug_{ts}.png")
        os.makedirs(Screenshot_path, exist_ok=True)
        cv2.imwrite(debug_path, debug)
        safe_print(f"[DEBUG] Annotated graph saved: {debug_path}")

    except Exception as e:
        safe_print(f"[DEBUG] Could not save debug image: {e}")

    result = {
        "fast_sessions":    fast_sessions,
        "slow_sessions":    slow_sessions,
        "red_pixels":       red_pixels,
        "green_pixels":     green_pixels,
        "red_regions":      red_regions,
        "green_regions":    green_regions,
        "graph_top_px":     g_top,
        "graph_bottom_px":  g_bottom,
        "graph_left_px":    g_left,
        "graph_right_px":   g_right,
        "debug_image_path": debug_path,
    }
    return result, None


# ---------------------------------------------------------------------------
#  OPTIONAL: UI text cross-check (secondary validation only)
# ---------------------------------------------------------------------------

def extract_fast_slow_count_from_ui():
    """
    Read fast/slow session counts from the 'Fast vs slow charging' card text.
    Used only when ENABLE_TEXT_CROSSCHECK = True.
    Returns (fast_count, slow_count, text_list).
    """
    text_list  = []
    fast_count = None
    slow_count = None

    driver.implicitly_wait(5)
    try:
        label_map = {
            "fast": ("fast charging sessions", "fast charging"),
            "slow": ("slow charging sessions", "slow charging"),
        }
        for kind, keywords in label_map.items():
            for kw in keywords:
                xpath = (
                    f"//*[contains("
                    f"translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    f"'abcdefghijklmnopqrstuvwxyz'),'{kw}')]"
                    f"/following-sibling::*[1]"
                )
                els = driver.find_elements(AppiumBy.XPATH, xpath)
                if els:
                    raw = els[0].text.strip()
                    text_list.append(f"{kind}={raw}")
                    try:
                        val = int(raw)
                        if kind == "fast":
                            fast_count = val
                        else:
                            slow_count = val
                        break
                    except ValueError:
                        continue

        # Fallback: index-offset search
        if fast_count is None or slow_count is None:
            all_els   = driver.find_elements(AppiumBy.XPATH, "//*[@text]")
            all_texts = [el.text.strip() for el in all_els if el.text.strip()]
            text_list.extend(all_texts)
            for i, t in enumerate(all_texts):
                tl = t.lower()
                if "fast charging sessions" in tl or "fast charging" in tl:
                    for j in range(i + 1, min(i + 4, len(all_texts))):
                        try:
                            fast_count = int(all_texts[j]); break
                        except ValueError:
                            continue
                if "slow charging sessions" in tl or "slow charging" in tl:
                    for j in range(i + 1, min(i + 4, len(all_texts))):
                        try:
                            slow_count = int(all_texts[j]); break
                        except ValueError:
                            continue
    except Exception as e:
        text_list.append(str(e))
    finally:
        driver.implicitly_wait(0.5)

    return fast_count, slow_count, text_list


# ---------------------------------------------------------------------------
#  MAIN VALIDATION FUNCTION
# ---------------------------------------------------------------------------

def Validate_Charging_History(input_str="", _retry=0):
    """
    LabVIEW-compatible validation function.

    Input
    -----
    "fast_threshold,slow_threshold"
      Minimum pixel count to consider a session colour present on the graph.
      Example : "50,50"
      Default : fast_threshold=50, slow_threshold=50

    Output (always a single string)
    ------
    Ok#PASS:GraphFast=<n>,GraphSlow=<n>[,UIFast=<n>,UISlow=<n>],
            RedPixels=<n>,GreenPixels=<n>,
            RedRegions=<n>,GreenRegions=<n>+<screenshot_path>

    Not ok#FAIL:GraphFast=<n>,GraphSlow=<n>,UIFast=<n>,UISlow=<n>,
                Mismatch=<field>+<screenshot_path>

    Not ok#<reason>   on error / abort
    """
    try:
        # ── Abort guard ────────────────────────────────────────────────────
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not ok#Aborted by abort signal"
        
        input_str=""

        # ── Parse thresholds ───────────────────────────────────────────────
        fast_threshold = 100
        slow_threshold = 100

        # if input_str and "," in input_str:
        #     p1, p2 = input_str.split(",", 1)
        #     try:
        #         fast_threshold = int(p1.strip())
        #         slow_threshold = int(p2.strip())
        #     except ValueError:
        #         return "Not ok#Invalid threshold format. Expected 'int,int'"

        # ── Capture screenshot ─────────────────────────────────────────────
        status = capture_screenshot(temp_path)
        if "error" in str(status).lower() or "not ok" in str(status).lower():
            return f"Not ok#Screenshot capture failed:{status}"

        # ── PRIMARY: detect sessions from graph line ───────────────────────
        graph_result, error = detect_sessions_from_graph(temp_path)
        if error:
            return f"Not ok#{error}"

        graph_fast = graph_result["fast_sessions"]
        graph_slow = graph_result["slow_sessions"]

        # ── SECONDARY (optional): read UI text counts ──────────────────────
        ui_fast       = None
        ui_slow       = None
        mismatch_info = ""

        if ENABLE_TEXT_CROSSCHECK:
            ui_fast, ui_slow, text_list = extract_fast_slow_count_from_ui()
            safe_print(f"[UI TEXT] UIFast={ui_fast}, UISlow={ui_slow}")

            if ui_fast is not None and ui_fast != graph_fast:
                mismatch_info += f"FastMismatch(Graph={graph_fast},UI={ui_fast}),"
            if ui_slow is not None and ui_slow != graph_slow:
                mismatch_info += f"SlowMismatch(Graph={graph_slow},UI={ui_slow}),"

        # ── Save proof screenshot ──────────────────────────────────────────
        os.makedirs(Screenshot_path, exist_ok=True)
        ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_name = f"charging_graph_validation_{ts}.png"
        full_path = os.path.join(Screenshot_path, save_name)

        raw = cv2.imread(str(temp_path))
        if raw is not None:
            cv2.imwrite(full_path, raw)
        else:
            full_path = str(temp_path)

        # ── Build common payload ───────────────────────────────────────────
        ui_part = (
            f",UIFast={ui_fast},UISlow={ui_slow}"
            if ENABLE_TEXT_CROSSCHECK and ui_fast is not None
            else ""
        )

        common = (
            f"GraphFast={graph_fast},"
            f"GraphSlow={graph_slow}"
            f"{ui_part},"
            f"RedPixels={graph_result['red_pixels']},"
            f"GreenPixels={graph_result['green_pixels']},"
            f"RedRegions={graph_result['red_regions']},"
            f"GreenRegions={graph_result['green_regions']},"
            f"GraphTop={graph_result['graph_top_px']},"
            f"GraphBottom={graph_result['graph_bottom_px']}"
        )

        # ── Determine PASS / FAIL ──────────────────────────────────────────
        # red_pixels_ok = (
        #     (graph_fast == 0 and graph_result["red_pixels"]   <= fast_threshold) or
        #     (graph_fast >  0 and graph_result["red_pixels"]   >  fast_threshold)
        # )
        # green_pixels_ok = (
        #     (graph_slow == 0 and graph_result["green_pixels"] <= slow_threshold) or
        #     (graph_slow >  0 and graph_result["green_pixels"] >  slow_threshold)
        # )

        # passed = red_pixels_ok and green_pixels_ok and (mismatch_info == "")

        # if passed:
        #     return f"Ok#PASS:{common}+{full_path}"
        # else:
        #     fail_reason = mismatch_info if mismatch_info else \
        #         "PixelCountMismatch(sessions>0 but pixels below threshold)"
        #     return f"Not ok#FAIL:{fail_reason},{common}+{full_path}"
    # ── Determine PASS / FAIL ──────────────────────────────────────────
        red_pixels_ok = (
            (graph_fast == 0 and graph_result["red_pixels"] <= fast_threshold) or
            (graph_fast > 0 and graph_result["red_pixels"] > fast_threshold)
        )

        green_pixels_ok = (
            (graph_slow == 0 and graph_result["green_pixels"] <= slow_threshold) or
            (graph_slow > 0 and graph_result["green_pixels"] > slow_threshold)
        )

        mismatch_messages = []

        if ENABLE_TEXT_CROSSCHECK:
            if ui_fast is not None and ui_fast != graph_fast:
                mismatch_messages.append(
                    f"Fast Charging Sessions: Graph={graph_fast}, App={ui_fast}"
                )

            if ui_slow is not None and ui_slow != graph_slow:
                mismatch_messages.append(
                    f"Slow Charging Sessions: Graph={graph_slow}, App={ui_slow}"
                )

        passed = (
            red_pixels_ok and
            green_pixels_ok and
            len(mismatch_messages) == 0
        )

        if passed:
            return (
                f"Ok#"
                f"Fast Charging Sessions = {graph_fast}, "
                f"Slow Charging Sessions = {graph_slow}. "
                f"Graph data matches application data."
                f"+{full_path}"
            )

        else:

            if mismatch_messages:

                return (
                    f"Not ok#"
                    f"Charging session count mismatch detected. "
                    f"{' | '.join(mismatch_messages)}"
                    f"+{full_path}"
                )

            else:

                return (
                    f"Not ok#"
                    f"Graph validation failed due to insufficient graph pixels detected."
                    f" Graph Count -> Fast={graph_fast}, Slow={graph_slow}"
                    f"+{full_path}"
                )

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        if is_uia2_socket_error(e):
            if _retry < 2:
                safe_print(f"[UIA2 RECOVERY] Retry {_retry + 1}")
                recover_uia2_session()
                sleep(1)
                return Validate_Fast_Slow_Charging_Graph(
                    input_str, _retry=_retry + 1
                )
            return "Not ok#UIA2 session recovery failed after retries"

        return f"Not ok#{str(e)}"





# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------


################################ Heath Pattern ###############################

# def validate_charging_health(input_string):
#     """
#     Input Format:
#     cycle_index#expected_cycle#check_recommendation

#     Example:
#     1#F#Yes
#     """

#     try:
#         # --------------------------
#         # Parse Input
#         # --------------------------
#         cycle_index, expected_cycle, check_reco = input_string.split("#")
#         cycle_index = int(cycle_index) - 1

#         # --------------------------
#         # Health Pattern Extraction
#         # --------------------------
#         health_pattern = []

#         health_elements = driver.find_elements(
#             AppiumBy.XPATH,
#             "//*[contains(@text,'/4 cycles')]"
#         )

#         for ele in health_elements:
#             health_pattern.append(ele.text.strip())

#         # Example:
#         # ['3/4 cycles','2/4 cycles','1/4 cycles','0/4 cycles']

#         # --------------------------
#         # Charging Cycle Extraction
#         # --------------------------
#         cycle_elements = driver.find_elements(
#             AppiumBy.XPATH,
#             "//*[@text='F' or @text='S']"
#         )

#         charging_cycle = [x.text.strip() for x in cycle_elements]

#         # Example:
#         # ['F','F','F','F']

#         # --------------------------
#         # Recommendation Extraction
#         # --------------------------
#         try:
#             reco_element = driver.find_element(
#                 AppiumBy.XPATH,
#                 "//*[contains(@text,'recommendation')]"
#             )

#             recommendation = reco_element.text.replace(
#                 "recommendation:",
#                 ""
#             ).strip()

#             if recommendation == "" or recommendation == "--":
#                 recommendation = "NA"

#         except:
#             recommendation = "NA"

#         # --------------------------
#         # Validation
#         # --------------------------
#         cycle_pass = False
#         reco_pass = False

#         if charging_cycle[cycle_index] == expected_cycle:
#             cycle_pass = True

#         if check_reco.upper() == "YES":
#             reco_pass = recommendation != "NA"
#         else:
#             reco_pass = True

#         result = "PASS" if cycle_pass and reco_pass else "FAIL"

#         return {
#             "result": result,
#             "health_pattern": health_pattern,
#             "charging_cycle": charging_cycle,
#             "recommendation": recommendation
#         }

#     except Exception as e:
#         return {
#             "result": "FAIL",
#             "error": str(e)
#         }

def Validate_Charging_Health(input_string):
    """
    Input Format:
    cycle_index#expected_cycle#check_recommendation

    Example:
    1#F#Yes
    """

    try:
        cycle_index, expected_cycle, check_reco = input_string.split("#")
        cycle_index = int(cycle_index) - 1

        # --------------------------
        # Health Pattern Extraction
        # --------------------------
        health_pattern = []

        health_elements = driver.find_elements(
            AppiumBy.XPATH,
            "//*[contains(@text,'/4 cycles')]"
        )

        for ele in health_elements:
            health_pattern.append(ele.text.strip())

        # --------------------------
        # Charging Cycle Extraction
        # --------------------------
        cycle_elements = driver.find_elements(
            AppiumBy.XPATH,
            "//*[@text='F' or @text='S']"
        )

        charging_cycle = [x.text.strip() for x in cycle_elements]

        # --------------------------
        # Recommendation Extraction
        # --------------------------
        try:
            reco_element = driver.find_element(
                AppiumBy.XPATH,
                "//*[contains(@text,'recommendation')]"
            )

            recommendation = (
                reco_element.text
                .replace("recommendation:", "")
                .strip()
            )

            if recommendation in ["", "--"]:
                recommendation = "NA"

        except Exception:
            recommendation = "NA"

        capture_screenshot(Ref_Img_Path)
        curr_img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"Ref_Screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)

        # --------------------------
        # Validation
        # --------------------------
        # if cycle_index >= len(charging_cycle):
        #     return (
        #         f"Not ok#Invalid cycle index {cycle_index + 1}. "
        #         f"Available cycles={len(charging_cycle)}+{full_path}"
        #     )

        # if charging_cycle[cycle_index] != expected_cycle:
        #     return (
        #         f"Not ok#Charging cycle mismatch. "
        #         f"Expected={expected_cycle}, "
        #         f"Actual={charging_cycle[cycle_index]}+{full_path}"
        #     )

        # if check_reco.upper() == "YES" and recommendation == "NA":
        #     return (
        #         f"Not ok#Recommendation expected but not found+{full_path}"
        #     )

        # return (
        #     f"Ok#Charging health validation passed. "
        #     f"Cycle={charging_cycle[cycle_index]}, "
        #     f"Recommendation={recommendation}+{full_path}"
        # )

        # # --------------------------
        # # Validation
        # # --------------------------

        # if cycle_index == -1:  # User entered 0
        #     actual_pattern = "".join(charging_cycle)

        #     if actual_pattern != expected_cycle:

        #         return (
        #             f"Not ok#Charging cycle pattern mismatch. "
        #             f"Expected={expected_cycle}, "
        #             f"Actual={actual_pattern}"
        #             f"+{full_path}"
        #         )

        # else:
        #     if cycle_index >= len(charging_cycle):
               

        #         return (
        #             f"Not ok#Invalid cycle index {cycle_index + 1}. "
        #             f"Available cycles={len(charging_cycle)}"
        #             f"+{full_path}"
        #         )

        #     if charging_cycle[cycle_index] != expected_cycle:
            

        #         return (
        #             f"Not ok#Charging cycle mismatch. "
        #             f"Expected={expected_cycle}, "
        #             f"Actual={charging_cycle[cycle_index]}"
        #             f"+{full_path}"
        #         )

        # # Recommendation validation
        # if check_reco.upper() == "YES" and recommendation == "NA":
           

        #     return (
        #         f"Not ok#Recommendation expected but not found."
        #         f"+{full_path}"
        #     )

        # screenshot = capture_screenshot("ChargingHealthPass")

        # return (
        #     f"Ok#Charging health validation passed."
        #     f"+{full_path}"
        # )


        # --------------------------
        # Validation
        # --------------------------

        input_index = int(cycle_index)

        # FULL PATTERN MODE
        if input_index == -1 or len(expected_cycle) > 1:

            actual_pattern = "".join(charging_cycle)

            if actual_pattern != expected_cycle:

                return (
                    f"Not ok#Charging cycle pattern mismatch. "
                    f"Expected={expected_cycle}, Actual={actual_pattern}"
                    f"+{full_path}"
                )

        # INDEX MODE
        else:
            idx = input_index - 1

            if idx >= len(charging_cycle):

                return (
                    f"Not ok#Invalid cycle index {input_index}. "
                    f"Available cycles={len(charging_cycle)}"
                    f"+{full_path}"
                )

            if charging_cycle[idx] != expected_cycle:

                return (
                    f"Not ok#Charging cycle mismatch. "
                    f"Expected={expected_cycle}, Actual={charging_cycle[idx]}"
                    f"+{full_path}"
                )

        # --------------------------
        # Recommendation validation
        # --------------------------
        if check_reco.upper() == "YES" and recommendation == "NA":

            return (
                f"Not ok#Recommendation expected but not found."
                f"+{full_path}"
            )

        # --------------------------
        # PASS CASE
        # --------------------------
        return (
            f"Ok#Charging health validation passed."
            f"+{full_path}"
        )

    except Exception as e:
        return f"Not ok#{str(e)}"

# init_driver()
# result = Validate_Fast_Slow_Charging_Graph("100,100")
# print(result)

# print(validate_charging_health("1#FSFF#No"))


# I Check Health Pattern for the 'nth' charging cycle with the expected cycle 'Cycle (F/S)' and validate the recommendation status 'Yes/No'.