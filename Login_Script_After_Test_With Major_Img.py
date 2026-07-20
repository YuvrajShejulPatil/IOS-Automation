from appium import webdriver
import cv2
import numpy as np
import base64
import threading
from time import time, sleep
from skimage.metrics import structural_similarity as ssim
import os
import pathlib
import sys

# === Safe print ===
def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode())

# === Globals ===
last_change_time = time()
monitor_running = True
monitor_lock = threading.Lock()

def wait_until_text_appears(driver, visible_text, timeout=120, check_interval=2):
    safe_print(f"[WAIT] Waiting for text to appear: '{visible_text}'")
    start_time = time()
    while time() - start_time < timeout:
        try:
            element = driver.find_element("xpath", f"//*[@text='{visible_text}']")
            if element:
                safe_print(f"[FOUND] Text appeared: '{visible_text}'")
                return True
        except:
            pass
        sleep(check_interval)
    safe_print(f"[TIMEOUT] Text did not appear in {timeout} seconds -> '{visible_text}'")
    os._exit(1)

def wait_until_image_appears(driver, path, threshold=0.8, timeout=120, check_interval=2):
    safe_print(f"[WAIT] Waiting for image to appear: {path}")
    start_time = time()
    while time() - start_time < timeout:
        if check_image_exists(driver, path, threshold):
            safe_print(f"[FOUND] Image appeared: {path}")
            return True
        sleep(check_interval)
    safe_print(f"[TIMEOUT] Image did not appear in {timeout} seconds -> {path}")
    os._exit(1)

def click_by_text(driver, visible_text, timeout=10):
    try:
        driver.implicitly_wait(timeout)
        el = driver.find_element("xpath", f"//*[@text='{visible_text}']")
        el.click()
        safe_print(f"[CLICK] Clicked on text: '{visible_text}'")
        return True
    except Exception as e:
        safe_print(f"[ERROR] Text not found: '{visible_text}' - {e}")
        return False

def screenshot_to_cv_image(screenshot_base64):
    nparr = np.frombuffer(base64.b64decode(screenshot_base64), np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def take_screenshot(driver):
    return screenshot_to_cv_image(driver.get_screenshot_as_base64())

def images_are_different(img1, img2, threshold=0.98):
    h, w = min(img1.shape[0], img2.shape[0]), min(img1.shape[1], img2.shape[1])
    sim_score, _ = ssim(
        cv2.cvtColor(img1[:h, :w], cv2.COLOR_BGR2GRAY),
        cv2.cvtColor(img2[:h, :w], cv2.COLOR_BGR2GRAY),
        full=True
    )
    return sim_score < threshold

def screen_monitor(driver):
    global last_change_time
    prev_img = take_screenshot(driver)
    while monitor_running:
        sleep(0.01)
        try:
            curr_img = take_screenshot(driver)
            if images_are_different(prev_img, curr_img):
                with monitor_lock:
                    last_change_time = time()
                prev_img = curr_img
            elif time() - last_change_time > 60:
                safe_print("[HANG] Screen hasn't changed for 60 seconds. Exiting.")
                os._exit(1)
        except:
            continue

def wait_for_screen_change(timeout=30):
    global last_change_time
    start = time()
    while time() - start < timeout:
        with monitor_lock:
            if time() - last_change_time < 1:
                return True
        sleep(0.2)
    safe_print(f"[TIMEOUT] Waiting for screen change exceeded {timeout} seconds")
    os._exit(1)

def load_reference_image(path, grayscale=False):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR)
    if img is None:
        safe_print(f"[ERROR] Failed to load image: {path}")
        exit(1)
    return img

