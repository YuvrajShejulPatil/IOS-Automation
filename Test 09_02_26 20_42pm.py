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


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# from datetime import datetime
temp_path = "C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\temp_img.png"
#temp_path = "D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\temp_img.png"
Ref_Img_Path = "C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\ref_img.png"
Image_File_Path = "C:\\MaxEye\\MEP00179\\Application\\Configuration_Files\\Appium\\Image FIle Path\\Image_Path.txt"
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
x_str = None
y_str = None
app_evpv = 0 #0 PV 1 EV
knob = 0
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



def file_watcher(filepath, check_interval=1):
    """Background watcher that monitors for a stop file."""
    while not stop_event.is_set():
        if os.path.exists(filepath):
            print(f"[STOP TRIGGER] File detected: {filepath}")
            stop_event.set()
            try:
                if driver:
                    driver.quit()
                    
                driver = None
                os.remove(file_to_watch) 
                failcaseinit("demo")
                print("[STOP ACTION] Appium driver terminated.")
            except Exception as e:
                print(f"[ERROR stopping driver]: {e}")
            break
        time.sleep(check_interval)
        

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
        driver = webdriver.Remote("http://localhost:4723", caps)
        # sleep(1)
        # start_keep_alive()
        safe_print("[INIT] Appium driver initialized")
        app_package = caps["appPackage"]
        device_id = caps["udid"]
        print(device_id)
        # Launch WhatsApp using ADB monkey command

        ensure_app_in_foreground(app_package)
        
        stop_event = threading.Event()
        stop_event.clear()
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

def Restart_App_Package_Name_Text(input):
    """
    LabVIEW-safe, hang-proof app restart
    Input  : "Tata Motors PV App,<optional>"
    Output : "Ok#..." or "Not ok#..."
    """
    global app_evpv

    def adb(cmd, timeout=5):
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
            app_evpv=0
        else:
            package_name = "com.tatamotors.evoneapp"
            app_evpv=1

        # ---------------- FORCE STOP ----------------
        cmd = ["adb"]
        if device_id:
            cmd += ["-s", device_id]
        cmd += ["shell", "am", "force-stop", package_name]

        _, err = adb(cmd, timeout=4)
        if "ADB_TIMEOUT" in err:
            return "Not ok#ADB timeout during force-stop"

        sleep(0.8)

        # ---------------- RESOLVE ACTIVITY ----------------
        cmd = ["adb"]
        if device_id:
            cmd += ["-s", device_id]
        cmd += [
            "shell", "cmd", "package", "resolve-activity",
            "--brief", package_name
        ]

        out, err = adb(cmd, timeout=5)
        if not out or "not found" in out.lower():
            return f"Not ok#Unable to resolve activity for {package_name}"

        lines = out.splitlines()
        if len(lines) < 2:
            return f"Not ok#Invalid resolve-activity output"

        app_activity = lines[1].replace("/", "").strip()

        # ---------------- DIRECT ACTIVITY LAUNCH (MOST RELIABLE) ----------------
        cmd = ["adb"]
        if device_id:
            cmd += ["-s", device_id]
        cmd += [
            "shell", "am", "start",
            "-n", f"{package_name}/{app_activity}"
        ]

        _, err = adb(cmd, timeout=6)
        if "ADB_TIMEOUT" in err:
            return "Not ok#ADB timeout during launch"

        sleep(2)

        # ---------------- FALLBACK (MONKEY) ----------------
        if not is_app_in_foreground(package_name):
            cmd = ["adb"]
            if device_id:
                cmd += ["-s", device_id]
            cmd += [
                "shell", "monkey", "-p", package_name,
                "-c", "android.intent.category.LAUNCHER", "1"
            ]
            adb(cmd, timeout=4)
            sleep(2)

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

def Set_Time_With_Text(input_str):
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

    except Exception as e:
        return f"Not ok#{str(e)}"
    


def Set_Date_With_Text(input_str):
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
            date_str = datetime.now().strftime("%d:%b:%Y")
        else:
            from dateutil.relativedelta import relativedelta

            one_year_later = datetime.now() + relativedelta(days=4)
            print(one_year_later)
            date_str = one_year_later.strftime("%d:%b:%Y")
        
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
        return f"Not ok#{str(e)}"


