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
import time
from time import sleep
import traceback
import os


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# from datetime import datetime
temp_path = "C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\temp_img.png"
#temp_path = "D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\temp_img.png"
Ref_Img_Path = "C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\ref_img.png"

Common_Ref_Img_Path = None


# Get the current script's directory
BASE_DIR = Path(__file__).resolve().parent

# Go up to project root if needed
PROJECT_ROOT = BASE_DIR.parent.parent  # adjust based on where your script is


# Construct the full path dynamically
temp_log = PROJECT_ROOT /  "Appium" / "ADB Logs"
Cap_path =  PROJECT_ROOT /  "Appium" / "Capabilities" / "Capabilities.json"
ss_path= PROJECT_ROOT /  "Appium" / "Screenshots"
log_process = None
temp_logfile = "temp_logcat.log"  # Temporary log file before renaming
driver = None  # global variable to hold the Appium driver
device_id = None
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




def start_server(input="str"):
    # Launch Appium in a new CMD window without blocking LabVIEW
    subprocess.Popen(["cmd.exe", "/c", "start cmd /k appium"], shell=True)
    return "Appium server started"

####################################################### Initialization function #############################################################


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

def is_driver_alive(driver):
    try:
        # This will throw an exception if the session is invalid
        if driver is None:
            return False

        # Try a harmless command to check if driver is alive
        driver.current_activity  # or: driver.title, driver.session_id etc.
        return True

    except Exception:
        return False


def mark_driver_busy():
    global driver_busy
    driver_busy = True

def mark_driver_idle():
    global driver_busy
    driver_busy = False
    
driver_lock = threading.Lock()
def keep_driver_alive():
    global driver
    while driver_lock:
        try:
            if driver:
                driver.current_activity  # dummy ping
        except:
            pass
        sleep(60)  # ping every 30 seconds

# Call this once after initializing the driver
def start_keep_alive():
    t = threading.Thread(target=keep_driver_alive, daemon=True)
    t.start()

# from functools import wraps
# # Global keep-alive thread will check this
# driver_busy = False

# def set_driver_busy(flag: bool):
#     global driver_busy
#     driver_busy = flag

# # Wrapper class around the driver
# class KeepAliveDriver:
#     def __init__(self, driver):
#         self._driver = driver

#     def __getattr__(self, name):
#         orig_attr = getattr(self._driver, name)
#         if callable(orig_attr):
#             @wraps(orig_attr)
#             def wrapper(*args, **kwargs):
#                 set_driver_busy(True)
#                 try:
#                     return orig_attr(*args, **kwargs)
#                 finally:
#                     set_driver_busy(False)
#             return wrapper
#         else:
#             return orig_attr

# def keep_driver_alive(driver):
#     while True:
#         try:
#             if driver and not driver_busy:
#                 driver.current_activity  # ping only when idle
#         except Exception as e:
#             print(f"Keep-alive ping failed: {e}")
#         sleep(60)

# def start_keep_alive(driver):
#     t = threading.Thread(target=keep_driver_alive, args=(driver,), daemon=True)
#     t.start()

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
    
# def is_app_in_foreground(package_name):
#     try:
#         result = subprocess.run(
#             ["adb", "shell", "dumpsys", "activity", "activities"],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )
#         output = result.stdout

#         # Look for the top (foreground) activity
#         if f"ResumedActivity: ActivityRecord" in output and package_name in output:
#             print(f"{package_name} is in the foreground.")
#             return True
#         else:
#             print(f"{package_name} is NOT in the foreground.")
#             return False
#     except Exception as e:
#         print(f"Error checking foreground app: {e}")
#         return False

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
        # Validate input
        if not isinstance(pin_code, str):
            return f"Error: Expected pin_code as string, got {type(pin_code).__name__}"

        # Wake up the phone
        subprocess.run(["adb", "shell", "input", "keyevent", "224"], check=True)
        sleep(1)

        # Swipe up to unlock
        subprocess.run(["adb", "shell", "input", "swipe", "300", "1000", "300", "500"], check=True)
        sleep(1)

        if is_device_unlocked():
            print('unlocked')
        else:
            subprocess.run(["adb", "shell", "input", "text", pin_code], check=True)
            sleep(0.5)

        # Press Enter
        subprocess.run(["adb", "shell", "input", "keyevent", "66"], check=True)
        sleep(2)

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

def failcaseinit(input):
    global driver, device_id, app_package

    input = str(input)

    with driver_lock:
        # Read capabilities
        with open(Capability_path, "r") as file:
            caps = json.load(file)

        print("[INIT] Restarting driver...")

        # Create new Appium session
        new_driver = webdriver.Remote("http://localhost:4723", caps)

        # Update globals
        driver = new_driver
        device_id = caps["udid"]
        app_package = caps["appPackage"]

        # Start keep-alive again
        start_keep_alive(driver)

        print("[INIT] Driver reinitialized OK")

    return "PASS"

 
def appium_error_monitor(interval=0.5):
    global driver, stop_thread_flag

    while not stop_thread_flag:
        time.sleep(interval)

        try:
            with driver_lock:
                if driver is None:
                    print("[MONITOR] No driver reinitializing...")
                    failcaseinit("demo")
                    continue

                _ = driver.session_id  # Validate session

        except Exception:
            print("[MONITOR] Driver error detected reinitializing...")
            failcaseinit("demo")

            

def file_watcher(filepath, check_interval=0.5):
    """Background watcher that monitors for a stop file."""
    while not stop_event.is_set():
        if os.path.exists(filepath):
            print(f"[STOP TRIGGER] File detected: {filepath}")
            stop_event.set()
            try:
                if driver:
                    driver.quit()
                    driver = None
                    failcaseinit("demo")
                    print("[STOP ACTION] Appium driver terminated.")
            except Exception as e:
                print(f"[ERROR stopping driver]: {e}")
            break
        time.sleep(check_interval)


                                                                    ############## Init Main #############
def init_driver(variable_str="", timeout=10):
    global driver, device_id, stop_event,stop_thread_flag
    try:
        stop_event = threading.Event()
        stop_event.clear()
        watcher_thread = threading.Thread(target=file_watcher, args=(file_to_watch,), daemon=True)
        watcher_thread.start()
        
        stop_thread_flag = False  # global flag to stop the thread

        monitor_thread = threading.Thread(target=appium_error_monitor, args=(5,), daemon=True)
        monitor_thread.start()
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
        driver = webdriver.Remote("http://localhost:4723", caps)
        # sleep(1)
      # wrap it
        start_keep_alive(driver)
        
        safe_print("[INIT] Appium driver initialized")
        app_package = caps["appPackage"]
        device_id = caps["udid"]
        print(device_id)
        # Launch WhatsApp using ADB monkey command

        ensure_app_in_foreground(app_package)

        return "PASS: Driver initialized"

    except Exception as e:
        err = f"ERROR: Failed to initialize Appium driver: {str(e)}"
        safe_print(err)
        safe_print(traceback.format_exc())
        return err

init_driver()