def find_template_in_screenshot(screenshot_cv, template_cv, threshold=0.8):
    screenshot_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)
    template_gray = template_cv if len(template_cv.shape) == 2 else cv2.cvtColor(template_cv, cv2.COLOR_BGR2GRAY)
    for scale in np.linspace(0.7, 1.3, 25)[::-1]:
        resized_template = cv2.resize(template_gray, (0, 0), fx=scale, fy=scale)
        if resized_template.shape[0] > screenshot_gray.shape[0] or resized_template.shape[1] > screenshot_gray.shape[1]:
            continue
        res = cv2.matchTemplate(screenshot_gray, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            h, w = resized_template.shape[:2]
            return (max_loc[0] + w // 2, max_loc[1] + h // 2)
    return None

def click_image(driver, path, threshold=0.8):
    template = load_reference_image(path)
    screenshot = take_screenshot(driver)
    pos = find_template_in_screenshot(screenshot, template, threshold)
    if pos:
        driver.execute_script("mobile: clickGesture", {"x": pos[0], "y": pos[1]})
        safe_print(f"[CLICK] Clicked on image: {path}")
        return True
    safe_print(f"[NOT FOUND] Image not found: {path}")
    return False

def check_image_exists(driver, path, threshold=0.8):
    template = load_reference_image(path)
    screenshot = take_screenshot(driver)
    pos = find_template_in_screenshot(screenshot, template, threshold)
    safe_print(f"[CHECK] {'Found' if pos else 'Not Found'}: {path}")
    return pos is not None

def write_input(driver, text):
    try:
        el = driver.find_element("class name", "android.widget.EditText")
        el.clear()
        el.send_keys(text)
        safe_print(f"[INPUT] Entered text: {text}")
        return True
    except Exception as e:
        safe_print(f"[ERROR] Input failed: {e}")
        return False

# === Appium Setup ===
caps = {
    "platformName": "Android",
    "platformVersion": "12",
    "deviceName": "RZ8NB1B2MJR",
    "appPackage": "com.tatamotors.oneapp",
    "appActivity": "com.tatamotors.oneapp.ui.onboarding.OnBoardingActivity",
    "automationName": "UiAutomator2",
    "autoGrantPermissions": True,
    "noReset": True
}

driver = webdriver.Remote("http://localhost:4723", caps)
sleep(5)

monitor_thread = threading.Thread(target=screen_monitor, args=(driver,), daemon=True)
monitor_thread.start()

# === Image Folder Path ===
base = str(pathlib.Path(r"D:\Docker Containerization\Photos For Login"))

try:
    wait_until_text_appears(driver, "Register or Sign In")
    click_by_text(driver, "Register or Sign In")

    if check_image_exists(driver, f"{base}\\2.0.jpg"):
        click_by_text(driver, "Allow")

    wait_until_text_appears(driver, "Mobile number")
    click_by_text(driver, "Register or Sign In")
    write_input(driver, "7517336509")

    click_image(driver, f"{base}\\3.1.1.jpg")
    click_image(driver, f"{base}\\3.1.jpg")

    if check_image_exists(driver, f"{base}\\3.2 Valid.jpg"):
        safe_print("[ERROR] Mobile Number Invalid")
    else:
        safe_print("[VALID] Mobile Number Valid")

    wait_until_image_appears(driver, f"{base}\\4.0.jpg")
    click_image(driver, f"{base}\\4.0.jpg")
    write_input(driver, "254265")

    if check_image_exists(driver, f"{base}\\4.1.jpg"):
        safe_print("[ERROR] Invalid OTP")
    else:
        safe_print("[VALID] OTP Accepted")

    wait_until_image_appears(driver, f"{base}\\5.0.jpg")
    if check_image_exists(driver, f"{base}\\5.0.jpg"):
        click_image(driver, f"{base}\\5.1.jpg")

    wait_until_image_appears(driver, f"{base}\\6.0.jpg")
    click_image(driver, f"{base}\\6.0.jpg")
    write_input(driver, "1234")
    wait_until_image_appears(driver, f"{base}\\6.0.jpg")
    click_image(driver, f"{base}\\6.0.jpg")
    write_input(driver, "1234")

    if check_image_exists(driver, f"{base}\\6.1 Valid.jpg"):
        safe_print("[SUCCESS] PIN set successfully")
    else:
        safe_print("[FAIL] PIN setup failed")

    click_by_text(driver, "Skip")
    click_by_text(driver, "Allow Location Permissions")
    click_by_text(driver, "While using the app")
    click_by_text(driver, "Allow Notification")

    if click_by_text(driver, "Registration successful"):
        safe_print("[SUCCESS] Registration Successful")
        click_by_text(driver, "Proceed")
        sleep(3)
        if click_by_text(driver, "MH05CW19014"):
            safe_print("[SUCCESS] Vehicle is detected properly")
        else:
            safe_print("[ERROR] Vehicle is not detected properly")
    else:
        safe_print("[FAIL] Registration Failed")

except Exception as e:
    safe_print(f"[UNEXPECTED ERROR] {e}")

finally:
    monitor_running = False
    driver.quit()
