from appium import webdriver
from selenium.webdriver.common.by import By
import cv2
import numpy as np
import base64
import traceback, os
from time import sleep, time
from datetime import datetime, timedelta
from appium.webdriver.common.appiumby import AppiumBy
from skimage.metrics import structural_similarity as ssim
import subprocess
import threading
import re
from datetime import datetime
import xml.etree.ElementTree as ET
import sys
import json
#from appium.webdriver.common.touch_action import TouchAction
from PIL import Image
import os
import subprocess
import re
import time
import traceback
from selenium.common.exceptions import WebDriverException
import datetime
import requests
import pytesseract
from pathlib import Path
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from datetime import datetime
temp_path = "C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\temp_img.png"
#temp_path = "D:\\Sourcecode 17_09_25\\Sourcecode\\Configuration_Files\\Appium\\Temp Screenshot\\temp_img.png"


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

# # def file_watcher(file_path, check_interval=1):
# #     """Continuously checks for file. If found → aborts script."""
# #     while True:
# #         if os.path.exists(file_path):
# #             os.remove(file_path)
# #             print(f"[ABORT] File detected: {file_path}. Stopping script...")
# #             os._exit(0)  # terminate this Python script immediately
# #         time.sleep(check_interval)

# # Example usage:
file_to_watch_t = PROJECT_ROOT /  "Appium" / "Watcher" / "Watcher.txt"
file_to_watch = str(file_to_watch_t).replace("\\", "\\\\")
print(file_to_watch)

if os.path.exists(file_to_watch):
    os.remove(file_to_watch)

# # # Start watcher in background thread
# watcher_thread = threading.Thread(
#     target=file_watcher, 
#     args=(file_to_watch,), 
#     daemon=True
# )
# watcher_thread.start()



####################################################### Initialization function #############################################################
def keep_driver_alive():
    global driver
    while True:
        try:
            if driver:
                driver.current_activity  # dummy ping
        except:
            pass
        time.sleep(30)  # ping every 30 seconds