# init_driver()
# print(Set_Date_With_Text("End,10"))
# print(Set_Time_With_Text("1 mins,10"))

########################################## Hold Swipe to the right Mobilize ############################



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
    
def Click_Hold_Swipe_Right_On_Image(text):
    """
    Detect slider by index, long-hold it, and swipe fully to the right.

    Args:
        text (str): "slider_index,timeout"

    Returns:
        str:
            "Ok#Slider swiped successfully"
            "Not Ok#Aborted by abort signal"
            "Not Ok#<reason>"
    """
    try:
        # Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok#Aborted by abort signal"

        param1, param2 = text.split(",", 1)
        slider_index = int(param1.strip())
        timeout = int(param2.strip())

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
            x_end   = r["x"] + int(r["width"] * 0.90)

            # 🔥 REAL hold + swipe
            driver.execute_script("mobile: dragGesture", {
                "startX": x_start,
                "startY": y,
                "endX": x_end,
                "endY": y,
                "speed": 300
            })

            return "Ok#Slider swiped successfully"

        return "Not Ok#Slider not detected within timeout"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"Not Ok#Click_Hold_Swipe_Right_On_Image failed: {str(e)}"
# init_driver()
# print(Click_Hold_Swipe_Right_On_Image("0,10"))

# init_driver()
# Click_Hold_Swipe_Right_On_Image("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Immobilise.png,5")


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

def Click_Hold_Swipe_Right_By_XY_Text_ValSet(text):
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

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"Not ok#Click_Hold_Swipe_Right_By_Coordinates_Dynamic failed: {str(e)}"
    
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

# def Click_Hold_Swipe_Right_By_Photo_Text_ValSet(text):
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
#         return f"Not ok#Click_Hold_Swipe_Right failed:{str(e)}"

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

def Get_Driver_Score_Text(input):
    global Driver_Score
    param1,param2=input.split(",")

    elements = driver.find_elements(
        AppiumBy.CLASS_NAME,
        "android.widget.TextView"
    )

    # # Safety check
    # if len(elements) <= 6:
    #     return "Not ok#Driver score element not found"

    

    ## Screenshot ##
    capture_screenshot(temp_path)
    curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = f"screenshot_{timestamp}.png"
    full_path = os.path.join(Screenshot_path, save_path)
    cv2.imwrite(full_path, curr_img)

    valid = elements[6]   # direct indexing
    Validation_txt = valid.text.strip()

    el = elements[5]   # direct indexing
    txt = el.text.strip()

    if Validation_txt == "No data available":
        return f"Not ok#No data available on screen+{full_path}"

    if not txt:
        return "Not ok#Empty Driver score text"

    Driver_Score = float(txt)

    if Driver_Score > 0:
        return f"Ok#Driver score: {Driver_Score}+{full_path}"
    else:
        return f"Not ok#Driver Score: {Driver_Score}+{full_path}"

 ################## SOS #################

# ################ Main ###########
    
def PressAndHold_By_Gesture_Text(input_str):
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

    except Exception as e:
        exec_time = (time.perf_counter() - start_time) * 1000
        return f"Not ok# {str(e)} | {exec_time:.1f}ms"

def PressAndHold_By_Image(input_str):
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

    except Exception as e:
        exec_time = (time.perf_counter() - start_time) * 1000
        return f"Not Ok# {str(e)} | {exec_time:.1f}ms"

def Get_Vehicle_Health_Status_Text(input):
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

        # ---------------- Validation logic ----------------
        if section == "systems with issues":
            if parameter in with_issues:
                return f"Ok#System with issues contains {parameter}"
            else:
                return f"Not ok#System with issues does not contain {parameter}"

        elif section == "systems without any issues":
            if parameter in without_issues:
                return f"Ok#System without any issues contains {parameter}"
            else:
                return f"Not ok#System without any issues does not contain {parameter}"

        else:
            return f"Not ok#Unknown section: {section}"

    except Exception as e:
        # ---------------- Global safety net ----------------
        return f"Not ok#Unexpected error: {str(e)}"