def Restart_App_Package_Name_Text(input):
    """
    Force stop and relaunch the given app.
    
    Args:
        package_name (str): App package name (e.g., "com.whatsapp")
        device_id (str, optional): Android device ID for multi-device handling

    Returns:
        str: PASS/FAIL message
    """
    try:
        # ?package_name = Get_Package_Name("input")

        p1,p2=input.split(",",1)
        p1 = p1.lower().strip()
        if p1=="tata motors pv app":
            package_name="com.tatamotors.oneapp"
        else:
            package_name="com.tatamotors.evoneapp"
        
        # Load existing JSON
        with open(Capability_path, 'r') as file:
            data = json.load(file)

        # Modify the package name
        
        #App_Activity = package_name + "com.tatamotors.oneapp.ui.onboarding.OnBoardingActiv

        # Run the ADB command
        result = subprocess.run(
            [
                "adb", "-s", device_id,
                "shell", "cmd", "package", "resolve-activity", "--brief", package_name
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Parse the output
        output = result.stdout.strip().splitlines()

        if len(output) >= 2:
            app_package = output[0]
            app_activity = output[1]
            print("appPackage:", app_package)
            print("appActivity:", app_activity)
        else:
            print("Failed to resolve activity. Output:")
            print(result.stdout)
            print("Error (if any):", result.stderr)
        
        app_activity=app_activity.replace("/","")
        print(app_activity)
                
        data['appPackage'] = package_name
        data['appActivity'] = app_activity
        
        # Save it back
        with open(Capability_path, 'w') as file:
            json.dump(data, file, indent=4)
            
        # Step 1: Kill the app
        cmd = ["adb"]
        if device_id:
            print("hello")
            cmd += ["-s", device_id]
        cmd += ["shell", "am", "force-stop", package_name]
        print(cmd)
        subprocess.run(cmd, check=True)
        sleep(1)

        # Step 2: Relaunch the app
        cmd = ["adb"]
        if device_id:
            cmd += ["-s", device_id]
        cmd += [
            "shell", "monkey", "-p", package_name,
            "-c", "android.intent.category.LAUNCHER", "1"
        ]
        subprocess.run(cmd, check=True)
        #sleep(5)

        # Step 3: Verify it's foreground
        if is_app_in_foreground(package_name):
            return f"Ok#{package_name} restarted and is in foreground"
        else:
            return f"Not ok#{package_name} relaunched but not in foreground"

    except subprocess.CalledProcessError as e:
        return f"ERROR: Failed to restart {package_name}: {e}"
    except Exception as e:
        return f"ERROR: Unexpected issue restarting app: {str(e)}"
    
# print(init_driver())
# print(Restart_App_Package_Name_Text("tata motors pv app,10"))
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
        return f"error:capture_failed:{str(e)}"


################################################### Check notification ##########################################################

def Check_Notification(text):
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

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: {str(e)}\n"

# init_driver()
# Check_Notification("hi,1")

def Open_Notification_Panel(text):
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

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: {str(e)}\n"

# init_driver()
# Open_Notification_Panel("hi,1")

def Close_Notification_Panel(text):
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

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: {str(e)}\n"

# init_driver()
# Close_Notification_Panel("hi,1")
###################################################### Mobile Resolution ##########################################################

def get_resolution(device_id):
    try:
        param1, param2 = device_id.split(",", 1)
        # Run adb command for the specific device
        result = subprocess.check_output(['adb', '-s', param1, 'shell', 'wm', 'size'], encoding='utf-8')
        
        # Extract width and height using regex
        match = re.search(r'Physical size:\s*(\d+)x(\d+)', result)
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        if match:
            width, height = match.groups()
            return f"{width}x{height}"  # Example: "1080x2400"
        else:
            return "ERROR: Resolution not found"
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

# def Wait_Until_Text_Appears(visible_text, check_interval=2):
#     """
#     Wait until the specified text appears on the screen.

#     Args:
#         visible_text (str): "text_to_find,timeout"
#         check_interval (int|float): Polling interval in seconds (default 2s)

#     Returns:
#         str: "Ok# Text '<text>' appeared"
#              "Not Ok# Aborted by abort signal"
#              "Not Ok# Text '<text>' not found within timeout"
#              "ERROR: <exception details>"
#     """
#     try:
#         # Parse input
#         param1, param2 = visible_text.split(",", 1)
#         search_str = param1.strip()
#         timeout = float(param2)         # <-- your timeout is used here
#         check_interval = float(check_interval)

#         if not init_driver():
#             return "ERROR: Driver not initialized"

#         wait = WebDriverWait(driver, timeout, poll_frequency=check_interval)

#         def condition(drv):
#             # Abort signal check
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 raise TimeoutException("ABORT")  # immediate stop

#             try:
#                 element = drv.find_element(By.XPATH, f"//*[@text='{search_str}']")
#                 return element if element else False
#             except NoSuchElementException:
#                 return False

#         try:
#             element = wait.until(condition)
#             return f"Ok# Text '{search_str}' appeared"
#         except TimeoutException as e:
#             if "ABORT" in str(e):
#                 return "Not Ok# Aborted by abort signal"
            
             
#             capture_screenshot(temp_path)
#             curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             save_path = f"screenshot_{timestamp}.png"
#             full_path = os.path.join(Screenshot_path, save_path)
#             # Save the image
#             cv2.imwrite(full_path, curr_img)
#             return f"Not Ok# Text '{search_str}' not found+{full_path}"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Wait_Until_Text_Appears failed: {str(e)}"

def Wait_Until_Text_Appears(visible_text, check_interval=2):
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

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Wait_Until_Text_Appears failed: {str(e)}"


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
    

# def Wait_Until_Image_Appears(path_with_timeout, threshold=0.8, check_interval=2):
#     """
#     Wait until the specified image appears on the screen.

#     Args:
#         path_with_timeout (str): "path,timeout"
#         threshold (float): Matching threshold (default 0.8)
#         check_interval (int|float): Polling interval (default 2s)

#     Returns:
#         str: "Ok# Image '<path>' appeared"
#              "Not Ok# Image '<path>' not found within timeout"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <exception details>"
#     """
#     try:
#         # Parse input
#         parts = path_with_timeout.split(",", 1)
#         if len(parts) != 2:
#             return "ERROR: Input format must be 'path,timeout'"

#         path = parts[0].strip()
#         timeout = float(parts[1].strip())
#         threshold = float(threshold)
#         check_interval = float(check_interval)

#         if not init_driver():
#             return "ERROR: Driver not initialized"

#         wait = WebDriverWait(driver, timeout, poll_frequency=check_interval)

#         def condition(_):
#             # Abort signal check
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 raise TimeoutException("ABORT")

#             try:
#                 result = check_image_exists(path, threshold)
#                 if isinstance(result, str) and "Ok" in result:
#                     return True
#             except Exception as inner:
#                 safe_print(f"[LOOP ERROR] {inner}")
#             return False

#         try:
#             wait.until(condition)
#             return f"Ok# Image '{path}' appeared"
#         except TimeoutException as e:
#             if "ABORT" in str(e):
#                 return "Not Ok# Aborted by abort signal"
             
#             capture_screenshot(temp_path)
#             curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             save_path = f"screenshot_{timestamp}.png"
#             full_path = os.path.join(Screenshot_path, save_path)
#             # Save the image
#             cv2.imwrite(full_path, curr_img)
#             return f"Not Ok# Image '{path}' not found+{full_path}"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Wait_Until_Image_Appears failed: {str(e)}"




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

def Wait_Until_Image_Appears(path_with_timeout, threshold=0.86, check_interval=1.0, timeout_message_screenshot=True, debug=False):
    """
    Robust wait until image appears. `path_with_timeout` -> "path,timeout_seconds"
    `threshold` is used as primary template matching score (0..1).
    Returns: same string-format as your original function.
    """
    try:
        mark_driver_busy()
        
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
            mark_driver_idle()

    except Exception as e:
        # Ensure abort file cleaned up
        try:
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
        except Exception:
            pass
        return f"ERROR: Wait_Until_Image_Appears failed: {str(e)}"


# init_driver()
# print(Wait_Until_Image_Appears("D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Disconnectivity.jpg,10"))
######################################################## Click Operation ###############################################


def Click_By_Text(visible_text):
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
    try:
        mark_driver_busy()
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
        mark_driver_idle()

        return f"Not Ok# '{search_text}' not found+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Failed to click on '{visible_text}': {str(e)}"


# def Click_By_Image(path, threshold=0.8):
#     """
#     Click on a UI element by matching an image on the screen.

#     Args:
#         path (str): "image_path,timeout"
#         threshold (float): Matching threshold (default 0.8)

#     Returns:
#         str: "Ok# Clicked on image '<path>' at (x,y)"
#              "Not Ok# Image '<path>' not found within timeout"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <details>"
#     """
#     try:
#         # Extract params
#         parts = path.split(",", 1)
#         if len(parts) != 2:
#             return "ERROR: Input format must be 'image_path,timeout'"

#         img_path = parts[0].strip()
#         timeout = int(parts[1].strip())
#         threshold = float(threshold)

#         # Ensure driver is ready
#         if not init_driver():
#             return "ERROR: Appium driver not initialized"

#         start_time = time.time()send_input
#         while time.time() - start_time < timeout:
#             # ✅ Abort check
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Not Ok# Aborted by abort signal"

#             try:
#                 screenshot = take_screenshot(driver)
#                 template = load_reference_image(img_path)
#                 pos = find_template_in_screenshot(screenshot, template, threshold)

#                 if pos:
#                     driver.execute_script("mobile: clickGesture", {"x": pos[0], "y": pos[1]})
#                     return f"Ok# Clicked on image '{img_path}' at {pos}"

#             except Exception as inner:
#                 safe_print(f"[LOOP ERROR] {inner}")

#             sleep(1)
        
         
#         capture_screenshot(temp_path)
#         curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         save_path = f"screenshot_{timestamp}.png"
#         full_path = os.path.join(Screenshot_path, save_path)
#         # Save the image
#         cv2.imwrite(full_path, curr_img)
        
#         filename = os.path.basename(img_path)

#         # Timeout reached
#         return f"Not Ok# Image '{filename}' not found.+ {full_path}"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Click_By_Image failed for '{path}': {str(e)}"


# def Click_By_Image(path, threshold=0.86, check_interval=1.0, debug=False):
#     """
#     Robustly click on a UI element by matching an image on the screen.

#     Args:
#         path (str): "image_path,timeout"
#         threshold (float): Primary matching threshold (default 0.86)
#         check_interval (float): Polling interval in seconds (default 1.0)
#         debug (bool): If True, logs details of detection pipeline.

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
#             return "ERROR: Input format must be 'image_path,timeout'"

#         img_path = parts[0].strip()
#         timeout = float(parts[1].strip())

#         if not os.path.exists(img_path):
#             return f"ERROR: Reference image not found: {img_path}"

#         if not init_driver():
#             return "ERROR: Appium driver not initialized"

#         start_time = time.time()

#         while True:
#             # Abort check
#             if os.path.exists(file_to_watch):
#                 try:
#                     os.remove(file_to_watch)
#                 except Exception:
#                     pass
#                 return "Not Ok# Aborted by abort signal"

#             # Take screenshot
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

#             # 🔍 Run robust image detection
#             found, details = robust_check_image_exists(img_path, screen_bgr,
#                                                        tm_threshold=threshold,
#                                                        debug=debug)

#             if debug:
#                 safe_print(f"[DEBUG] detection details: {details}")

#             if found:
#                 # Compute click point
#                 click_x, click_y = None, None
#                 # if details.get("method") in ["multi-scale-template", "edge-template", "multiscale-template-secondary"]:
#                 #     (mx, my) = details["match_loc"]
#                 #     scale = details.get("match_scale", 1.0)
#                 #     tpl = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
#                 #     th, tw = tpl.shape[:2]
#                 #     click_x = int(mx + tw * scale / 2)
#                 #     click_y = int(my + th * scale / 2)
#                 if details.get("method") in ["multi-scale-template", "edge-template", "multiscale-template-secondary"]:
#                     match_loc = details.get("match_loc")
#                     if match_loc:
#                         (mx, my) = match_loc
#                         scale = details.get("match_scale", 1.0)
#                         tpl = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
#                         th, tw = tpl.shape[:2]
#                         click_x = int(mx + tw * scale / 2)
#                         click_y = int(my + th * scale / 2)
#                     else:
#                         safe_print("[WARN] match_loc not found despite found=True")
#                         continue

#                 elif details.get("method") == "orb-homography" and details.get("corners") is not None:
#                     poly = details["corners"].reshape(-1,2)
#                     M = cv2.moments(poly)
#                     if M["m00"] != 0:
#                         click_x = int(M["m10"] / M["m00"])
#                         click_y = int(M["m01"] / M["m00"])

#                 if click_x is not None and click_y is not None:
#                     driver.execute_script("mobile: clickGesture", {"x": click_x, "y": click_y})
#                     return f"Ok# Clicked on image '{os.path.basename(img_path)}' at ({click_x},{click_y})"
#                 else:
#                     safe_print("[WARN] Could not compute click coordinates even though match was found")

#             # Timeout check
#             if time.time() - start_time > timeout:
#                 # Save failure screenshot
#                 try:
#                     curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#                     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                     save_path = f"screenshot_{timestamp}.png"
#                     full_path = os.path.join(Screenshot_path, save_path)
#                     cv2.imwrite(full_path, curr_img)
#                 except Exception as e:
#                     safe_print(f"[ERROR] saving timeout screenshot: {e}")
#                     full_path = temp_path if os.path.exists(temp_path) else "screenshot_not_available"
#                 return f"Not Ok# Image '{os.path.basename(img_path)}' not found.+ {full_path}"

#             sleep(check_interval)

#     except Exception as e:
#         try:
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#         except Exception:
#             pass
#         return f"ERROR: Click_By_Image failed for '{path}': {str(e)}"

def Click_By_Image(path, threshold=0.86, check_interval=1.0, debug=False):
    """
    Robustly click on a UI element by matching an image on the screen.

    Handles low-texture icons (e.g., toggles) with fallback multi-scale matching.

    Args:
        path (str): "image_path,timeout"
        threshold (float): Matching threshold (default 0.86)
        check_interval (float): Polling interval in seconds (default 1.0)
        debug (bool): Enable detailed debug logging.

    Returns:
        str: "Ok# Clicked on image '<path>' at (x,y)"
             "Not Ok# Image '<path>' not found within timeout"
             "Not Ok# Aborted by abort signal"
             "ERROR: <details>"
    """
    try:
        mark_driver_busy()
        # Parse inputs
        parts = path.split(",", 1)
        if len(parts) != 2:
            return "ERROR: Input format must be 'image_path,timeout'"

        img_path = parts[0].strip()
        timeout = float(parts[1].strip())

        if not os.path.exists(img_path):
            return f"ERROR: Reference image not found: {img_path}"

        if not init_driver():
            return "ERROR: Appium driver not initialized"

        start_time = time.time()

        while True:
            # Abort check
            if os.path.exists(file_to_watch):
                try:
                    os.remove(file_to_watch)
                except Exception:
                    pass
                return "Not Ok# Aborted by abort signal"

            # Capture screenshot
            capture_result = capture_screenshot(temp_path)
            if not capture_result or not os.path.exists(capture_result):
                safe_print(f"[WARN] Screenshot failed: {capture_result}")
                sleep(check_interval)
                if time.time() - start_time > timeout:
                    break
                continue

            screen_bgr = cv2.imread(temp_path, cv2.IMREAD_COLOR)
            if screen_bgr is None:
                safe_print("[WARN] Failed to read screenshot file")
                sleep(check_interval)
                if time.time() - start_time > timeout:
                    break
                continue

            # 🔍 Primary robust image detection
            found, details = robust_check_image_exists(
                img_path, screen_bgr, tm_threshold=threshold, debug=debug
            )

            if debug:
                safe_print(f"[DEBUG] Detection details: {details}")

            click_x, click_y = None, None

            if found:
                method = details.get("method", "unknown")

                # --- Template or Edge-based Match ---
                if method in ["multi-scale-template", "edge-template", "multiscale-template-secondary"]:
                    match_loc = details.get("match_loc")
                    if match_loc:
                        (mx, my) = match_loc
                        scale = details.get("match_scale", 1.0)
                        tpl = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                        if tpl is not None:
                            th, tw = tpl.shape[:2]
                            click_x = int(mx + tw * scale / 2)
                            click_y = int(my + th * scale / 2)
                    else:
                        safe_print("[WARN] match_loc missing, attempting fallback detection...")
                        found, (click_x, click_y) = multi_scale_fallback(img_path, screen_bgr, threshold, debug)

                # --- ORB / Feature-based Match ---
                elif method == "orb-homography" and details.get("corners") is not None:
                    poly = details["corners"].reshape(-1, 2)
                    M = cv2.moments(poly)
                    if M["m00"] != 0:
                        click_x = int(M["m10"] / M["m00"])
                        click_y = int(M["m01"] / M["m00"])
                else:
                    # --- Unknown method fallback ---
                    safe_print("[INFO] Unknown detection method, triggering multi-scale fallback...")
                    found, (click_x, click_y) = multi_scale_fallback(img_path, screen_bgr, threshold, debug)

                # --- Perform Click if Coordinates Found ---
                if click_x is not None and click_y is not None:
                    driver.execute_script("mobile: clickGesture", {"x": click_x, "y": click_y})
                    return f"Ok# Clicked on image '{os.path.basename(img_path)}' at ({click_x},{click_y})"

                else:
                    safe_print("[WARN] Could not compute click coordinates even though match was found")

            # Timeout check
            if time.time() - start_time > timeout:
                try:
                    curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_path = f"screenshot_{timestamp}.png"
                    full_path = os.path.join(Screenshot_path, save_path)
                    cv2.imwrite(full_path, curr_img)
                except Exception as e:
                    safe_print(f"[ERROR] saving timeout screenshot: {e}")
                    full_path = temp_path if os.path.exists(temp_path) else "screenshot_not_available"
                return f"Not Ok# Image '{os.path.basename(img_path)}' not found.+ {full_path}"
            
            mark_driver_idle()

            sleep(check_interval)

    except Exception as e:
        try:
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
        except Exception:
            pass
        return f"ERROR: Click_By_Image failed for '{path}': {str(e)}"


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




# init_driver()
# print(Click_By_Image("D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Remote_Command.jpg,10"))


###########################################################  Compare Operation ######################################


# def Compare_Screen_By_Text(input_text, base_dir=Screenshot_path):
#     """
#     Take screenshot, extract text via OCR, and check if a given text is present.

#     Args:
#         input_text (str): "text_to_find,timeout"

#     Returns:
#         str: "Ok# Text '<text>' is present on screen, Screenshot: <path>"
#              "Not Ok# Text '<text>' not found within <timeout> sec, Screenshot: <path>"
#              "ERROR: <details>"
#     """
#     try:
#         #import time
#         # Split input into text and timeout
#         param1, param2 = input_text.split(",", 1)
#         search_str = param1.strip()
#         timeout = int(param2.strip())

#         if not os.path.exists(base_dir):
#             os.makedirs(base_dir)

#         start_time = time()
#         screenshot_path = None

#         while time() - start_time < timeout:
#             # Screenshot captured in memory
#             png = driver.get_screenshot_as_png()
#             np_img = np.frombuffer(png, np.uint8)
#             image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

#             # Optional preprocessing
#             gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#             _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

#             # Correct pytesseract call
#             custom_config = r'--oem 3 --psm 6'   # Configuration options go in 'config', NOT 'lang'
#             text = pytesseract.image_to_string(thresh, config=custom_config, lang='eng')  # lang='eng' is correct

#             # Debug log
#             print("[OCR Extracted Text]:", text)

#             # Case-insensitive search
#             if search_str.lower() in text.lower():
#                 # Save only when found
#                 timestamp = time.strftime("%Y%m%d_%H%M%S")
#                 screenshot_path = os.path.join(base_dir, f"screen_found_{timestamp}.png")
#                 with open(screenshot_path, "wb") as f:
#                     f.write(png)
#                 return f"Ok# Text '{search_str}' is present on screen.+{screenshot_path}"

#             sleep(0.5)  # small wait before next check

#         # Timeout reached → save last screenshot for evidence
#         timestamp = time.strftime("%Y%m%d_%H%M%S")
#         screenshot_path = os.path.join(base_dir, f"screen_timeout_{timestamp}.png")
#         driver.save_screenshot(screenshot_path)

#         return f"Not Ok# Text '{search_str}' not found.+{screenshot_path}"

#     except Exception as e:
#         return f"ERROR: {str(e)}"


def Compare_Screen_By_Text(input_text, base_dir=Screenshot_path):
    """
    Take screenshot, extract text via OCR, and check if a given text is present.
    """
    try:
        mark_driver_busy()
        # Split input into text and timeout
        param1, param2 = input_text.split(",", 1)
        search_str = param1.strip()
        timeout = int(param2.strip())

        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        start_time = time.time()   # ✅ correct usage
        screenshot_path = None

        while time.time() - start_time < timeout:
            # Screenshot captured in memory
            png = driver.get_screenshot_as_png()
            np_img = np.frombuffer(png, np.uint8)
            image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

            # Preprocessing for OCR
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # OCR
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(thresh, lang='eng')

            print("[OCR Extracted Text]:", text)

            if search_str.lower() in text.lower():
                # Save only when found
                timestamp = time.strftime("%Y%m%d_%H%M%S")   # ✅ works now
                screenshot_path = os.path.join(base_dir, f"screen_found_{timestamp}.png")
                with open(screenshot_path, "wb") as f:
                    f.write(png)
                return f"Ok# Text '{search_str}' is present on screen.+{screenshot_path}"

            sleep(0.5)

        # Timeout reached → save last screenshot
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(base_dir, f"screen_timeout_{timestamp}.png")
        driver.save_screenshot(screenshot_path)
        
        mark_driver_idle()

        return f"Not Ok# Text '{search_str}' not found.+{screenshot_path}"

    except Exception as e:
        return f"ERROR: {str(e)}"



# init_driver()
# print(Compare_Screen_By_Text("Location permission needed,20"))

# def Compare_Screen_By_Image(input_str, threshold=0.90, retries=3, scale_factors=(1.0, 0.9, 1.1)):
#     """
#     Check if a small reference image exists in the current screen using template matching (robust).

#     Args:
#         input_str (str): "ref_image_path,timeout"
#         threshold (float): Match confidence threshold
#         retries (int): Number of re-captures before concluding Not Ok
#         scale_factors (tuple): Different scales to try for template (to handle resolution/zoom changes)

#     Returns:
#         str: "Ok#" / "Not Ok#" / "ERROR#"
#     """
#     try:
#         # Parse input
#         param1, param2 = input_str.split(",", 1)
#         ref_path = param1.strip()
#         timeout = int(param2.strip())

#         filename = os.path.basename(ref_path).lower()

#         if not init_driver():
#             return "ERROR: Driver not initialized"

#         # Load reference image in grayscale
#         ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
#         if ref_img is None:
#             return f"ERROR: Reference image not found at {ref_path}"

#         start_time = time.time()
#         attempt = 0

#         while time.time() - start_time < timeout and attempt < retries:
#             attempt += 1
#             sleep(1)  # allow UI to stabilize a bit

#             result = capture_screenshot(temp_path)
#             if isinstance(result, str) and result.lower().startswith("error"):
#                 return f"ERROR: Failed to capture screenshot -> {result}"

#             curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#             if curr_img is None:
#                 return f"ERROR: Screenshot not readable"

#             # Save for debugging
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             save_path = os.path.join(Screenshot_path, f"screenshot_{timestamp}.png")
#             cv2.imwrite(save_path, curr_img)

#             # Abort check
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Not Ok# Aborted by abort signal"

#             best_match = 0
#             for scale in scale_factors:
#                 if scale != 1.0:
#                     new_w = int(ref_img.shape[1] * scale)
#                     new_h = int(ref_img.shape[0] * scale)
#                     if new_w < 10 or new_h < 10:  # skip too small scales
#                         continue
#                     resized = cv2.resize(ref_img, (new_w, new_h))
#                 else:
#                     resized = ref_img

#                 # Template Matching (multiple methods for robustness)
#                 for method in [cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED]:
#                     res = cv2.matchTemplate(curr_img, resized, method)
#                     _, max_val, _, max_loc = cv2.minMaxLoc(res)
#                     best_match = max(best_match, max_val)

#             print(f"[DEBUG] Attempt#{attempt} Best confidence = {best_match:.4f}")

#             # Decision
#             if filename == "connectivity.jpg":
#                 if best_match >= threshold:
#                     return f"Ok# Vehicle connectivity is TRUE.+{save_path}"
#                 else:
#                     continue  # retry
#             else:
#                 if best_match >= threshold:
#                     return f"Ok# Reference image found on screen.+{save_path}"
#                 else:
#                     continue  # retry

#         # After retries/timeout, final failure
#         if filename == "connectivity.jpg":
#             return f"Not Ok# Vehicle connectivity is FALSE.+{save_path}"
#         else:
#             return f"Not Ok# Reference image NOT found on screen.+{save_path}"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Compare_Screen_By_Image failed: {str(e)}"


# def Compare_Screen_By_Image(input_str, threshold=0.90, retries=3, scale_factors=(1.0, 0.9, 1.1), debug=False):
#     """
#     Robustly check if a reference image exists on the current screen using multi-scale template matching.

#     Args:
#         input_str (str): "ref_image_path,timeout"
#         threshold (float): Confidence threshold for matching
#         retries (int): Number of retries before declaring Not Ok
#         scale_factors (tuple): Scaling factors to handle resolution/zoom differences
#         debug (bool): If True, prints debug information

#     Returns:
#         str: "Ok#" / "Not Ok#" / "ERROR:"
#     """
#     try:
#         # Parse input
#         parts = input_str.split(",", 1)
#         if len(parts) != 2:
#             return "ERROR: Input format must be 'ref_image_path,timeout'"

#         ref_path = parts[0].strip()
#         timeout = float(parts[1].strip())
#         filename = os.path.basename(ref_path).lower()

#         # Check driver
#         if not init_driver():
#             return "ERROR: Driver not initialized"

#         # Load reference image in grayscale
#         ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
#         if ref_img is None:
#             return f"ERROR: Reference image not found at {ref_path}"

#         start_time = time.time()
#         attempt = 0

#         while time.time() - start_time < timeout and attempt < retries:
#             attempt += 1
#             sleep(1)  # allow UI to stabilize

#             # Abort check
#             if os.path.exists(file_to_watch):
#                 try:
#                     os.remove(file_to_watch)
#                 except:
#                     pass
#                 return "Not Ok# Aborted by abort signal"

#             # Capture screenshot
#             capture_result = capture_screenshot(temp_path)
#             if not capture_result or not os.path.exists(temp_path):
#                 if debug:
#                     safe_print(f"[WARN] Screenshot failed: {capture_result}")
#                 sleep(1)
#                 continue

#             curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#             if curr_img is None:
#                 if debug:
#                     safe_print("[WARN] Screenshot not readable")
#                 sleep(1)
#                 continue

#             # Save for debugging
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             save_path = os.path.join(Screenshot_path, f"screenshot_{timestamp}.png")
#             cv2.imwrite(save_path, curr_img)

#             best_match = 0
#             for scale in scale_factors:
#                 if scale != 1.0:
#                     new_w = int(ref_img.shape[1] * scale)
#                     new_h = int(ref_img.shape[0] * scale)
#                     if new_w < 10 or new_h < 10:
#                         continue
#                     resized = cv2.resize(ref_img, (new_w, new_h))
#                 else:
#                     resized = ref_img

#                 # Multiple template matching methods for robustness
#                 for method in [cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED]:
#                     res = cv2.matchTemplate(curr_img, resized, method)
#                     _, max_val, _, _ = cv2.minMaxLoc(res)
#                     best_match = max(best_match, max_val)

#             if debug:
#                 safe_print(f"[DEBUG] Attempt#{attempt} Best confidence = {best_match:.4f}")

#             # Decision based on image type
#             if best_match >= threshold:
#                 if filename == "connectivity.jpg":
#                     return f"Ok# Vehicle connectivity is TRUE.+{save_path}"
#                 else:
#                     return f"Ok# Reference image found on screen.+{save_path}"

#             # If not matched, wait a bit and retry
#             sleep(0.5)

#         # After timeout/retries
#         if filename == "connectivity.jpg":
#             return f"Not Ok# Vehicle connectivity is FALSE.+{save_path}"
#         else:
#             return f"Not Ok# Reference image NOT found on screen.+{save_path}"

#     except Exception as e:
#         try:
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#         except:
#             pass
#         return f"ERROR: Compare_Screen_By_Image failed: {str(e)}"

def Compare_Screen_By_Image(input_str, threshold=0.90, timeout=5, retries=3, scales=(1.0, 0.9, 1.1)):
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
        mark_driver_busy()
        # Parse input
        ref_path, t = input_str.split(",", 1)
        ref_path = ref_path.strip()
        timeout = int(t.strip())

        if not init_driver():
            return "ERROR: Driver not initialized"

        # Wait for UI to stabilize
        time.sleep(timeout)

        # Capture current screenshot
        result = capture_screenshot(temp_path)
        if isinstance(result, str) and result.lower().startswith("error"):
            return f"ERROR: Failed to capture screenshot -> {result}"

        # Load images in grayscale
        ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        if ref_img is None:
            return f"ERROR: Reference image not found -> {ref_path}"
        if curr_img is None:
            return f"ERROR: Screenshot image not found -> {temp_path}"

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
                    
        mark_driver_idle()

        # -------------------------
        # 3️⃣ Return final result
        # -------------------------
        filename = os.path.basename(ref_path).lower()
        if filename == "connectivity.jpg":
            return f"{'Ok# Vehicle connectivity is TRUE' if found else 'Not Ok# Vehicle connectivity is FALSE'}.+{save_path}"
        else:
            return f"{'Ok# Reference image found on screen' if found else 'Not Ok# Reference image NOT found on screen'}.+{save_path}"
        
        

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Compare_Screen_By_Image failed: {str(e)}"

# init_driver()
# print(Compare_Screen_By_Image("D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Connectivity.jpg,10"))


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


# def Scroll_and_Click_Text(text_maxScrolls, threshold=0.98):
#     try:
#         import traceback
#         from time import sleep

#         param1, param2 = text_maxScrolls.split(",", 1)
#         target_text = param1.strip()
#         max_scrolls = int(param2.strip())
        
        
#         if not init_driver():
#             return "[ERROR] Appium driver initialization failed"

#         prev_screenshot = take_screenshot_cv(driver)
#         scroll_count = 0

#         while scroll_count < max_scrolls:
#             scroll_count += 1
#             safe_print(f"[SCROLL] Attempt #{scroll_count}")
           

#             elements = driver.find_elements("xpath", f"//*[@text='{target_text}']")
#             for el in elements:
#                 try:
#                     el.click()  # ✅ attempt click immediately
#                     safe_print(f"[SUCCESS] Clicked on text: '{target_text}' after {scroll_count} scroll(s)")
#                     return f"Ok# Scrolled and clicked on text {target_text}"
#                 except Exception as click_err:
#                     safe_print(f"[RETRY] Click failed due to: {click_err} — retrying after re-fetch...")

#             scroll_down_continuous(driver)
#             sleep(0.5)

#             end_reached, new_screenshot = is_end_of_scroll(driver, prev_screenshot, threshold)
#             safe_print(f"[SSIM] Scroll#{scroll_count} SSIM-based EndReached: {end_reached}")
#             if end_reached:
#                 capture_screenshot(temp_path)
#                 curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 save_path = f"screenshot_{timestamp}.png"
#                 full_path = os.path.join(Screenshot_path, save_path)
#                # Save the image
#                 cv2.imwrite(full_path, curr_img)
#                 return f"Not ok# Scrolled but not found text {target_text}+{full_path}"

#             prev_screenshot = new_screenshot

#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break
        
#         capture_screenshot(temp_path)
#         curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         save_path = f"screenshot_{timestamp}.png"
#         full_path = os.path.join(Screenshot_path, save_path)
#         # Save the image
#         cv2.imwrite(full_path, curr_img)

#         return f"Not ok# Scrolled but not found text {target_text}+{full_path}"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         err = f"[ERROR] scroll_and_click_text failed: {e}\n{traceback.format_exc()}"
#         safe_print(err)
#         return err

def Scroll_and_Click_Text(text_maxScrolls, threshold=0.98, scroll_pause=0.5, retry=2, debug=False):
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
        
        mark_driver_busy()

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
        
        mark_driver_idle()

        # screenshot_path = save_screenshot("scroll_max")
        return f"Not Ok# Text '{target_text}' not found after {max_scrolls} scrolls.+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch): 
            try: os.remove(file_to_watch)
            except: pass
        err_msg = f"[ERROR] Scroll_and_Click_Text failed: {e}\n{traceback.format_exc()}"
        safe_print(err_msg)
        return err_msg


    
# init_driver()
# print(Scroll_and_Click_Text("Register or Sign In,5"))


# def Scroll_and_Click_Image(path_maxScroll, threshold=0.98):
#     """
#     Scrolls the screen until a target image is found and clicks it.

#     Args:
#         path_maxScroll (str): "image_path,max_scrolls"
#         threshold (float): SSIM threshold to detect end of scroll

#     Returns:
#         str: "Ok# Clicked on target image"
#              "Not Ok# Target image not found after scrolling"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <details>"
#     """
#     try:
#         param1, param2 = path_maxScroll.split(",", 1)
#         image_path = param1.strip()
#         max_scrolls = int(param2.strip())
         

#         if not init_driver():
#             return "ERROR: Appium driver initialization failed"

#         template = load_reference_image(image_path)
#         if template is None:
#             return f"ERROR: Reference image not found at {image_path}"

#         prev_screenshot = take_screenshot_cv(driver)
#         scroll_count = 0

#         while scroll_count < max_scrolls:
#             scroll_count += 1

#             screenshot = take_screenshot_cv(driver)
#             pos = find_template_in_screenshot(screenshot, template, threshold)

#             if pos:
#                 try:
#                     driver.execute_script("mobile: clickGesture", {"x": pos[0], "y": pos[1]})
#                     return f"Ok# Clicked on target image after {scroll_count} scroll(s)"
#                 except Exception as click_err:
#                     return f"ERROR: Click gesture failed on '{image_path}': {click_err}"

#             scroll_down_continuous(driver)

#             end_reached, new_screenshot = is_end_of_scroll(driver, prev_screenshot, threshold)
#             if end_reached:
#                 capture_screenshot(temp_path)
#                 curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 save_path = f"screenshot_{timestamp}.png"
#                 full_path = os.path.join(Screenshot_path, save_path)
#                # Save the image
#                 cv2.imwrite(full_path, curr_img)
#                 return f"Not Ok# Target image not found after {scroll_count} scroll(s)+{full_path}"

#             prev_screenshot = new_screenshot

#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return f"Not Ok# Aborted by abort signal"
        
#         temp_path=capture_screenshot(temp_path)
#         curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         save_path = f"screenshot_{timestamp}.png"
#         full_path = os.path.join(Screenshot_path, save_path)
#                # Save the image
#         cv2.imwrite(full_path, curr_img)

#         return f"Not Ok# Target image not found after {max_scrolls} scroll(s)+{full_path}"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Scroll_and_Click_Image failed: {str(e)}"

# -------------------------
# Updated helper functions for robustness

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
    
def Scroll_and_Click_Image(path_maxScroll, threshold=0.98):
    """
    Scroll until a target image is found and click it.

    Args:
        path_maxScroll (str): "image_path,max_scrolls"
        threshold (float): SSIM threshold for end-of-scroll detection

    Returns:
        str: Ok / Not Ok / Aborted / ERROR messages with screenshot path on failure
    """
    try:
        mark_driver_busy()
        param1, param2 = path_maxScroll.split(",", 1)
        image_path = param1.strip()
        max_scrolls = int(param2.strip())

        if not os.path.exists(image_path):
            return f"ERROR: Reference image not found: {image_path}"

        if not init_driver():
            return "ERROR: Appium driver initialization failed"

        template = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if template is None:
            return f"ERROR: Failed to read reference image: {image_path}"

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
                    return f"ERROR: Click gesture failed on '{image_path}': {click_err}"

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
        mark_driver_idle()
        return f"Not Ok# Target image not found after {max_scrolls} scroll(s)+screenshot_saved"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Scroll_and_Click_Image failed: {str(e)}"
    
# init_driver()
# print(Scroll_and_Click_Image("D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Register.png,5"))







def Scroll(input_str):
    """
    LabVIEW-compatible single scroll function.
    Input: 'up', 'down', 'left', or 'right'
    Output: Single string with status
    """
    try:
        mark_driver_busy()
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
        mark_driver_idle()
        return f"Ok#Scrolled"

    except Exception as e:
        return f"ERROR:scroll failed: {str(e)}"

############################################################ Tap using coordinates ########################################################

def Click_By_Coordinate(coord_string):
    """
    Clicks on the screen at specified coordinates.

    Args:
        coord_string (str): "x_y,timeout" (timeout is ignored but parsed for consistency)

    Returns:
        str: "Ok# Clicked at coordinates (x, y)"
             "Not Ok# Invalid input or driver not initialized"
             "Not Ok# Aborted by abort signal"
             "ERROR: <details>"
    """
    try:
        mark_driver_busy()
        param1, param2 = coord_string.split(",", 1)  # timeout ignored for now

        # Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        # Attempt driver recovery if needed
        if driver is None or not is_driver_alive(driver):
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
        mark_driver_idle()
        return f"Ok# Clicked at coordinates ({x}, {y})"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Click_By_Coordinate failed: {str(e)}"





                                                    ######### Realtime coordinates ############


def get_touch_range():
    output = subprocess.check_output(['adb', 'shell', 'getevent', '-p'], universal_newlines=True)
    x_range = y_range = None
    for line in output.splitlines():
        if 'ABS_MT_POSITION_X' in line or '0035' in line:
            x_range = list(map(int, re.findall(r'min (\d+), max (\d+)', line)[0]))
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


def Send_Inputs(text):
    """
    Sends input text to the appropriate EditText field(s) on the screen.

    Args:
        text (str): "key:value,timeout" or just "value,timeout" if only one input field

    Returns:
        str: "Ok# Input sent successfully"
             "Not Ok# Input field not found within timeout"
             "Not Ok# Aborted by abort signal"
             "ERROR: <details>"
    """
    try:
        mark_driver_busy()
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
            return "ERROR: Driver not initialized"

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
        
        mark_driver_idle()

        # Timeout reached
        return f"Not Ok# Input field not found+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Send_Inputs failed: {str(e)}"



# init_driver()
# Send_Inputs("Mobile number:2580,10")
# for i in range(30):
#     Swipe_From_Right_Edge("dummy")


########################################### Swipe Operation ##############################################

def Swipe_From_Left_Edge(text):
    """
    Performs a left-edge swipe to the right.

    Args:
        text (str): "param,timeout" format (timeout is ignored here)

    Returns:
        str: "Ok" / "Not Ok# Aborted by abort signal" / "ERROR: <details>"
    """
    try:
        
        mark_driver_busy()
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
            
        mark_driver_idle()

        return "Ok#Swiped from left edge"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Swipe_From_Left_Edge failed: {str(e)}"



def Swipe_From_Right_Edge(text):
    try:
        
        mark_driver_busy()

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
        
        mark_driver_idle()

        return "Ok#Swiped from right edge"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            
        return f"Error:Swipe from right edge failed: {str(e)}"

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
        mark_driver_busy()

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        param1, param2 = path.split(",", 1)
        filepath = param1
        if driver is None:
            return "ERROR: Driver is not initialized"

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
        
        mark_driver_idle()

        return filepath

    except WebDriverException as e:
        return f"ERROR: Screenshot error\n{str(e)}"
    except Exception:
        return f"ERROR: Unknown error\n{traceback.format_exc()}"


def SS(path):
    
    try:
        mark_driver_busy()

        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)

        param1, param2 = path.split(",", 1)
        filepath = param1
        if driver is None:
            return "ERROR: Driver is not initialized"

        if is_flag_secure():
            return "SKIPPED: FLAG_SECURE screen blocks screenshot"

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
        
        mark_driver_idle()

        return filepath

    except WebDriverException as e:
        return f"ERROR: Screenshot error\n{str(e)}"
    except Exception:
        return f"ERROR: Unknown error\n{traceback.format_exc()}"

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
            return "SKIPPED: FLAG_SECURE screen blocks screenshot"

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
                return f"ERROR: Restart failed\n{restart_result}"
            try:
                if is_flag_secure():
                    return "SKIPPED: FLAG_SECURE after restart"

                # Same logic after restart
                png_path = filepath.replace(".jpg", ".png")
                driver.get_screenshot_as_file(png_path)
                image = Image.open(png_path).convert("RGB")
                image.save(filepath, "JPEG")
                os.remove(png_path)

                return filepath
            except Exception as retry_error:
                return f"ERROR: Retry failed\n{str(retry_error)}"
        return f"ERROR: Screenshot error\n{str(e)}"
    except Exception as ex:
        return f"ERROR: Unknown error\n{traceback.format_exc()}"


##########################################################################################################

def Swipe_Up(input):
    """
    Perform a single swipe up gesture.

    Args:
        duration (int): Duration of the swipe in ms (default 800)

    Returns:
        str: "Ok# Swiped up"
             "Not Ok# Aborted by abort signal"
             "ERROR: <details>"
    """
    try:
        mark_driver_busy()
        # ✅ Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        size = driver.get_window_size()
        width, height = size["width"], size["height"]

        start_x = width // 2
        start_y = int(height * 0.90)  # bottom
        end_y   = int(height * 0.60)  # drag up

        driver.swipe(start_x, start_y, start_x, end_y, 800)
        mark_driver_idle()
        return "Ok# Swiped up"

    except Exception as e:
        return f"ERROR (Swipe Up): {str(e)}"


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
        
        mark_driver_busy()
        # ✅ Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        size = driver.get_window_size()
        width, height = size["width"], size["height"]

        start_x = width // 2
        start_y = int(height * 0.60)  # higher up
        end_y   = int(height * 0.90)  # bottom

        driver.swipe(start_x, start_y, start_x, end_y, 800)
        mark_driver_idle()
        return "Ok# Swiped down"

    except Exception as e:
        return f"ERROR (Swipe Down): {str(e)}"

# init_driver()
# Swipe_Up()

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
        return f"ERROR: {str(e)}"

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




def Compare_Screen_By_Multiple_Texts(input_text, scroll_distance=100):
    """
    Take screenshot, extract text via OCR, and check if multiple given texts are present.

    Args:
        input_text (str): "text1:text2:text3,timeout"
        scroll_distance (int): Pixels to scroll up/down when text is missing

    Returns:
        str: "Ok# All texts found"
             "Not Ok# Only <count>/<total> texts found"
             "ERROR: <details>"
    """
    try:
        mark_driver_busy()
        # Split inputs and timeout
        param1, param2 = input_text.split(",", 1)
        search_list = [x.strip() for x in param1.split(":") if x.strip()]
        timeout = int(param2.strip())
        total = len(search_list)

        found = set()
        start_time = time.time()

        Ok_output=""
        Not_ok_output=""

        # Get device window size (for dynamic swipe)
        window_size = driver.get_window_size()
        width = window_size["width"]
        height = window_size["height"]

        # Define swipe helpers
        def swipe_up(distance):
            driver.swipe(width // 2, height // 2, width // 2, height // 2 - distance, 300)

        def swipe_down(distance):
            driver.swipe(width // 2, height // 2, width // 2, height // 2 + distance, 300)

        while time.time() - start_time < timeout:
            # Capture screenshot in memory (not saved)
            screenshot = driver.get_screenshot_as_png()
            image = cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_COLOR)

            # OCR extraction
            text = pytesseract.image_to_string(image)
            text=extract_status(text)

            # Debug log
            print("[OCR Extracted Text]:", text)

            # Case-insensitive search for each string
            for s in search_list:
                if s.lower() in text.lower():
                    found.add(s)

            itr=0

            # If all found → Ok
            if len(found) == total:
                for i in found:
                    Ok_output+=i
                    if itr < (len(found) - 1):
                        Ok_output+=", "
            
                return f"Ok# Status found on screen: {Ok_output}"

            # Scroll if required (only once per loop)
            missing = [s for s in search_list if s not in found]
            if missing:
                if missing[0] == search_list[0]:
                    print("[Action]: Scrolling slightly UP (first text missing)")
                    swipe_up(scroll_distance)
                elif missing[-1] == search_list[-1]:
                    print("[Action]: Scrolling slightly DOWN (last text missing)")
                    swipe_down(scroll_distance)

            sleep(1)  # small delay before retry

             # If all found → Ok
            for i in missing:
                Not_ok_output+=i
                if itr < (len(found) - 1):
                    Not_ok_output+=", "
        
         
        capture_screenshot(temp_path)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)

        mark_driver_idle()

        # Timeout reached → Not ok
        return f"Not ok# Missing status on screen: {Not_ok_output}+{full_path}"

    except Exception as e:
        return f"ERROR: {str(e)}"
    

# init_driver()
# print(Compare_Screen_By_Multiple_Texts("Register,10"))

# init_driver()
# print(capture_and_read_text())

def Validate_Status(input_str):
    """
    Validate each feature (all words except last) against expected status (last word).

    Args:
        input_str (str): "Front Driver Closed:Rear Passenger Open,10"
                         (multiple items separated by ":" and timeout after comma)

    Returns:
        str: "Ok# ..." with PASS/FAIL results or "ERROR"
    """
    try:
        
        mark_driver_busy()
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

        for item in Status_Arr:
            sleep(timeout)
            #print(item)

            # 1. Take screenshot with current date & time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(base_dir, f"status_{timestamp}.png")
            driver.save_screenshot(screenshot_path)

            # 2. OCR on screenshot
            image = cv2.imread(screenshot_path)
            text = pytesseract.image_to_string(image)
            text=extract_status(text)

            print("\n OCR text: \n",text)

            # 3. Split feature & expected result
            parts = item.split()
            feature = " ".join(parts[:-1])
            expected = parts[-1]
            
            clean_text = feature.replace('\n', ' ').replace('\r', ' ').strip()

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
        mark_driver_idle()
        return output

    except Exception as e:
        print(f"Error: {e}")
        return "ERROR"

# init_driver()
# print(Validate_Status(",10"))

def Validate_Alerts(search_str):
    """
    Open notifications, take screenshot, extract text,
    search for a string, clear notifications, and close panel.

    Args:
        search_str (str): String to search in notification text, format: "alert1:alert2:alert3,...timeout"

    Returns:
        str: "Ok# ..." with PASS/FAIL results or "ERROR"
    """
    try:
        
        mark_driver_busy()
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

            while True:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    break  # Time’s up

                # Take screenshot
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(base_dir, f"notification_comman.png")
                driver.save_screenshot(screenshot_path)

                # OCR extract text
                image = cv2.imread(screenshot_path)
                text = pytesseract.image_to_string(image)
                print(text)

                if alert_text.lower() in text.lower():
                    found = True
                    screenshot_path = os.path.join(base_dir, f"notification_{timestamp}.png")
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
            op=Click_By_Text("Clear all,1")
            op1,op2=op.split("#",1)
            if op1 != "Ok":
                driver.back()

        else:
            driver.back()  # optional close notifications panel
            
        mark_driver_idle()
       
       

        return output

    except Exception as e:
        print(f"Error: {e}")
        driver.back()
        return "ERROR"

# init_driver()
# print(Validate_Alerts("Service-due alert$received,10"))

# def Check_Remote_Command_Status(input,base_dir=Screenshot_path, interval=0.5):
#     """
#     Continuously capture screenshots and OCR-check for 'Successfull/Successful'
#     until timeout. Ends early if found.
 
#     Args:
#         base_dir (str): Directory to save screenshot
#         timeout (int): Max time in seconds to wait
#         interval (float): Interval in seconds between checks
 
#     Returns:
#         str: "Ok# Remote command executed successfully, Screenshot: <path>"
#              "Not Ok# Remote command not executed successfully, Screenshot: <path>"
#              "ERROR: <details>"
#     """
#     try:
#         param1, param2 = input.split(",", 1)
#         timeout=int(param2)
#         if not os.path.exists(base_dir):
#             os.makedirs(base_dir)
 
#         end_time = time.time() + timeout
#         #screenshot_path = None
#         text = ""
#         Common_Ref_Img_Path
 
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
        
#         png = Common_Ref_Img_Path
#         np_img = np.frombuffer(png, np.uint8)
#         image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

#         # OCR
#         text = pytesseract.image_to_string(image)

#         # Save last screenshot
#         timestamp = time.strftime("%Y%m%d_%H%M%S")
#         screenshot_path = os.path.join(base_dir, f"quick_validate_{timestamp}.png")
#         with open(screenshot_path, "wb") as f:
#             f.write(png)

#         # Check success
#         if "Successfully" in text or "Successful" in text:
#             return f"Ok# Remote command executed successfully.+{screenshot_path}"
        
#         while time.time() < end_time:
#             # Capture screenshot (in memory)
#             png = driver.get_screenshot_as_png()
#             np_img = np.frombuffer(png, np.uint8)
#             image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
 
#             # OCR
#             text = pytesseract.image_to_string(image)
 
#             # Save last screenshot
#             timestamp = time.strftime("%Y%m%d_%H%M%S")
#             screenshot_path = os.path.join(base_dir, f"quick_validate_{timestamp}.png")
#             with open(screenshot_path, "wb") as f:
#                 f.write(png)
 
#             # Check success
#             if "Successfully" in text or "Successful" in text:
#                 return f"Ok# Remote command executed successfully.+{screenshot_path}"
 
#             #sleep(interval)  # wait before next check
 
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break
 
#         # Timeout reached → Not ok
#         return f"Not ok# Remote command not executed successfully.+{screenshot_path}"
 
#     except Exception as e:
#         return f"ERROR: {str(e)}"

def Check_Remote_Command_Status(input_str,interval=0.2):
    """
    Check if remote command was executed successfully by scanning an existing image.
    """
    try:
        mark_driver_busy()
        param1, param2 = input_str.split(",", 1)
        timeout = int(param2)

        # Load the image
        image = cv2.imread(Common_Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return f"ERROR: Could not load image from {Common_Ref_Img_Path}"

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
            
            mark_driver_idle()
            return f"Not ok# Remote command not executed successfully.+{screenshot_path}"

    except Exception as e:
        return f"ERROR: {str(e)}"

# init_driver()
# print(Check_Remote_Command_Status("Horn,180"))

# def Long_Press_Indirect_By_Image(image_path, duration=3000, threshold=0.8):
#     param1, param2 = image_path.split(",", 1)
#     img_path = param1
#     timeout = int(param2)

#     screenshot_file = os.path.join(Screenshot_path, "temp.png")
#     driver.save_screenshot(screenshot_file)

#     screen = cv2.imread(screenshot_file)
#     template = cv2.imread(img_path)

#     if screen is None or template is None:
#         return "ERROR: Failed to read images"

#     result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
#     _, max_val, _, max_loc = cv2.minMaxLoc(result)

#     if max_val < threshold:
#         return f"Not Ok# Image '{image_path}' not found"

#     x = max_loc[0] + template.shape[1] // 2
#     y = max_loc[1] + template.shape[0] // 2

#     # Indirect long press using TouchAction
#     action = TouchAction(driver)
#     action.press(x=x, y=y).wait(ms=duration).release().perform()

#     return f"Ok# Long pressed on image '{image_path}' indirectly at ({x},{y})"

# def Long_Press_Indirect_By_Image(image_path, duration=2000, threshold=0.8):
#     """
#     Long press on an element found by image reference using mobile: dragGesture.

#     Args:
#         image_path (str): "path_to_image,timeout"
#         duration (int): Long press duration in ms
#         threshold (float): Template matching threshold

#     Returns:
#         str
#     """
#     try:
#         param1, param2 = image_path.split(",", 1)
#         img_path = param1.strip()
#         timeout = int(param2)

#         screenshot_file = os.path.join(Screenshot_path, "temp.png")
#         driver.save_screenshot(screenshot_file)

#         screen = cv2.imread(screenshot_file)
#         template = cv2.imread(img_path)

#         if screen is None or template is None:
#             return "ERROR: Failed to read images"

#         result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
#         _, max_val, _, max_loc = cv2.minMaxLoc(result)

#         if max_val < threshold:
#             return f"Not Ok# Image '{image_path}' not found"

#         x = max_loc[0] + template.shape[1] // 2
#         y = max_loc[1] + template.shape[0] // 2

#         # ✅ Use dragGesture to simulate long press at the same position
#         driver.execute_script(
#             "mobile: dragGesture",
#             {
#                 "startX": x,
#                 "startY": y,
#                 "endX": x,      # same point for long press
#                 "endY": y,
#                 "duration": duration  # hold time in ms
#             }
#         )

#         return f"Ok# Long pressed on image '{image_path}' at ({x},{y})"

#     except Exception as e:
#         return f"ERROR: Long_Press_Indirect_By_Image failed: {str(e)}"

# def Long_Press_Indirect_By_Image(image_path, duration=2000, threshold=0.85):
#     """
#     Long press on an element found by image reference using mobile: dragGesture.
#     Works across all resolutions (scales coordinates).

#     Args:
#         image_path (str): "path_to_image,timeout"
#         duration (int): Long press duration in ms
#         threshold (float): Template matching threshold (default 0.85)

#     Returns:
#         str
#     """
#     try:
#         param1, param2 = image_path.split(",", 1)
#         img_path = param1.strip()
#         timeout = int(param2)
#         duration = timeout * 1000

#         screenshot_file = os.path.join(Screenshot_path, "temp.png")
#         driver.save_screenshot(screenshot_file)

#         screen = cv2.imread(screenshot_file)
#         template = cv2.imread(img_path)

#         if screen is None or template is None:
#             return "ERROR: Failed to read images"

#         # Template matching
#         result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
#         _, max_val, _, max_loc = cv2.minMaxLoc(result)

#         if max_val < threshold:
#             return f"Not Ok# Image '{image_path}' not found (max_val={max_val:.2f})"

#         # Get match center (in screenshot coordinates)
#         x = max_loc[0] + template.shape[1] // 2
#         y = max_loc[1] + template.shape[0] // 2

#         # Normalize → convert to device resolution
#         screen_h, screen_w = screen.shape[:2]
#         window_size = driver.get_window_size()
#         dev_w, dev_h = window_size["width"], window_size["height"]

#         norm_x = x / screen_w
#         norm_y = y / screen_h
#         dev_x = int(norm_x * dev_w)
#         dev_y = int(norm_y * dev_h)

#         # Extra validation (SSIM check on region to reduce false positives)
#         try:
#             matched_region = screen[y - template.shape[0]//2:y + template.shape[0]//2,
#                                     x - template.shape[1]//2:x + template.shape[1]//2]
#             if matched_region.shape[:2] == template.shape[:2]:
#                 from skimage.metrics import structural_similarity as ssim
#                 gray_ref = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
#                 gray_crop = cv2.cvtColor(matched_region, cv2.COLOR_BGR2GRAY)
#                 score, _ = ssim(gray_ref, gray_crop, full=True)
#                 if score < 0.70:  # reject if not visually similar
#                     return f"Not Ok# False match rejected (SSIM={score:.2f})"
#         except Exception:
#             pass  # fallback if crop fails

#         # ✅ Use dragGesture for long press
#         driver.execute_script(
#             "mobile: dragGesture",
#             {
#                 "startX": dev_x,
#                 "startY": dev_y,
#                 "endX": dev_x,      # same point → long press
#                 "endY": dev_y,
#                 "duration": duration
#             }
#         )

#         return f"Ok# Long pressed on image '{image_path}' at ({dev_x},{dev_y})"

#     except Exception as e:
#         return f"ERROR: Long_Press_Indirect_By_Image failed: {str(e)}"



def Long_Press_Indirect_By_Image(image_path, duration=2000, threshold=0.85):
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
        mark_driver_busy()
        param1, param2 = image_path.split(",", 1)
        img_path = param1.strip()
        timeout = int(param2)
        duration = timeout * 1000

        screenshot_file = os.path.join(Screenshot_path, "temp.png")
        driver.save_screenshot(screenshot_file)

        screen = cv2.imread(screenshot_file)
        template = cv2.imread(img_path)

        if screen is None or template is None:
            return "ERROR: Failed to read images"

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
        mark_driver_idle()

        exec_time = (time.perf_counter() - start_time) * 1000  # ms
        return f"Ok# Long pressed on image '{image_path}' at ({dev_x},{dev_y}) | ExecTime={exec_time:.2f}ms"

    except Exception as e:
        exec_time = (time.perf_counter() - start_time) * 1000  # ms
        return f"ERROR: Long_Press_Indirect_By_Image failed: {str(e)} | ExecTime={exec_time:.2f}ms"



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
            return f"ERROR: Failed to start logging - {e}"

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
            return f"ERROR: Failed to stop logging - {e}"

    else:
        return "ERROR: Unknown command. Use 'start' or 'stop'"
    
    
# init_driver()

# print(log_handler("start,1"))
# print(log_handler("stop,1"))

def Wait_Until_Text_Disappears(text_to_watch):
    """
    Wait until a given text disappears from the screen.
    Halts until text disappears, or saves screenshot on failure.
    """
    global Common_Ref_Img_Path
    try:
        
        mark_driver_busy()
        param1,param2=text_to_watch.split(",")
        timeout=int(param2)
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{param1}")')
            )
        )

        #sleep(2)
        capture_screenshot(Ref_Img_Path)
        curr_img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"Ref_Screenshot.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)
        Common_Ref_Img_Path=full_path
        print(Common_Ref_Img_Path)
        mark_driver_idle()
        return "Ok# Screen got changed"
    except Exception:
        # Take screenshot directly
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_path = os.path.join(
            Screenshot_path, f"screenshot_{timestamp}.png"
        )
        driver.get_screenshot_as_file(full_path)
        return f"Not Ok# Text '{param1}' still present after {timeout} sec+{full_path}"
    
# init_driver()
# print(Wait_Until_Text_Disappears("USB debugging connected,5"))


# init_driver()
# print(Wait_Until_Text_Disappears("Connecting you to your car,180"))
# print(Check_Remote_Command_Status("Horn,80"))