# Call this once after initializing the driver
def start_keep_alive():
    t = threading.Thread(target=keep_driver_alive, daemon=True)
    t.start()

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
    try:
        result = subprocess.run(
            ["adb", "shell", "dumpsys", "activity", "activities"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output = result.stdout

        # Look for the top (foreground) activity
        if f"ResumedActivity: ActivityRecord" in output and package_name in output:
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
        time.sleep(1)

        # Swipe up to unlock
        subprocess.run(["adb", "shell", "input", "swipe", "300", "1000", "300", "500"], check=True)
        time.sleep(1)

        if is_device_unlocked():
            print('')
        else:
            subprocess.run(["adb", "shell", "input", "text", pin_code], check=True)
            time.sleep(0.5)

        # Press Enter
        subprocess.run(["adb", "shell", "input", "keyevent", "66"], check=True)
        time.sleep(2)

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

# def get_foreground_app():
#     try:
#         result = subprocess.check_output(
#             ["adb", "shell", "dumpsys", "activity", "activities"],
#             encoding="utf-8"
#         )
#         for line in result.splitlines():
#             if "mResumedActivity" in line:
#                 return line.strip()
#         return None
#     except subprocess.CalledProcessError as e:
#         print(f"Error fetching foreground activity: {e}")
#         return None

def get_foreground_app():
    """
    Get the currently foregrounded app on a specific device.
    """
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
        print(f"Error fetching foreground activity on device {device_id}: {e}")
        return None

# def bring_app_to_foreground(package_name):
#     try:
#         subprocess.run([
#             "adb", "shell", "monkey", "-p", package_name,
#             "-c", "android.intent.category.LAUNCHER", "1"
#         ], check=True)
#         print(f"{package_name} brought to foreground.")
#     except subprocess.CalledProcessError as e:
#         print(f"Failed to bring {package_name} to foreground: {e}")

def bring_app_to_foreground(package_name):
    """
    Bring the app to the foreground on a specific device UDID.
    """
    try:
        subprocess.run([
            "adb", "-s", device_id, "shell", "monkey", "-p", package_name,
            "-c", "android.intent.category.LAUNCHER", "1"
        ], check=True)
        print(f"{package_name} brought to foreground on device {device_id}.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to bring {package_name} to foreground on device {device_id}: {e}")

# def launch_app(package_name):
#     try:
#         subprocess.run([
#             "adb", "shell", "monkey", "-p", package_name,
#             "-c", "android.intent.category.LAUNCHER", "1"
#         ], check=True)
#         print(f"App '{package_name}' launched successfully.")
#     except subprocess.CalledProcessError as e:
#         print(f"Failed to launch app '{package_name}': {e}")

def launch_app(package_name):
    """
    Launch the app on a specific device identified by its UDID.
    """
    try:
        subprocess.run([
            "adb", "-s", device_id, "shell", "monkey", "-p", package_name,
            "-c", "android.intent.category.LAUNCHER", "1"
        ], check=True)
        print(f"App '{package_name}' launched successfully on device {device_id}.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to launch app '{package_name}' on device {device_id}: {e}")

def ensure_app_in_foreground(package_name):
    if not is_app_running(package_name):
        print("App is not running. Launching it...")
        launch_app(package_name)
        return 

    fg_line = get_foreground_app(device_id)  # ✅ pass device_id
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
        response = requests.get(url, timeout=2)
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
        time.sleep(3)
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

                                                                    ############## Init Main #############
# def init_driver(variable_str="", timeout=10):
#     global driver
#     try:
#         # If driver exists, check session
#         if driver is not None:
#             try:
#                 driver.current_activity  # Throws if session is dead
#                 return "PASS: Driver already initialized"
#             except:
#                 try:
#                     driver.quit()
#                 except:
#                     pass
#                 driver = None

#         # Read capabilities
#         with open(Capability_path, "r") as file:
#             caps = json.load(file)
        
#         print(caps)

#         # Start Appium session
#         driver = webdriver.Remote("http://localhost:4723", caps)
#         time.sleep(2)
#         start_keep_alive()
#         safe_print("[INIT] Appium driver initialized")
#         app_package = caps["appPackage"]
#         device_id = ["udid"]
#         # Launch WhatsApp using ADB monkey command

#         ensure_app_in_foreground(app_package)

#         return "PASS: Driver initialized"

#     except Exception as e:
#         err = f"ERROR: Failed to initialize Appium driver: {str(e)}"
#         safe_print(err)
#         safe_print(traceback.format_exc())
#         return err

def init_driver(variable_str="", timeout=10):
    global driver, device_id   # <— add device_id global
    try:
        if driver is not None:
            try:
                driver.current_activity
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

        # Save device_id globally
        device_id = caps.get("udid")
        if not device_id:
            return "ERROR: No UDID found in Capabilities.json"

        driver = webdriver.Remote("http://localhost:4723", caps)
        time.sleep(2)
        start_keep_alive()
        safe_print("[INIT] Appium driver initialized")

        app_package = caps.get("appPackage")
        if not app_package:
            return "ERROR: appPackage missing in Capabilities.json"

        ensure_app_in_foreground(app_package)

        return "PASS: Driver initialized"

    except Exception as e:
        err = f"ERROR: Failed to initialize Appium driver: {str(e)}"
        safe_print(err)
        safe_print(traceback.format_exc())
        return err

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
        driver.save_screenshot(output_path)
        if not os.path.exists(output_path):
            return "error:screenshot_not_created"
        return "ok"
    except Exception as e:
        return f"error:capture_failed:{str(e)}"

################################################### Check notification ##########################################################
# def Check_Notification(text):
#     try:
#         param1, param2 = text.split(",", 1)
#         timeout = int(param2)
        
#         driver.open_notifications()
#         sleep(timeout)
#         driver.press_keycode(4)
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
        
#         return "Ok"
    
#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return "Not ok"

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

        return "Ok# Notification panel opened"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: {str(e)}\n"




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


# def check_image_exists(path, threshold=0.8):
#     try:
        
#         threshold = float(threshold)

#         if not init_driver():
#             return "[ERROR] Driver not initialized"

#         template = load_reference_image(path)
#         screenshot = take_screenshot(driver)

#         # Debug: Save images
#         cv2.imwrite("C:/temp/screenshot.png", screenshot)
#         cv2.imwrite("C:/temp/template.png", template)

#         pos = find_template_in_screenshot(screenshot, template, threshold)
#         msg = f"[CHECK] {'Ok' if pos else 'Not ok'}: {path}"
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         safe_print(msg)
#         return msg

#     except Exception as e:
#         err = f"[ERROR] check_image_exists failed: {e}\n{traceback.format_exc()}"
#         safe_print(err)
#         return err


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
#     try:
#         import time
#         from time import sleep
#         import traceback
#         from selenium.webdriver.common.by import By

#         param1, param2 = visible_text.split(",", 1)
#         visible_text = str(param1)
#         timeout = float(param2)
#         check_interval = float(check_interval)

#         if not init_driver():
#             return "[ERROR] Driver not initialized"

#         start_time = time.time()
#         while time.time() - start_time < timeout:
#             try:
#                 element = driver.find_element(By.XPATH, f"//*[@text='{visible_text}']")
#                 if element:
#                     return "Ok"
#             except:
#                 pass
#             sleep(check_interval)
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break

#         return "Not Ok"
#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"[ERROR] {str(e)}\n{traceback.format_exc()}"

# def Wait_Until_Text_Appears(visible_text, check_interval=2):
#     """
#     Wait until the specified text appears on the screen.

#     Args:
#         visible_text (str): "text_to_find,timeout"
#         check_interval (int|float): Interval between checks (default 2s)

#     Returns:
#         str: "Ok# Text '<text>' appeared"
#              "Not Ok# Text '<text>' not found within timeout"
#              "ERROR: <exception details>"
#     """
#     try:
#         import time
#         from time import sleep
#         from selenium.webdriver.common.by import By

#         param1, param2 = visible_text.split(",", 1)
#         visible_text = str(param1)
#         timeout = float(param2)
#         check_interval = float(check_interval)

#         if not init_driver():
#             return "ERROR: Driver not initialized"

#         start_time = time.time()
#         while time.time() - start_time < timeout:
#             try:
#                 element = driver.find_element(By.XPATH, f"//*[@text='{visible_text}']")
#                 if element:
#                     if os.path.exists(file_to_watch):
#                         os.remove(file_to_watch)
#                     return f"Ok# Text '{visible_text}' appeared"
#             except:
#                 pass

#             sleep(check_interval)

#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Not Ok# Aborted by abort signal"

#         return f"Not Ok# Text '{visible_text}' not found"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Wait_Until_Text_Appears failed: {str(e)}"


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os

def Wait_Until_Text_Appears(visible_text, check_interval=2):
    """
    Wait until the specified text appears on the screen.

    Args:
        visible_text (str): "text_to_find,timeout"
        check_interval (int|float): Polling interval in seconds (default 2s)

    Returns:
        str: "Ok# Text '<text>' appeared"
             "Not Ok# Aborted by abort signal"
             "Not Ok# Text '<text>' not found within timeout"
             "ERROR: <exception details>"
    """
    try:
        # Parse input
        param1, param2 = visible_text.split(",", 1)
        search_str = param1.strip()
        timeout = float(param2)         # <-- your timeout is used here
        check_interval = float(check_interval)

        if not init_driver():
            return "ERROR: Driver not initialized"

        wait = WebDriverWait(driver, timeout, poll_frequency=check_interval)

        def condition(drv):
            # Abort signal check
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                raise TimeoutException("ABORT")  # immediate stop

            try:
                element = drv.find_element(By.XPATH, f"//*[@text='{search_str}']")
                return element if element else False
            except NoSuchElementException:
                return False

        try:
            element = wait.until(condition)
            return f"Ok# Text '{search_str}' appeared"
        except TimeoutException as e:
            if "ABORT" in str(e):
                return "Not Ok# Aborted by abort signal"
            
             
            capture_screenshot(temp_path)
            curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"screenshot_{timestamp}.png"
            full_path = os.path.join(Screenshot_path, save_path)
            # Save the image
            cv2.imwrite(full_path, curr_img)
            return f"Not Ok# Text '{search_str}' not found+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Wait_Until_Text_Appears failed: {str(e)}"


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
    


# # Main function
# def Wait_Until_Image_Appears(path_with_timeout, threshold=0.8, check_interval=2):
#     try:
#         safe_print(f"[INPUT] path_with_timeout: {path_with_timeout}, threshold: {threshold}, check_interval: {check_interval}")

#         parts = path_with_timeout.split(",", 1)
#         if len(parts) != 2:
#             return "[ERROR] Input format must be 'path,timeout'"

#         path = parts[0].strip()
#         timeout = float(parts[1].strip())
#         threshold = float(threshold)
#         check_interval = float(check_interval)

#         if not init_driver():
#             return "[ERROR] Driver not initialized"

#         safe_print(f"[WAIT] Waiting for image: {path} (timeout: {timeout}s)")
#         start_time = time.time()

#         while time.time() - start_time < timeout:
#             try:
#                 result = check_image_exists(path, threshold)
#                 safe_print(f"[CHECK] Image check result: {result}")

#                 if isinstance(result, str) and "FOUND" in result:
#                     safe_print(f"[FOUND] Image appeared: {path}")
#                     return "Ok"
#             except Exception as inner:
#                 safe_print(f"[LOOP ERROR] {inner}")
            
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break

#             sleep(check_interval)


#         safe_print(f"[TIMEOUT] Image not found within {timeout}s: {path}")
#         return "Not ok"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         err = f"[ERROR] wait_until_image_appears failed: {e}\n{traceback.format_exc()}"
#         safe_print(err)
#         return f"[ERROR] {str(e)}"



# def Wait_Until_Image_Appears(path_with_timeout, threshold=0.8, check_interval=2):
#     """
#     Wait until the specified image appears on the screen.

#     Args:
#         path_with_timeout (str): "path,timeout"
#         threshold (float): Matching threshold (default 0.8)
#         check_interval (int|float): Interval between checks (default 2s)

#     Returns:
#         str: "Ok# Image '<path>' appeared"
#              "Not Ok# Image '<path>' not found within timeout"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <exception details>"
#     """
#     try:
#         parts = path_with_timeout.split(",", 1)
#         if len(parts) != 2:
#             return "ERROR: Input format must be 'path,timeout'"

#         path = parts[0].strip()
#         timeout = float(parts[1].strip())
#         threshold = float(threshold)
#         check_interval = float(check_interval)

#         if not init_driver():
#             return "ERROR: Driver not initialized"

#         start_time = time.time()
#         while time.time() - start_time < timeout:
#             try:
#                 result = check_image_exists(path, threshold)

#                 if isinstance(result, str) and "Ok" in result:
#                     if os.path.exists(file_to_watch):
#                         os.remove(file_to_watch)
#                     return f"Ok# Image '{path}' appeared"
#             except Exception as inner:
#                 safe_print(f"[LOOP ERROR] {inner}")

#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Not Ok# Aborted by abort signal"

#             sleep(check_interval)

#         return f"Not Ok# Image '{path}' not found"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Wait_Until_Image_Appears failed: {str(e)}"



def Wait_Until_Image_Appears(path_with_timeout, threshold=0.8, check_interval=2):
    """
    Wait until the specified image appears on the screen.

    Args:
        path_with_timeout (str): "path,timeout"
        threshold (float): Matching threshold (default 0.8)
        check_interval (int|float): Polling interval (default 2s)

    Returns:
        str: "Ok# Image '<path>' appeared"
             "Not Ok# Image '<path>' not found within timeout"
             "Not Ok# Aborted by abort signal"
             "ERROR: <exception details>"
    """
    try:
        # Parse input
        parts = path_with_timeout.split(",", 1)
        if len(parts) != 2:
            return "ERROR: Input format must be 'path,timeout'"

        path = parts[0].strip()
        timeout = float(parts[1].strip())
        threshold = float(threshold)
        check_interval = float(check_interval)

        if not init_driver():
            return "ERROR: Driver not initialized"

        wait = WebDriverWait(driver, timeout, poll_frequency=check_interval)

        def condition(_):
            # Abort signal check
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                raise TimeoutException("ABORT")

            try:
                result = check_image_exists(path, threshold)
                if isinstance(result, str) and "Ok" in result:
                    return True
            except Exception as inner:
                safe_print(f"[LOOP ERROR] {inner}")
            return False

        try:
            wait.until(condition)
            return f"Ok# Image '{path}' appeared"
        except TimeoutException as e:
            if "ABORT" in str(e):
                return "Not Ok# Aborted by abort signal"
             
            capture_screenshot(temp_path)
            curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"screenshot_{timestamp}.png"
            full_path = os.path.join(Screenshot_path, save_path)
            # Save the image
            cv2.imwrite(full_path, curr_img)
            return f"Not Ok# Image '{path}' not found+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Wait_Until_Image_Appears failed: {str(e)}"



# init_driver()
# print(Wait_Until_Image_Appears("C:\\Users\\panch\\Downloads\\2.png,10"))
######################################################## Working Click by Text LABVIEW ###############################################

# def Click_By_Text(visible_text):
#     try:
#         param1, param2 = visible_text.split(",", 1)
#         visible_text = str(param1)  # ensure type safety
#         timeout = int(param2)
#         #driver.implicitly_wait(timeout)
#         for _ in range(int(timeout)):
#             time.sleep(1)
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break

#         el = driver.find_element(By.XPATH, f"//*[@text='{visible_text}']")
#         el.click()
#         print("Ok")
#         #return f"[CLICK] Clicked on: {visible_text}"
#         return "Ok"
#     except Exception as e:
#         print( f"[ERROR] Failed to click on '{visible_text}': {e}")
#         return "Not ok"





# def Click_By_Text(visible_text):
#     try:
#         param1, param2 = visible_text.split(",", 1)
#         visible_text = str(param1).strip()   # text to search
#         timeout = int(param2)                # timeout in seconds

#         # Loop wait (like implicit wait)
#         for _ in range(timeout):
#             # ✅ Abort check
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break

#             try:
#                 el = driver.find_element(By.XPATH, f"//*[@text='{visible_text}']")
#                 if el:   # Found element
#                     el.click()
#                     return "Ok"
#             except NoSuchElementException:
#                 pass  # keep waiting if not found

#             time.sleep(1)

#         # Timeout reached, element not found
#         return "Not ok"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         print(f"[ERROR] Failed to click on '{visible_text}': {e}")
#         return "Not ok"


# def Click_By_Text(visible_text):
#     """
#     Click on a UI element by its visible text.

#     Args:
#         visible_text (str): "text_to_click,timeout"

#     Returns:
#         str: "Ok# Clicked on '<text>'"
#              "Not Ok# '<text>' not found within timeout"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <details>"
#     """
#     try:
#         param1, param2 = visible_text.split(",", 1)
#         visible_text = str(param1).strip()   # text to search
#         timeout = int(param2)                # timeout in seconds

#         # Loop wait (like implicit wait)
#         for _ in range(timeout):
#             # ✅ Abort check
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Not Ok# Aborted by abort signal"

#             try:
#                 el = driver.find_element(By.XPATH, f"//*[@text='{visible_text}']")
#                 if el:   # Found element
#                     el.click()
#                     return f"Ok# Clicked on '{visible_text}'"
#             except NoSuchElementException:
#                 pass  # keep waiting if not found

#             time.sleep(1)

#         # Timeout reached, element not found
#         return f"Not Ok# '{visible_text}' not found"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Failed to click on '{visible_text}': {str(e)}"
    





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

            time.sleep(0.5)
        
         
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
        return f"ERROR: Failed to click on '{visible_text}': {str(e)}"








from selenium.common.exceptions import NoSuchElementException
# def Compare_Screen_By_Text(visible_text):
#     try:
#         param1, param2 = visible_text.split(",", 1)
#         visible_text = str(param1).strip()  # ensure type safety
#         timeout = int(param2)
#         #driver.implicitly_wait(timeout)

#         for _ in range(int(timeout)):
#             time.sleep(1)
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break

#         driver.find_element(By.XPATH, f"//*[@text='{visible_text}']")
#         # If element is found, return True
#         return "Ok"
#     except NoSuchElementException:
#         return "Not ok"
#     except Exception as e:
#         print(f"[ERROR] Failed to check text '{visible_text}': {e}")
#         return "Not ok"

# def Compare_Screen_By_Text(visible_text):
#     try:
#         #os.remove(file_to_watch)

#         param1, param2 = visible_text.split(",", 1)
#         visible_text = str(param1).strip()   # text to search
#         timeout = int(param2)                # timeout in seconds
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         # Explicit loop wait (acts like implicit wait)
#         for _ in range(timeout):
#             # ✅ Abort check
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Abort"

#             try:
#                 task = driver.find_element(By.XPATH, f"//*[@text='{visible_text}']")
#                 if task:   # Found element
#                     return "Ok"
#             except NoSuchElementException:
#                 pass  # keep waiting

#             time.sleep(1)
        
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         # Timeout reached, element not found
#         return "Not ok"

#     except Exception as e:
#         print(f"[ERROR] Failed to check text '{visible_text}': {e}")
#         os.remove(file_to_watch)
#         return "Not ok"


# def Compare_Screen_By_Text(visible_text):
#     """
#     Check if a given text is present on the current screen.

#     Args:
#         visible_text (str): "text_to_find,timeout"

#     Returns:
#         str: "Ok# Text '<text>' is present on screen"
#              "Not Ok# Text '<text>' not found within timeout"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <details>"
#     """
#     try:
#         param1, param2 = visible_text.split(",", 1)
#         visible_text = str(param1).strip()   # text to search
#         timeout = int(param2)                # timeout in seconds
#         print("#######################################")
#         print(param2)

#         # Clear abort file if it exists at start
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         # Explicit loop wait
#         for _ in range(timeout):
#             # Abort check
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Not Ok# Aborted by abort signal"

#             try:
#                 task = driver.find_element(By.XPATH, f"//*[@text='{visible_text}']")
#                 if task:   # Found element
#                     return f"Ok# Text '{visible_text}' is present on screen"
#             except NoSuchElementException:
#                 pass  # keep waiting

#             time.sleep(1)

#         # Timeout reached, element not found
#         return f"Not Ok# Text '{visible_text}' not found"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Failed to check text '{visible_text}': {str(e)}"

# def Compare_Screen_By_Text(input_text, base_dir=Screenshot_path):
#     """
#     Take screenshot, extract text via OCR, and check if a given text is present.

#     Args:
#         input_text (str): "text_to_find,timeout"

#     Returns:
#         str: "Ok# Text '<text>' is present on screen"
#              "Not Ok# Text '<text>' not found within <timeout> sec"
#              "ERROR: <details>"
#     """
#     try:
#         # Split input into text and timeout
#         param1, param2 = input_text.split(",", 1)
#         search_str = param1.strip()
#         timeout = int(param2.strip())

#         # Create folder if not exists
#         if not os.path.exists(base_dir):
#             os.makedirs(base_dir)

#         # Wait before screenshot
#         time.sleep(timeout)
#         # Screenshot with timestamp
#         timestamp = time.strftime("%Y%m%d_%H%M%S")
#         screenshot_path = os.path.join(base_dir, f"screen_{timestamp}.png")
#         driver.save_screenshot(screenshot_path)

#         # OCR extraction
#         image = cv2.imread(screenshot_path)
#         text = pytesseract.image_to_string(image)

#         # Debug log
#         print("[OCR Extracted Text]:", text)

#         # Case-insensitive search
#         if search_str.lower() in text.lower():
#             return f"Ok# Text '{search_str}' is present on screen, Screenshot: {screenshot_path}"
#         else:
#             return f"Not Ok# Text '{search_str}' not found, Screenshot: {screenshot_path}"

#     except Exception as e:
#         return f"ERROR: {str(e)}"


# def Compare_Screen_By_Text(input_text, base_dir=Screenshot_path):
#     """
#     Take screenshot, extract text via OCR, and check if a given text is present.

#     Args:
#         input_text (str): "text_to_find,timeout"

#     Returns:
#         str: "Ok# Text '<text>' is present on screen"
#              "Not Ok# Text '<text>' not found within <timeout> sec"
#              "ERROR: <details>"
#     """
#     try:
#         # Split input into text and timeout
#         param1, param2 = input_text.split(",", 1)
#         search_str = param1.strip()
#         timeout = int(param2.strip())

#         # Create folder if not exists
#         if not os.path.exists(base_dir):
#             os.makedirs(base_dir)

#         start_time = time.time()

#         while time.time() - start_time < timeout:
#             # Screenshot with timestamp
#             timestamp = time.strftime("%Y%m%d_%H%M%S")
#             screenshot_path = os.path.join(base_dir, f"screen_{timestamp}.png")
#             driver.save_screenshot(screenshot_path)

#             # OCR extraction
#             image = cv2.imread(screenshot_path)
#             text = pytesseract.image_to_string(image)

#             # Debug log
#             print("[OCR Extracted Text]:", text)

#             # Case-insensitive search
#             if search_str.lower() in text.lower():
#                 return f"Ok# Text '{search_str}' is present on screen, Screenshot: {screenshot_path}"

#             # Small delay before next attempt
#             time.sleep(1)

#         # Timeout reached
#         return f"Not Ok# Text '{search_str}' not found, Screenshot: {screenshot_path}"

#     except Exception as e:
#         return f"ERROR: {str(e)}"

# init_driver()
# print(Compare_Screen_By_Text("Allow Tata Motors IRA 2.0,20"))



def Compare_Screen_By_Text(input_text, base_dir=Screenshot_path):
    """
    Take screenshot, extract text via OCR, and check if a given text is present.

    Args:
        input_text (str): "text_to_find,timeout"

    Returns:
        str: "Ok# Text '<text>' is present on screen, Screenshot: <path>"
             "Not Ok# Text '<text>' not found within <timeout> sec, Screenshot: <path>"
             "ERROR: <details>"
    """
    try:
        # Split input into text and timeout
        param1, param2 = input_text.split(",", 1)
        search_str = param1.strip()
        timeout = int(param2.strip())

        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        start_time = time.time()
        screenshot_path = None

        while time.time() - start_time < timeout:
            # Screenshot captured in memory
            png = driver.get_screenshot_as_png()
            np_img = np.frombuffer(png, np.uint8)
            image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

            # Optional preprocessing
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Correct pytesseract call
            custom_config = r'--oem 3 --psm 6'   # Configuration options go in 'config', NOT 'lang'
            text = pytesseract.image_to_string(thresh, config=custom_config, lang='eng')  # lang='eng' is correct

            # Debug log
            print("[OCR Extracted Text]:", text)

            # Case-insensitive search
            if search_str.lower() in text.lower():
                # Save only when found
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(base_dir, f"screen_found_{timestamp}.png")
                with open(screenshot_path, "wb") as f:
                    f.write(png)
                return f"Ok# Text '{search_str}' is present on screen.+{screenshot_path}"

            time.sleep(0.5)  # small wait before next check

        # Timeout reached → save last screenshot for evidence
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(base_dir, f"screen_timeout_{timestamp}.png")
        driver.save_screenshot(screenshot_path)

        return f"Not Ok# Text '{search_str}' not found.+{screenshot_path}"

    except Exception as e:
        return f"ERROR: {str(e)}"




# init_driver()
# print(Compare_Screen_By_Text("Sierra,20"))



##################################################### Working Click by Image LABVIEW #########################################################


                                                          ################# Main ##################

# def Click_By_Image(path, threshold=0.8):
#     try:
#         # Type conversion for LabVIEW input
#         param1, param2 = path.split(",", 1)
#         path = str(param1)
#         threshold = float(threshold)
#         timeout=int(param2)
#         for _ in range(timeout):
#             time.sleep(1)


#         # Ensure driver is ready
#         if not init_driver():
#             return "[ERROR] Appium driver not initialized"

#         template = load_reference_image(path)
#         screenshot = take_screenshot(driver)
#         pos = find_template_in_screenshot(screenshot, template, threshold)

#         if pos:
#             driver.execute_script("mobile: clickGesture", {"x": pos[0], "y": pos[1]})
#             msg = f"[CLICK] Clicked on image at: {pos}, file: {path}"
#             safe_print(msg)
#             #return msg
#             return "Ok"

#         msg = f"[NOT FOUND] No match for image: {path}"
#         safe_print(msg)
#         #return msg
#         return "Not ok"

#     except Exception as e:
#         err = f"[ERROR] Exception in click_image: {str(e)}\n{traceback.format_exc()}"
#         safe_print(err)
#         return err


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
#         param1, param2 = path.split(",", 1)
#         path = str(param1).strip()
#         threshold = float(threshold)
#         timeout = int(param2)

#         # Ensure driver is ready
#         if not init_driver():
#             return "ERROR: Appium driver not initialized"

#         for _ in range(timeout):
#             # ✅ Abort check
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return "Not Ok# Aborted by abort signal"

#             screenshot = take_screenshot(driver)
#             template = load_reference_image(path)
#             pos = find_template_in_screenshot(screenshot, template, threshold)

#             if pos:
#                 driver.execute_script("mobile: clickGesture", {"x": pos[0], "y": pos[1]})
#                 return f"Ok# Clicked on image '{path}' at {pos}"

#             time.sleep(1)

#         # Timeout reached
#         return f"Not Ok# Image '{path}' not found"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Click_By_Image failed for '{path}': {str(e)}"






def Click_By_Image(path, threshold=0.8):
    """
    Click on a UI element by matching an image on the screen.

    Args:
        path (str): "image_path,timeout"
        threshold (float): Matching threshold (default 0.8)

    Returns:
        str: "Ok# Clicked on image '<path>' at (x,y)"
             "Not Ok# Image '<path>' not found within timeout"
             "Not Ok# Aborted by abort signal"
             "ERROR: <details>"
    """
    try:
        # Extract params
        parts = path.split(",", 1)
        if len(parts) != 2:
            return "ERROR: Input format must be 'image_path,timeout'"

        img_path = parts[0].strip()
        timeout = int(parts[1].strip())
        threshold = float(threshold)

        # Ensure driver is ready
        if not init_driver():
            return "ERROR: Appium driver not initialized"

        start_time = time.time()
        while time.time() - start_time < timeout:
            # ✅ Abort check
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                return "Not Ok# Aborted by abort signal"

            try:
                screenshot = take_screenshot(driver)
                template = load_reference_image(img_path)
                pos = find_template_in_screenshot(screenshot, template, threshold)

                if pos:
                    driver.execute_script("mobile: clickGesture", {"x": pos[0], "y": pos[1]})
                    return f"Ok# Clicked on image '{img_path}' at {pos}"

            except Exception as inner:
                safe_print(f"[LOOP ERROR] {inner}")

            time.sleep(1)
        
         
        capture_screenshot(temp_path)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)
        
        filename = os.path.basename(img_path)

        # Timeout reached
        return f"Not Ok# Image '{filename}' not found.+ {full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Click_By_Image failed for '{path}': {str(e)}"


# init_driver()
# print(Click_By_Image("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\1.1.jpg,10"))





# init_driver()
# print(Click_By_Image("C:\\MaxEye\\MEP00179\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\Status.jpg,5"))
    

    

####################################################### Compare screen with reference image ####################################################################

# def capture_screenshot(output_path):
#     try:
#         driver.save_screenshot(output_path)
#         if not os.path.exists(output_path):
#             print("Screenshot file not created.")
#         else:
#             print(f"Screenshot saved at: {output_path}")
#         return True
#     except Exception as e:
#         print(f"error:capture_failed:{str(e)}")
#         return False

# def Compare_Screen_By_Image(input, threshold=0.97):
#     try:
#         param1, param2 = input.split(",", 1)
#         ref_path = param1.strip()

#         # Define where screenshot will be saved
#         curr_path = "D:\\temp.png"

#         if not capture_screenshot(curr_path):
#             return "error:screenshot_failed"

#         # Load images
#         ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
#         curr_img = cv2.imread(curr_path, cv2.IMREAD_GRAYSCALE)

#         if ref_img is None or curr_img is None:
#             return "error:invalid_image_path"

#         # Resize if needed
#         if ref_img.shape != curr_img.shape:
#             curr_img = cv2.resize(curr_img, (ref_img.shape[1], ref_img.shape[0]))

#         # Compare using SSIM
#         score, _ = ssim(ref_img, curr_img, full=True)
#         print("SSIM Score:", score)

#         return "Ok" if score >= threshold else "Not ok"

#     except Exception as e:
#         return f"error:{str(e)}"



# def Compare_Screen_By_Image(input, threshold=0.97):
#     try:
#         # Parse input
#         param1, param2 = input.split(",", 1)
#         ref_path = param1.strip()
#          

#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)

#         # Take screenshot
#         result = capture_screenshot(temp_path)
#         if "error" in result:
#             return result

#         # Load images
#         ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
#         curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)

#         if ref_img is None:
#             return f"error:ref_image_not_found:{ref_path}"
#         if curr_img is None:
#             return f"error:screenshot_image_not_found:{temp_path}"

#         # Resize if needed
#         if ref_img.shape != curr_img.shape:
#             curr_img = cv2.resize(curr_img, (ref_img.shape[1], ref_img.shape[0]))

#         # Compare using SSIM
#         score, _ = ssim(ref_img, curr_img, full=True)

#         if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
            

#         if score >= threshold:
#             return f"Ok"
#         else:
#             return f"Not ok"
        
        

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"error:exception:{str(e)}"



# def Compare_Screen_By_Image(input, threshold=0.97):
#     """
#     Compare the current screen with a reference image using SSIM.

#     Args:
#         input (str): "ref_image_path,timeout"
#         threshold (float): Similarity threshold (default 0.97)

#     Returns:
#         str: "Ok# Screen matches reference image"
#              "Not Ok# Screen does not match reference image"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <details>"
#     """
#     try:
#         # Parse input
#         param1, param2 = input.split(",", 1)
#         ref_path = param1.strip()
#         timeout = int(param2)
#          

#         # Ensure driver is initialized
#         if not init_driver():
#             return "ERROR: Driver not initialized"

#         # Take screenshot
#         result = capture_screenshot(temp_path)
#         if isinstance(result, str) and result.lower().startswith("error"):
#             return f"ERROR: Failed to capture screenshot -> {result}"

#         # Load images
#         ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
#         curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)

#         if ref_img is None:
#             return f"ERROR: Reference image not found at {ref_path}"
#         if curr_img is None:
#             return f"ERROR: Screenshot image not found at {temp_path}"

#         # Resize if dimensions differ
#         if ref_img.shape != curr_img.shape:
#             curr_img = cv2.resize(curr_img, (ref_img.shape[1], ref_img.shape[0]))

#         # Abort check
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#             return "Not Ok# Aborted by abort signal"

#         # Compare using SSIM
#         score, _ = ssim(ref_img, curr_img, full=True)

#         if score >= threshold:
#             return "Ok# Screen matches reference image"
#         else:
#             return "Not Ok# Screen does not match reference image"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Compare_Screen_By_Image failed: {str(e)}"



# def Compare_Screen_By_Image(input, threshold=0.90):
#     """
#     Check if a small reference image exists in the current screen using template matching.

#     Args:
#         input (str): "ref_image_path,timeout"
#         threshold (float): Match confidence threshold (0.90 recommended for template match)

#     Returns:
#         str: Result message
#     """
#     try:
#         import cv2
#         import os
#         import time

#         # Parse input
#         param1, param2 = input.split(",", 1)
#         ref_path = param1.strip()
#         timeout = int(param2)
#          

#         if not init_driver():
#             return "ERROR: Driver not initialized"

#         time.sleep(timeout)  # Give UI time to stabilize

#         result = capture_screenshot(temp_path)
#         if isinstance(result, str) and result.lower().startswith("error"):
#             return f"ERROR: Failed to capture screenshot -> {result}"

#         # Load images in grayscale
#         ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
#         curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)

#         if ref_img is None:
#             return f"ERROR: Reference image not found at {ref_path}"
#         if curr_img is None:
#             return f"ERROR: Screenshot image not found at {temp_path}"

#         # Check for abort signal
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#             return "Not Ok# Aborted by abort signal"

#         # Template Matching
#         result = cv2.matchTemplate(curr_img, ref_img, cv2.TM_CCOEFF_NORMED)
#         min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

#         print(f"DEBUG: Template match confidence = {max_val:.4f}")

#         if max_val >= threshold:
#             return "Ok# Reference image found on screen"
#         else:
#             return "Not Ok# Reference image NOT found on screen"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Compare_Screen_By_Image failed: {str(e)}"


def Compare_Screen_By_Image(input, threshold=0.90):
    """
    Check if a small reference image exists in the current screen using template matching.

    Args:
        input (str): "ref_image_path,timeout"
        threshold (float): Match confidence threshold (0.90 recommended for template match)

    Returns:
        str: Result message
    """
    try:
        import cv2
        import os
        import time

        # Parse input
        param1, param2 = input.split(",", 1)
        ref_path = param1.strip()
        timeout = int(param2)
         

        # Extract filename for custom logic
        filename = os.path.basename(ref_path).lower()

        if not init_driver():
            return "ERROR: Driver not initialized"

        time.sleep(timeout)  # Give UI time to stabilize

        result = capture_screenshot(temp_path)
        if isinstance(result, str) and result.lower().startswith("error"):
            return f"ERROR: Failed to capture screenshot -> {result}"

        # Load images in grayscale
        ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        # Get current timestamp and format it for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"  # e.g., screenshot_20250917_145230.png
        full_path = os.path.join(Screenshot_path, save_path)

        # Save the image
        cv2.imwrite(full_path, curr_img)

        if ref_img is None:
            return f"ERROR: Reference image not found"
        if curr_img is None:
            return f"ERROR: Screenshot image not found"

        # Check for abort signal
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return "Not Ok# Aborted by abort signal"

        # Template Matching
        result = cv2.matchTemplate(curr_img, ref_img, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        print(f"DEBUG: Template match confidence = {max_val:.4f}")

        # Custom logic for Connectivity.jpg
        if filename == "connectivity.jpg":
            if max_val >= threshold:
                return f"Ok# Vehicle connectivity is TRUE.+{full_path}"
            else:
                return f"Not Ok# Vehicle connectivity is FALSE.+{full_path}"
        else:
            if max_val >= threshold:
                return f"Ok# Reference image found on screen.+{full_path}"
            else:
                return f"Not Ok# Reference image NOT found on screen.+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Compare_Screen_By_Image failed: {str(e)}"




################################################################ Scrolling #######################################################################

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

#             element = find_text_on_screen(driver, target_text)
#             if element:
#                 element.click()
#                 msg = f"[SUCCESS] Clicked on text: '{element.text}' after {scroll_count} scroll(s)"
#                 safe_print(msg)
#                 return "Ok"

#             scroll_down_continuous(driver)  # Simulates natural scroll
#             sleep(0.5)  # Wait for screen to stabilize/render

#             end_reached, new_screenshot = is_end_of_scroll(driver, prev_screenshot, threshold)
#             safe_print(f"[SSIM] Scroll#{scroll_count} SSIM-based EndReached: {end_reached}")
#             if end_reached:
#                 return "Not ok"

#             prev_screenshot = new_screenshot

#         return "Not ok"

#     except Exception as e:
#         err = f"[ERROR] scroll_and_click_text failed: {e}\n{traceback.format_exc()}"
#         safe_print(err)
#         return err

def Scroll_and_Click_Text(text_maxScrolls, threshold=0.98):
    try:
        import traceback
        from time import sleep

        param1, param2 = text_maxScrolls.split(",", 1)
        target_text = param1.strip()
        max_scrolls = int(param2.strip())
        
        
        if not init_driver():
            return "[ERROR] Appium driver initialization failed"

        prev_screenshot = take_screenshot_cv(driver)
        scroll_count = 0

        while scroll_count < max_scrolls:
            scroll_count += 1
            safe_print(f"[SCROLL] Attempt #{scroll_count}")
           

            elements = driver.find_elements("xpath", f"//*[@text='{target_text}']")
            for el in elements:
                try:
                    el.click()  # ✅ attempt click immediately
                    safe_print(f"[SUCCESS] Clicked on text: '{target_text}' after {scroll_count} scroll(s)")
                    return f"Ok# Scrolled and clicked on text {target_text}"
                except Exception as click_err:
                    safe_print(f"[RETRY] Click failed due to: {click_err} — retrying after re-fetch...")

            scroll_down_continuous(driver)
            sleep(0.5)

            end_reached, new_screenshot = is_end_of_scroll(driver, prev_screenshot, threshold)
            safe_print(f"[SSIM] Scroll#{scroll_count} SSIM-based EndReached: {end_reached}")
            if end_reached:
                capture_screenshot(temp_path)
                curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"screenshot_{timestamp}.png"
                full_path = os.path.join(Screenshot_path, save_path)
               # Save the image
                cv2.imwrite(full_path, curr_img)
                return f"Not ok# Scrolled but not found text {target_text}+{full_path}"

            prev_screenshot = new_screenshot

            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                break
        
        capture_screenshot(temp_path)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
        # Save the image
        cv2.imwrite(full_path, curr_img)

        return f"Not ok# Scrolled but not found text {target_text}+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        err = f"[ERROR] scroll_and_click_text failed: {e}\n{traceback.format_exc()}"
        safe_print(err)
        return err


# def Scroll_and_Click_Text(text_maxScrolls, threshold=0.98):
#     """
#     Scrolls the screen until a target text is found and clicks it.

#     Args:
#         text_maxScrolls (str): "target_text,max_scrolls"
#         threshold (float): SSIM threshold to detect end of scroll

#     Returns:
#         str: "Ok# Clicked on target text"
#              "Not Ok# Target text not found after scrolling"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <details>"
#     """
#     try:
#         param1, param2 = text_maxScrolls.split(",", 1)
#         target_text = param1.strip()
#         max_scrolls = int(param2.strip())

#         if not init_driver():
#             return "ERROR: Appium driver initialization failed"

#         prev_screenshot = take_screenshot_cv(driver)
#         scroll_count = 0

#         while scroll_count < max_scrolls:
#             scroll_count += 1

#             elements = driver.find_elements("xpath", f"//*[@text='{target_text}']")
#             for el in elements:
#                 try:
#                     el.click()
#                     return f"Ok# Clicked on target text '{target_text}' after {scroll_count} scroll(s)"
#                 except Exception as click_err:
#                     safe_print(f"[RETRY] Click failed due to: {click_err}")

#             scroll_down_continuous(driver)
#             end_reached, new_screenshot = is_end_of_scroll(driver, prev_screenshot, threshold)
#             if end_reached:
#                 return f"Not Ok# Target text '{target_text}' not found after {scroll_count} scroll(s)"

#             prev_screenshot = new_screenshot

#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 return f"Not Ok# Aborted by abort signal"

#         return f"Not Ok# Target text '{target_text}' not found after {max_scrolls} scroll(s)"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Scroll_and_Click_Text failed: {str(e)}"



                                                               ############## Scroll and click by image ############

# def Scroll_and_Click_Image(path_maxScroll, threshold=0.98):
#     try:
#         import traceback
#         from time import sleep

#         # Parse input: "path_to_image.png,max_scrolls"
#         param1, param2 = path_maxScroll.split(",", 1)
#         image_path = param1.strip()
#         max_scrolls = int(param2.strip())

#         if not init_driver():
#             return "[ERROR] Appium driver initialization failed"

#         # Load the reference image (template)
#         template = load_reference_image(image_path)
#         if template is None:
#             return f"[ERROR] Could not load reference image: {image_path}"

#         prev_screenshot = take_screenshot_cv(driver)
#         scroll_count = 0

#         while scroll_count < max_scrolls:
#             scroll_count += 1
#             safe_print(f"[SCROLL] Attempt #{scroll_count}")

#             try:
#                 screenshot = take_screenshot_cv(driver)
#                 pos = find_template_in_screenshot(screenshot, template, threshold=0.8)
#             except Exception as e:
#                 return "Not ok"

#             if pos:
#                 driver.execute_script("mobile: clickGesture", {"x": pos[0], "y": pos[1]})
#                 msg = "Ok"
#                 safe_print(msg)
#                 return msg

#             scroll_down_continuous(driver)
#             sleep(1.0)  # Let UI settle after scroll

#             try:
#                 end_reached, new_screenshot = is_end_of_scroll(driver, prev_screenshot, threshold)
#                 safe_print(f"[SSIM] Scroll#{scroll_count} EndReached: {end_reached}")
#             except Exception as e:
#                 return "Not ok"

#             if end_reached:
#                 msg = "Not ok"
#                 safe_print(msg)
#                 return msg

#             prev_screenshot = new_screenshot

#         return "Not ok"

#     except Exception as e:
#         err = f"[ERROR] Scroll_and_Click_Image failed: {e}\n{traceback.format_exc()}"
#         safe_print(err)
#         return err



def Scroll_and_Click_Image(path_maxScroll, threshold=0.98):
    """
    Scrolls the screen until a target image is found and clicks it.

    Args:
        path_maxScroll (str): "image_path,max_scrolls"
        threshold (float): SSIM threshold to detect end of scroll

    Returns:
        str: "Ok# Clicked on target image"
             "Not Ok# Target image not found after scrolling"
             "Not Ok# Aborted by abort signal"
             "ERROR: <details>"
    """
    try:
        param1, param2 = path_maxScroll.split(",", 1)
        image_path = param1.strip()
        max_scrolls = int(param2.strip())
         

        if not init_driver():
            return "ERROR: Appium driver initialization failed"

        template = load_reference_image(image_path)
        if template is None:
            return f"ERROR: Reference image not found at {image_path}"

        prev_screenshot = take_screenshot_cv(driver)
        scroll_count = 0

        while scroll_count < max_scrolls:
            scroll_count += 1

            screenshot = take_screenshot_cv(driver)
            pos = find_template_in_screenshot(screenshot, template, threshold)

            if pos:
                try:
                    driver.execute_script("mobile: clickGesture", {"x": pos[0], "y": pos[1]})
                    return f"Ok# Clicked on target image after {scroll_count} scroll(s)"
                except Exception as click_err:
                    return f"ERROR: Click gesture failed on '{image_path}': {click_err}"

            scroll_down_continuous(driver)

            end_reached, new_screenshot = is_end_of_scroll(driver, prev_screenshot, threshold)
            if end_reached:
                capture_screenshot(temp_path)
                curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"screenshot_{timestamp}.png"
                full_path = os.path.join(Screenshot_path, save_path)
               # Save the image
                cv2.imwrite(full_path, curr_img)
                return f"Not Ok# Target image not found after {scroll_count} scroll(s)+{full_path}"

            prev_screenshot = new_screenshot

            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                return f"Not Ok# Aborted by abort signal"
        
        temp_path=capture_screenshot(temp_path)
        curr_img = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshot_{timestamp}.png"
        full_path = os.path.join(Screenshot_path, save_path)
               # Save the image
        cv2.imwrite(full_path, curr_img)

        return f"Not Ok# Target image not found after {max_scrolls} scroll(s)+{full_path}"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Scroll_and_Click_Image failed: {str(e)}"

# init_driver()
# print(Scroll_and_Click_Image("D:\\MEP00179\\Sourcecode-09-06-2025\\Sourcecode\\Configuration_Files\\Appium\\Operational Images\\4.1.jpg,2"))

############################################## Tap using coordinates ########################################################


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

# def Click_By_Coordinate(coord_string):
#     try:
#         #global driver
#         param1, param2 = coord_string.split(",", 1)

#         # Attempt driver recovery if needed
#         if driver is None or not is_driver_alive(driver):
#             safe_print("[RECOVERY] Reinitializing Appium driver...")
#             init_result = init_driver()
#             if not init_result.startswith("PASS"):
#                 return "Not ok"

#         # Parse input string: "x,y"
#         parts = param1.split('_')
#         if len(parts) != 2:
#             return "Not ok"

#         x = int(parts[0].strip())
#         y = int(parts[1].strip())

#         driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
#         msg = f"[SUCCESS] Tapped at coordinates ({x}, {y})"
#         safe_print(msg)
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
            
#         return "Ok"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         err = f"[ERROR] tap_by_coordinates failed: {e}\n{traceback.format_exc()}"
#         safe_print(err)
#         return err
    

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
        return f"Ok# Clicked at coordinates ({x}, {y})"

    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return f"ERROR: Click_By_Coordinate failed: {str(e)}"





################################################## Realtime coordinates ###########################################################


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

############################################### Give input ###################################################

# def Send_Inputs(text):
#     try:
#         param1, param2 = text.split(",", 1)
#         el = driver.find_element("class name", "android.widget.EditText")
#         el.clear()
#         el.send_keys(param1)
#         print(f"[INPUT] Entered text: {text}")
#         return "Ok"
#     except Exception as e:
#         print(f"[ERROR] Input failed: {e}")
#         return "Not ok"

# def Send_Inputs(text):
#     try:
#         param1,param2= text.split(",",1)
#         key, value = param1.split(":", 1)

#         try:
#             # Try to find by accessibility id (content-desc)
#             el = driver.find_element("accessibility id", key)
#         except:
#             try:
#                 # Try to find by resource-id
#                 el = driver.find_element("id", key)
#             except:
#                 try:
#                     # Try to find by placeholder text using XPath
#                     el = driver.find_element("xpath", f"//android.widget.EditText[@text='{key}']")
#                 except:
#                     print(f"[ERROR] Could not find input field for key: {key}")
#                     print(f"[INPUT] Set '{key}' to '{value}'")
#                     return "Not ok"

#         el.clear()
#         el.send_keys(value)
#         print(f"[INPUT] Set '{key}' to '{value}'")
#         return "Ok"
       


#     except Exception as e:
#         print(f"[ERROR] Input failed: {e}")
#         return "Not ok"


# def Send_Inputs(text):
#     try:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         # Get all input fields on the current screen
#         input_fields = driver.find_elements("xpath", "//android.widget.EditText")

#         # Case 1: Only one input field, ignore key and send value directly
#         if len(input_fields) == 1:
#             if ":" in text:
#                 # Still extract value even if key:value format is used
#                 value = text.split(":", 1)[1].split(",", 1)[0]
#             else:
#                 value = text.strip()
#             el = input_fields[0]
#             el.clear()
#             el.send_keys(value)
#             print(f"[INPUT] Only one input field found. Set value '{value}' directly.")
#             return "Ok"

#         # Case 2: Multiple input fields, need to extract key and value
#         param1, _ = text.split(",", 1)
#         key, value = param1.split(":", 1)

#         try:
#             el = driver.find_element("accessibility id", key)
#         except:
#             try:
#                 el = driver.find_element("id", key)
#             except:
#                 try:
#                     el = driver.find_element("xpath", f"//android.widget.EditText[@text='{key}']")
#                 except:
#                     print(f"[ERROR] Could not find input field for key: {key}")
#                     print(f"[INPUT] Set '{key}' to '{value}'")
#                     return "Not ok"

#         el.clear()
#         el.send_keys(value)
#         print(f"[INPUT] Multiple input fields found. Set '{key}' to '{value}'")
            
#         return "Ok"

#     except Exception as e:
#         print(f"[ERROR] Exception in Send_Inputs: {e}")
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return "Not ok"




# def Send_Inputs(text):
#     """
#     Sends input text to the appropriate EditText field(s) on the screen.

#     Args:
#         text (str): "key:value,timeout" or just "value" if only one input field

#     Returns:
#         str: "Ok# Input sent successfully"
#              "Not Ok# Input field not found"
#              "Not Ok# Aborted by abort signal"
#              "ERROR: <details>"
#     """
#     try:
#         # Abort check
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#             return "Not Ok# Aborted by abort signal"

#         # Get all input fields
#         input_fields = driver.find_elements("xpath", "//android.widget.EditText")

#         # Case 1: Only one input field
#         if len(input_fields) == 1:
#             if ":" in text:
#                 value = text.split(":", 1)[1].split(",", 1)[0].strip()
#             else:
#                 value = text.strip()
#             el = input_fields[0]
#             el.clear()
#             el.send_keys(value)
#             return f"Ok# Input '{value}' sent to the only input field"

#         # Case 2: Multiple input fields
#         param1, _ = text.split(",", 1)
#         key, value = param1.split(":", 1)
#         value = value.strip()

#         try:
#             el = driver.find_element("accessibility id", key)
#         except:
#             try:
#                 el = driver.find_element("id", key)
#             except:
#                 try:
#                     el = driver.find_element("xpath", f"//android.widget.EditText[@text='{key}']")
#                 except:
#                     return f"Not Ok# Input field for key '{key}' not found"

#         el.clear()
#         el.send_keys(value)
#         return f"Ok# Input '{value}' sent to field '{key}'"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return f"ERROR: Send_Inputs failed: {str(e)}"

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

            time.sleep(1)
        
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
        return f"ERROR: Send_Inputs failed: {str(e)}"



# init_driver()
# Send_Inputs("Mobile number:254365,10")


############################################## Notification ##################################################

# def get_notification_text(text: str) -> dict:
#     try:
#         param1, param2 = text.split(",", 1)
#         search_keyword = param1
#         # Run ADB command to get current notifications in JSON format
#         result = subprocess.run(
#             ["adb", "shell", "dumpsys", "notification"],
#             capture_output=True,
#             text=True,
#             timeout=10
#         )

#         notifications_raw = result.stdout

#         # Optional: limit to "active notifications" section
#         active_notifications = re.findall(r'NotificationRecord\{.*?\n(?:.*\n)*?tickerText=.*?\n', notifications_raw)

#         found_notifications = []

#         for notif in active_notifications:
#             if search_keyword.lower() in notif.lower():
#                 # Extract title and text (simple regex for common fields)
#                 title_match = re.search(r'extras=.*?android.title=(.*?)\n', notif)
#                 text_match = re.search(r'extras=.*?android.text=(.*?)\n', notif)

#                 title = title_match.group(1).strip() if title_match else ""
#                 text = text_match.group(1).strip() if text_match else ""

#                 found_notifications.append({
#                     "title": title,
#                     "text": text
#                 })
            
#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break
        

#         return {
#             "status": "found" if found_notifications else "not_found",
#             "count": len(found_notifications),
#             "notifications": found_notifications
#         }

#     except subprocess.TimeoutExpired:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
            
#         return {"status": "error", "message": "ADB command timed out"}
#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         return {"status": "error", "message": str(e)}



def Get_Notification_Text(text: str) -> dict:
    """
    Fetches notifications containing the given keyword using ADB.

    Args:
        text (str): "keyword,timeout" (timeout is ignored here but kept for format consistency)

    Returns:
        dict: {
            "status": "Ok" / "Not ok" / "Not Ok# Aborted by abort signal" / "ERROR: <details>",
            "count": <number of notifications found>,
            "notifications": [ { "title": ..., "text": ... }, ... ]
        }
    """
    try:
        param1, _ = text.split(",", 1)
        search_keyword = param1.strip()

        # Abort check
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
            return {"status": "Not Ok# Aborted by abort signal", "count": 0, "notifications": []}

        # Run ADB command
        result = subprocess.run(
            ["adb", "shell", "dumpsys", "notification"],
            capture_output=True,
            text=True,
            timeout=10
        )
        notifications_raw = result.stdout

        # Extract active notifications
        active_notifications = re.findall(
            r'NotificationRecord\{.*?\n(?:.*\n)*?tickerText=.*?\n', notifications_raw
        )

        found_notifications = []
        for notif in active_notifications:
            if search_keyword.lower() in notif.lower():
                title_match = re.search(r'extras=.*?android.title=(.*?)\n', notif)
                text_match = re.search(r'extras=.*?android.text=(.*?)\n', notif)

                title = title_match.group(1).strip() if title_match else ""
                text_val = text_match.group(1).strip() if text_match else ""

                found_notifications.append({"title": title, "text": text_val})

        status = "Ok" if found_notifications else "Not Ok# Notification not found"
        return {"status": status, "count": len(found_notifications), "notifications": found_notifications}

    except subprocess.TimeoutExpired:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return {"status": "ERROR: ADB command timed out", "count": 0, "notifications": []}
    except Exception as e:
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
        return {"status": f"ERROR: {str(e)}", "count": 0, "notifications": []}





########################################### Swipe from edge ##############################################

# def Swipe_From_Left_Edge(text):
#     try:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
#         param1, param2 = text.split(",", 1)
#         # Get screen dimensions
#         size = driver.get_window_size()
#         width = size["width"]
#         height = size["height"]

#         # Edge swipe parameters (left edge swipe right)
#         start_x = 5
#         end_x = int(width * 0.2)
#         y = int(height / 2)

#         # Perform swipe gesture
#         driver.execute_script("mobile: swipeGesture", {
#             "left": start_x,
#             "top": y - 50,
#             "width": end_x - start_x,
#             "height": 100,
#             "direction": "right",
#             "percent": 0.75
#         })

#         driver.quit()
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
             
            
#         return "Ok"

#     except Exception as e:
#         if os.path.exists(file_to_watch):
#             os.remove(file_to_watch)
            
#         return f"Not ok"



def Swipe_From_Left_Edge(text):
    """
    Performs a left-edge swipe to the right.

    Args:
        text (str): "param,timeout" format (timeout is ignored here)

    Returns:
        str: "Ok" / "Not Ok# Aborted by abort signal" / "ERROR: <details>"
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
        return f"ERROR: Swipe_From_Left_Edge failed: {str(e)}"




    
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
            
        return f"Error:Swipe from right edge failed: {str(e)}"

##################################### Normal Scroll ####################################

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
        return f"ERROR:scroll failed: {str(e)}"

################################################# SCREENSHOT ############################################


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

def NSS(path):
    
    try:

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
        time.sleep(3)
        

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
        return f"ERROR: Screenshot error\n{str(e)}"
    except Exception:
        return f"ERROR: Unknown error\n{traceback.format_exc()}"


def SS(path):
    
    try:

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



# def Validate_Alerts(search_str):

#     """
#     Open notifications, take screenshot, extract text,
#     search for a string, clear notifications, and close panel.

#     Args:
#         driver: Appium webdriver instance
#         search_str (str): String to search in notification text

#     Returns:
#         str: "FOUND" if search_str exists in notification text, else "NOT_FOUND"
#     """
#     try:
#         param1, param2 = search_str.split(",", 1)
#         timeout=int(param2)
#         Alerts_Arr = param1.split(":")
#         print(Alerts_Arr)
#         # 1. Open notification panel
#         driver.open_notifications()
#         count=0
#         status=""
#         output=""

#         itr=0

#         for i in Alerts_Arr:
#             time.sleep(timeout)
            
#             # 2. Take screenshot
#             screenshot_path = "D:\\notification.png"
#             driver.save_screenshot(screenshot_path)

#             input_len=len(Alerts_Arr)

#             # 3. Extract text using OCR
#             image = cv2.imread(screenshot_path)
#             text = pytesseract.image_to_string(image)
#             #print("Extracted Notification Text:\n", text)

#             # 4. Search for the string
#             bolleasn_op = "Not ok"
#             if i and i.lower() in text.lower():
#                 #bolleasn_op = "Ok"
#                 count+=1
#                 status = status + i + " PASS"
#             else:
#                 status = status + i + " FAIL"
            
#             if itr < (input_len - 1):
#                 status += ", \n"
#             itr+=1

#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break

        
#         if count == len(Alerts_Arr):
#             bolleasn_op="Ok"
        
#         output= bolleasn_op+ ":" + status

        
#         #print(bolleasn_op)
#         # os.system("adb shell service call notification 1")
#         # print("Notifications cleared via ADB.")

#         # selectors = [
#         # 'new UiSelector().descriptionContains("Clear")',
#         # 'new UiSelector().textContains("Clear")',
#         # 'new UiSelector().descriptionContains("Dismiss")',
#         # 'new UiSelector().textContains("Dismiss")'
#         # ]
    
#         # for selector in selectors:
#         #     try:
#         #         clear_btn = driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, selector)
#         #         clear_btn.click()
#         #         print("Notifications cleared.")
#         #         
#         #         return True
#         #     except:
#         #         continue

#         driver.back()

#         return output

#     except Exception as e:
#         print(f"Error: {e}")
#         driver.back()
#         return "ERROR"


# def Swipe_Up(input):
#     try:
#         size = driver.get_window_size()
#         width = size["width"]
#         height = size["height"]

#         start_x = width // 2
#         start_y = int(height * 0.90)  # bottom area
#         end_y   = int(height * 0.60)  # drag up

#         driver.swipe(start_x, start_y, start_x, end_y, 800)
#         return "Ok# Swiped up (section opened)"
#     except Exception as e:
#         return f"ERROR (Swipe Up): {str(e)}"


# def Swipe_Down(input):
#     try:
#         size = driver.get_window_size()
#         width = size["width"]
#         height = size["height"]

#         start_x = width // 2
#         start_y = int(height * 0.60)  # higher up
#         end_y   = int(height * 0.90)  # drag down to bottom

#         driver.swipe(start_x, start_y, start_x, end_y, 800)
#         return "Ok# Swiped down (section closed)"
#     except Exception as e:
#         return f"ERROR (Swipe Down): {str(e)}"


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

            time.sleep(1)  # small delay before retry

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

            

        # Timeout reached → Not ok
        return f"Not ok# Missing status on screen: {Not_ok_output}+{full_path}"

    except Exception as e:
        return f"ERROR: {str(e)}"
    

# init_driver()
# print(Compare_Screen_By_Multiple_Texts("Front Driver:Rear Driver,10"))

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
            time.sleep(timeout)

            # 1. Take screenshot with current date & time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(base_dir, f"status_{timestamp}.png")
            driver.save_screenshot(screenshot_path)

            # 2. OCR on screenshot
            image = cv2.imread(screenshot_path)
            text = pytesseract.image_to_string(image)
            text=extract_status(text)

            # 3. Split feature & expected result
            parts = item.split()
            feature = " ".join(parts[:-1])
            expected = parts[-1]
            
            clean_text = feature.replace('\n', ' ').replace('\r', ' ').strip()

            # 4. Compare expected with OCR text
            bolleasn_op = "Not ok"
            if item.lower() in text.lower():
                count += 1
                status_log += f"Result: Pass,Status: {clean_text} is updated on mobile.+{screenshot_path}"
            else:
                status_log += f"Result: Fail,Status: {clean_text} is not updated on mobile.+{screenshot_path}"

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
        return "ERROR"

# init_driver()
# print(Validate_Status("Front right tyre 0.0 psi,10"))



# def Validate_Alerts(search_str):
#     """
#     Open notifications, take screenshot, extract text,
#     search for a string, clear notifications, and close panel.

#     Args:
#         search_str (str): String to search in notification text

#     Returns:
#         str: "Ok# ..." with PASS/FAIL results or "ERROR"
#     """
#     try:
#         param1, param2 = search_str.split(",", 1)
#         timeout = int(param2)
#         Alerts_Arr = param1.split(":")
#         print(Alerts_Arr)

#         # Screenshot directory
#         base_dir = PROJECT_ROOT /  "Appium" / "Validation Screenshots"
#         if not os.path.exists(base_dir):
#             os.makedirs(base_dir)

#         # 1. Open notification panel
#         driver.open_notifications()
#         count = 0
#         status = ""
#         output = ""
#         itr = 0

#         for i in Alerts_Arr:
#             time.sleep(timeout)

#             # 2. Take screenshot with current date & time
#             timestamp = time.strftime("%Y%m%d_%H%M%S")
#             screenshot_path = os.path.join(base_dir, f"notification_{timestamp}.png")
#             driver.save_screenshot(screenshot_path)

#             input_len = len(Alerts_Arr)

#             # 3. Extract text using OCR
#             image = cv2.imread(screenshot_path)
#             text = pytesseract.image_to_string(image)

#             # 4. Search for the string
#             bolleasn_op = "Not ok"
#             if i and i.lower() in text.lower():
#                 count += 1
#                 status += f"Result: Pass, Status: {i} Alert is received on mobile.+ {screenshot_path}"
#             else:
#                 status += f"Result: Fail, Status: {i} Alert is not received on mobile.+ {screenshot_path}"

#             if itr < (input_len - 1):
#                 status += ", \n"
#             itr += 1

#             if os.path.exists(file_to_watch):
#                 os.remove(file_to_watch)
#                 break

#         if count == len(Alerts_Arr):
#             bolleasn_op = "Ok"

#         output = bolleasn_op + "#\n" + status
#         Click_By_Text("Clear all,3")
#         #driver.back()
#         return output

#     except Exception as e:
#         print(f"Error: {e}")
#         driver.back()
#         return "ERROR"

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
        timeout = float(param2)
        Alerts_Arr = param1.split(":")
        print(Alerts_Arr)

        # Screenshot directory
        base_dir = PROJECT_ROOT / "Appium" / "Validation Screenshots"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        driver.open_notifications()
        count = 0
        status = ""
        itr = 0

        poll_interval = 1  # seconds

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
                screenshot_path = os.path.join(base_dir, f"notification_{timestamp}.png")
                driver.save_screenshot(screenshot_path)

                # OCR extract text
                image = cv2.imread(screenshot_path)
                text = pytesseract.image_to_string(image)

                if alert_text.lower() in text.lower():
                    found = True
                    break

                if os.path.exists(file_to_watch):
                    os.remove(file_to_watch)
                    break

                # Calculate remaining time
                time_left = timeout - elapsed
                # Sleep either poll_interval or remaining time, whichever is smaller
                time.sleep(min(poll_interval, time_left))
            
            clean_alert = alert_text.replace('\n', ' ').replace('\r', ' ').strip()


            if found:
                count += 1
                status += f"Result: Pass, Status: {clean_alert} is received on mobile.+{screenshot_path}"
            else:
                status += f"Result: Fail, Status: {clean_alert} is not received on mobile.+{screenshot_path}"

            if itr < (len(Alerts_Arr) - 1):
                status += ",\n"
            itr += 1

            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                break

        bolleasn_op = "Ok" if count == len(Alerts_Arr) else "Not ok"
        

        output = bolleasn_op + "#" + status

        
        #driver.back()  # optional close notifications panel
        
        if (bolleasn_op == "Not ok"):
            Swipe_From_Right_Edge("Hello")
        else:
            Click_By_Text("Clear all,1")

        return output

    except Exception as e:
        print(f"Error: {e}")
        driver.back()
        return "ERROR"


# init_driver()
# print(Validate_Alerts("Intrusion Alert,10"))




def Check_Remote_Command_Status(input,base_dir=Screenshot_path, interval=0.5):
    """
    Continuously capture screenshots and OCR-check for 'Successfull/Successful'
    until timeout. Ends early if found.
 
    Args:
        base_dir (str): Directory to save screenshot
        timeout (int): Max time in seconds to wait
        interval (float): Interval in seconds between checks
 
    Returns:
        str: "Ok# Remote command executed successfully, Screenshot: <path>"
             "Not Ok# Remote command not executed successfully, Screenshot: <path>"
             "ERROR: <details>"
    """
    try:
        param1, param2 = input.split(",", 1)
        timeout=int(param2)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
 
        end_time = time.time() + timeout
        #screenshot_path = None
        text = ""
 
        if os.path.exists(file_to_watch):
            os.remove(file_to_watch)
 
        while time.time() < end_time:
            # Capture screenshot (in memory)
            png = driver.get_screenshot_as_png()
            np_img = np.frombuffer(png, np.uint8)
            image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
 
            # OCR
            text = pytesseract.image_to_string(image)
 
            # Save last screenshot
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(base_dir, f"quick_validate_{timestamp}.png")
            with open(screenshot_path, "wb") as f:
                f.write(png)
 
            # Check success
            if "Successfully" in text or "Successful" in text:
                return f"Ok# Remote command executed successfully.+{screenshot_path}"
 
            time.sleep(interval)  # wait before next check
 
            if os.path.exists(file_to_watch):
                os.remove(file_to_watch)
                break
       
 
        # Timeout reached → Not ok
        return f"Not ok# Remote command not executed successfully.+{screenshot_path}"
 
    except Exception as e:
        return f"ERROR: {str(e)}"

from appium.webdriver.common.touch_action import TouchAction

def Long_Press_Indirect_By_Image(image_path, duration=3000, threshold=0.8):
    param1, param2 = image_path.split(",", 1)
    img_path = param1
    timeout = int(param2)

    screenshot_file = os.path.join(Screenshot_path, "temp.png")
    driver.save_screenshot(screenshot_file)

    screen = cv2.imread(screenshot_file)
    template = cv2.imread(img_path)

    if screen is None or template is None:
        return "ERROR: Failed to read images"

    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        return f"Not Ok# Image '{image_path}' not found"

    x = max_loc[0] + template.shape[1] // 2
    y = max_loc[1] + template.shape[0] // 2

    # Indirect long press using TouchAction
    action = TouchAction(driver)
    action.press(x=x, y=y).wait(ms=duration).release().perform()

    return f"Ok# Long pressed on image '{image_path}' indirectly at ({x},{y})"

def Long_Press_Indirect_By_Image(image_path, duration=2000, threshold=0.8):
    """
    Long press on an element found by image reference using mobile: dragGesture.

    Args:
        image_path (str): "path_to_image,timeout"
        duration (int): Long press duration in ms
        threshold (float): Template matching threshold

    Returns:
        str
    """
    try:
        param1, param2 = image_path.split(",", 1)
        img_path = param1.strip()
        timeout = int(param2)

        screenshot_file = os.path.join(Screenshot_path, "temp.png")
        driver.save_screenshot(screenshot_file)

        screen = cv2.imread(screenshot_file)
        template = cv2.imread(img_path)

        if screen is None or template is None:
            return "ERROR: Failed to read images"

        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            return f"Not Ok# Image '{image_path}' not found"

        x = max_loc[0] + template.shape[1] // 2
        y = max_loc[1] + template.shape[0] // 2

        # ✅ Use dragGesture to simulate long press at the same position
        driver.execute_script(
            "mobile: dragGesture",
            {
                "startX": x,
                "startY": y,
                "endX": x,      # same point for long press
                "endY": y,
                "duration": duration  # hold time in ms
            }
        )

        return f"Ok# Long pressed on image '{image_path}' at ({x},{y})"

    except Exception as e:
        return f"ERROR: Long_Press_Indirect_By_Image failed: {str(e)}"





#init_driver()
#print(Long_Press_Indirect_By_Image("C:\\Users\\panch\\OneDrive - Maxeye Technologies Pvt Ltd\\Documents\\VID.jpg,10"))
#print(Long_Press_Indirect_By_Image("C:\\Users\\panch\\OneDrive - Maxeye Technologies Pvt Ltd\\Documents\\VID.jpg,2000"))

# print(Scroll_and_Click_Text("87a8aab6-aab6-48aab6f45a-88aab6f45aadc-adc4e8=7498347036,10"))



# init_driver()
# print(Validate_Alerts("a1:a2:a3,10"))
    
############################################## Logcat ################################################

def log_handler(cmd):
    global log_process, temp_log_fullpath

    param1, param2 = cmd.split(",", 1)
    command = param1.strip()

    if command.lower() == "start":
        try:
            # Make log directory if not exists
            os.makedirs(temp_logfilepath, exist_ok=True)

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

    elif command.lower() == "stop":
        try:
            if log_process:
                log_process.terminate()
                log_process.wait()
                log_process = None

                # Rename with timestamp
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
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

def Wait_Until_Text_Disappears(text_to_watch):
    """
    Wait until a given text disappears from the screen.
    Halts until text disappears, or saves screenshot on failure.
    """
    try:
        param1,param2=text_to_watch.split(",")
        timeout=int(param2)
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{param1}")')
            )
        )
        return "Ok# Screen got changed"
    except Exception:
        # Take screenshot directly
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_path = os.path.join(
            Screenshot_path, f"screenshot_{timestamp}.png"
        )
        driver.get_screenshot_as_file(full_path)
        return f"Not Ok# Text '{param1}' still present after {timeout} sec+{full_path}"