def Compare_Screen_By_Text_Optional(input):
    param1, param2 = input.split(",")
    timeout=int(param2)
    sleep(timeout)
    Valid_text = param1.strip().lower()

    elements = driver.find_elements(
        AppiumBy.CLASS_NAME,
        "android.widget.TextView"
    )

    texts = []
    for element in elements:
        if element.text:  # safety check
            texts.append(element.text.lower())
    texts=str(texts).encode("utf-8", errors="ignore").decode()

    print(texts)


    if Valid_text in texts:
        return f"Ok#{Valid_text} text is found on screen"
    else:
        return f"Not ok#{Valid_text} text is not found on screen"

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


def Com_Screen_By_Text_Optional(input):
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
        if element.text:
            cleaned = clean_text(element.text)
            if cleaned:
                texts.append(cleaned)

    # Safe print (no Unicode crash, no symbols)
    print(texts)

    if Valid_text in texts:
        return f"Ok#{Valid_text} text is found on screen"
    else:
        return f"Not ok#{Valid_text} text is not found on screen"

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
        return f"Not ok: {str(e)}\n"

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
        return f"Not ok: {str(e)}\n"

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
        return f"Not ok: {str(e)}\n"

# init_driver()
# Close_Notification_Panel("hi,1")
###################################################### Mobile Resolution ##########################################################

def get_resolution(device_id):
    try:
        param1, param2 = device_id.split(",", 1)
        # Run adb command for the specific device
        result = subprocess.check_output(['adb', '-s', param1, 'shell', 'wm', 'size'], encoding='utf-8')
        
        # Extract width and height using regex
        match = re.search(r'Physical size:\s*(\b+)y(\b+)y, result')
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
        return f"Not ok: Wait_Until_Text_Appears failed: {str(e)}"


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

def Wait_Until_Image_Appears(path_with_timeout, threshold=0.86, check_interval=1.0, timeout_message_screenshot=True, debug=False):
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

    except Exception as e:
        # Ensure abort file cleaned up
        try:
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
        except Exception:
            pass
        return f"Not ok: Wait_Until_Image_Appears failed: {str(e)}"


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

def Click_By_Text(visible_text):
    """
    Robust, dynamic and fail-safe text click handler.

    Input:
        "text_to_click,timeout"

    Output:
        Ok# Clicked on '<text>'
        Not Ok# '<text>' not found + <screenshot_path>
        Not Ok# Aborted by abort signal
        ERROR# <details>
    """

    global Common_Ref_Img_Path

    try:
        # -----------------------------
        # Parse input
        # -----------------------------
        raw_text, raw_timeout = visible_text.split(",", 1)
        search_text = raw_text.lower().strip()
        timeout = int(raw_timeout)

        start_time = time.time()

        # -----------------------------
        # MAIN LOOP
        # -----------------------------
        while time.time() - start_time < timeout:

            # 🔴 Abort handling
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                return "Not Ok# Aborted by abort signal"

            el = None

            # -----------------------------
            # 1️⃣ FAST: Case-insensitive XPath
            # -----------------------------
            fast_xpaths = [
                f"//*[translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='{search_text}']",
                f"//*[contains(translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{search_text}')]",
                f"//*[contains(translate(@content-desc,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{search_text}')]"
            ]

            for xp in fast_xpaths:
                try:
                    el = driver.find_element(By.XPATH, xp)
                    if el:
                        break
                except:
                    pass

            # -----------------------------
            # 2️⃣ MEDIUM: Visible element scan
            # -----------------------------
            if not el:
                try:
                    elements = driver.find_elements(By.XPATH, "//*")
                    for e in elements:
                        try:
                            combined_text = (
                                (e.text or "") + " " +
                                (e.get_attribute("content-desc") or "")
                            ).lower().strip()

                            if search_text in combined_text:
                                el = e
                                break
                        except:
                            continue
                except:
                    pass

            # -----------------------------
            # 3️⃣ CLICK IF FOUND
            # -----------------------------
            if el:
                try:
                    el.click()
                    sleep(0.8)

                    # 📸 Capture success reference
                    capture_screenshot(Ref_Img_Path)
                    img = cv2.imread(Ref_Img_Path, cv2.IMREAD_GRAYSCALE)

                    save_path = os.path.join(
                        Screenshot_path,
                        "Click_Operation_Ref_Screenshot.png"
                    )
                    cv2.imwrite(save_path, img)

                    Common_Ref_Img_Path = save_path
                    return f"Ok# Clicked on '{raw_text.strip()}'"

                except Exception as click_err:
                    safe_print(f"[CLICK FAILED] {click_err}")

            sleep(0.5)

        # -----------------------------
        # ❌ FINAL FAILURE → Screenshot
        # -----------------------------
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = os.path.join(Screenshot_path, f"NotFound_{timestamp}.png")

        capture_screenshot(temp_path)
        img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        cv2.imwrite(temp_path, img)

        return f"Not Ok# '{raw_text.strip()}' not found + {temp_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"Not ok# Click_By_Text failed: {str(e)}"

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
        # Parse inputs
        parts = path.split(",", 1)
        if len(parts) != 2:
            return "Not ok: Input format must be 'image_path,timeout'"

        img_path = parts[0].strip()
        timeout = float(parts[1].strip())
        file_name = os.path.basename(img_path).strip()
        
        p = Path(img_path)

        if app_evpv == 1:
            img_path = str(p.with_name("EV_" + p.name))

        if not os.path.exists(img_path):
            return f"Not ok: Reference image not found: {img_path}"

        if not init_driver():
            return "Not ok: Appium driver not initialized"

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

            sleep(check_interval)

    except Exception as e:
        try:
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
        except Exception:
            pass
        return f"Not ok: Click_By_Image failed for '{path}': {str(e)}"

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
def Click_By_Image_new(path, threshold=0.86, check_interval=0.03, debug=False):
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

    except Exception as e:
        return f"Not{str(e)}"

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

###########################################################  Compare Operation ######################################

def Compare_Screen_By_Text(input_text, base_dir=Screenshot_path):
    """
    Take screenshot, extract text via OCR, and check if a given text is present.
    """
    try:
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

        return f"Not Ok# Text '{search_str}' not found.+{screenshot_path}"

    except Exception as e:
        return f"Not ok: {str(e)}"

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

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"Not ok: Compare_Screen_By_Image failed: {str(e)}"




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

    except Exception as e:
        if os.path.exists(file_to_watch): 
            try: os.remove(file_to_watch)
            except: pass
        err_msg = f"Not ok#[ERROR] Scroll_and_Click_Text failed: {e}\n{traceback.format_exc()}"
        safe_print(err_msg)
        return err_msg

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

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"Not ok: Scroll_and_Click_Image failed: {str(e)}"

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

def Click_By_Coordinates(coord_string):
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

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"Not ok: Click_By_Coordinate failed: {str(e)}"

def Click_By_Coordinates_new(coord_string):
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

    except Exception as e:
        # Absolute safety net
        try:
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
        except:
            pass
        return f"ERROR# Click_By_Coordinates failed: {str(e)}"
    
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
    
def Click_Date_Time_By_Index_Text(input):
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

    except Exception as e:
        try:
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
        except:
            pass
        return f"ERROR# Click_Date_Time_By_Index failed: {str(e)}"


# init_driver()
# print(Click_Date_Time_By_Index_Text("0,10"))
# init_driver()
# print(Click_By_Coordinates("540_897,10"))
# init_driver()
# print(Click_By_Coordinates("854_219,10"))

def Click_Dynamically_By_Index_Text(coord_string):
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
        return f"Not ok: Click_By_Coordinate failed: {str(e)}"

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


def Send_Inputs(text):
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
        return f"Not Ok# Input field not found+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"Not ok: Send_Inputs failed: {str(e)}"
    
    
# init_driver()
# Send_Inputs("Mobile number:2580,10")

# init_driver()
# for i in range(30):
#     Swipe_From_Right_Edge("dummy")
#     Send_Inputs("Mobile number:2580,10")

########################################### Swipe Operation ##############################################

def Swipe_From_Left_Edge(text):
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

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"Not ok: Swipe_From_Left_Edge failed: {str(e)}"



def Swipe_From_Right_Edge(text):
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

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            
        return f"Not ok:Swipe from right edge failed: {str(e)}"

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
        return "Ok#Swiped up"

    except Exception as e:
        return f"Not ok#{str(e)}"


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

def Compare_Screen_By_Multiple_Texts(input_text, scroll_distance=100):
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
        return f"Not ok#{str(e)}"

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

    except Exception as e:
        print(f"Error: {e}")
        return f"Not ok#ERROR:{e}"


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
       

        return output

    except Exception as e:
        print(f"Not ok#Error: {e}")
        driver.back()
        return f"Not ok#ERROR:{e}"

def Check_Remote_Command_Status(input_str,interval=0.2):
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

    except Exception as e:
        return f"Not ok#{str(e)}"

# Common_Ref_Img_Path="C:\\Users\\TML PCV TCU HIL PXI\\Documents\\Ref_Screenshot.png"
def ocr_to_single_line(text):
    # remove newlines, tabs
    text = text.replace("\n", " ").replace("\t", " ")

    # remove extra spaces
    text = re.sub(r"\s+", " ", text)

    # strip junk dots / stray characters
    text = re.sub(r"[•·]", "", text)

    return text.strip()

def Check_Display_Message_Text(input_str,interval=0.2):
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
        text=clean_text
        print(param1)
        print(text)
        
        print(f"OCR: {text} \n")
        # If successful, save a copy
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if param1 in text in text and Param == "received":
            screenshot_path = os.path.join(Screenshot_path, f"success_{timestamp}.png")
            cv2.imwrite(screenshot_path, image)
            return f"Ok# Remote command executed successfully.+{screenshot_path}"
        else:
            screenshot_path = os.path.join(Screenshot_path, f"fail_{timestamp}.png")
            cv2.imwrite(screenshot_path, image)
            return f"Not ok# Remote command not executed successfully.+{screenshot_path}"

    except Exception as e:
        return f"Not ok#{str(e)}"

def Check_Mode_Exe_Status_Text(input_str,interval=0.2):
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

    except Exception as e:
        return f"Not ok#{str(e)}"

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

    except Exception as e:
        exec_time = (time.perf_counter() - start_time) * 1000  # ms
        return f"Not ok#Long_Press_Indirect_By_Image failed: {str(e)} | ExecTime={exec_time:.2f}ms"



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

def Wait_Until_Text_Disappears(text_to_watch):
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
        save_path = f"New_Ref_Screenshot.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)
        Common_Ref_Img_Path=full_path
        print(Common_Ref_Img_Path)
        
        return "Ok# Screen got changed"
    except Exception:
        # Take screenshot directly
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_path = os.path.join(
            Screenshot_path, f"screenshot_{timestamp}.png"
        )
        driver.get_screenshot_as_file(full_path)
        return f"Not Ok# Text '{param1}' still present after {timeout} sec+{full_path}"
    
    
def Wait_Until_Image_Disappears(input):
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

    except Exception as e:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_path = os.path.join(
            Screenshot_path, f"error_{timestamp}.png"
        )
        driver.get_screenshot_as_file(full_path)

        return f"Not Ok# Exception occurred: {str(e)}+{full_path}"
    
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
    save_path = f"Ref_Screenshot.png"
    full_path = os.path.join(Screenshot_path, save_path)
    # Save the image
    cv2.imwrite(full_path, curr_img)
    return f"{param1}+{full_path}"

def Check_ODO_Status_Text(input):
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

    except Exception as e:
        return f"Not ok#ODO validation failed due to {str(e)}"

# init_driver()
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
def Click_By_Image_Fast(input_str, threshold=0.86, check_interval=0.2):
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

    except Exception as e:
        return f"Not Ok# ERROR: {str(e)}"
    
def Set_Speed_Limit_Using_Text(input):
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

        while time.time() < end_time:
            current = get_current_value()

            if current is None:
                sleep(0.1)
                continue

            print(f"Current Speed Limit: {current}")

            if current == target:
                return f"Ok#Speed limit set to {current} km/h"

            if current < target:
                # driver.find_element(
                #     AppiumBy.XPATH,
                #     "//android.widget.Button[@text='+']"
                # ).click()
                if app_evpv == 0:
                    print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Plus.png,10"))
                else:
                    print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\EV_Plus.png,10"))
            else:
                # driver.find_element(
                #     AppiumBy.XPATH,
                #     "//android.widget.Button[@text='-']"
                # ).click()
                if app_evpv == 0:
                    print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Minus.png,10"))
                else:
                    print(Click_By_Image_Fast("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\EV_Minus.png,10"))

            sleep(0.2)  # allow UI to update

        return f"Not ok#Timeout reached. Last value: {get_current_value()}"

    except Exception as e:
        return f"Not ok#Failed to set speed limit: {str(e)}"