from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
import cv2
import numpy as np
import base64
from time import sleep
from skimage.metrics import structural_similarity as ssim
import os

# Convert base64 screenshot to OpenCV image
def screenshot_to_cv_image(screenshot_base64):
    nparr = np.frombuffer(base64.b64decode(screenshot_base64), np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

# Take screenshot as OpenCV image
def take_screenshot_cv(driver):
    screenshot_base64 = driver.get_screenshot_as_base64()
    return screenshot_to_cv_image(screenshot_base64)

# Detect if screen content hasn't changed (end of scroll)
def is_end_of_scroll(driver, prev_screenshot, threshold=0.98):
    new_screenshot = take_screenshot_cv(driver)

    if prev_screenshot.shape != new_screenshot.shape:
        new_screenshot = cv2.resize(new_screenshot, (prev_screenshot.shape[1], prev_screenshot.shape[0]))

    grayA = cv2.cvtColor(prev_screenshot, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(new_screenshot, cv2.COLOR_BGR2GRAY)

    score, _ = ssim(grayA, grayB, full=True)
    return score > threshold, new_screenshot

# Scroll down slightly
def scroll_down(driver):
    window = driver.get_window_size()
    left = window['width'] // 2
    start_y = int(window['height'] * 0.6)
    end_y = int(window['height'] * 0.55)

    driver.execute_script("mobile: swipeGesture", {
        "left": left,
        "top": end_y,
        "width": 0,
        "height": start_y - end_y,
        "direction": "up",
        "percent": 1.0
    })
    sleep(0.7)

# Search for text on screen
def find_text_on_screen(driver, text):
    try:
        element = driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR,
                                      f'new UiSelector().textContains("{text}")')
        return element
    except:
        return None

# Appium capabilities
capabilities = {
    "platformName": "Android",
    "platformVersion": "12",
    "deviceName": "RZ8NB1B2MJR",
    "appPackage": "com.flipkart.android",
    "appActivity": "com.flipkart.android.activity.HomeFragmentHolderActivity",
    "automationName": "UiAutomator2",
    "autoGrantPermissions": True,
    "noReset": True
}

# Start session
driver = webdriver.Remote("http://localhost:4723", options=UiAutomator2Options().load_capabilities(capabilities))
sleep(5)

# Define target text to search
target_text = "Fashion"  # Change this to the desired visible text

# Initial screenshot
prev_screenshot = take_screenshot_cv(driver)
scroll_count = 0
element = None

while True:
    scroll_count += 1
    print(f"🔍 Scroll attempt {scroll_count}")

    element = find_text_on_screen(driver, target_text)
    if element:
        print(f"✅ Found text element: {element.text}")
        element.click()
        print("✅ Clicked on the text element.")

        # Save screenshot after clicking
        screenshot_path = os.path.abspath("screenshot_after_click.png")
        success = driver.get_screenshot_as_file(screenshot_path)

        if success:
            print(f"📸 Screenshot successfully saved at: {screenshot_path}")
        else:
            print("❌ Failed to save screenshot.")

        break

    scroll_down(driver)

    end_reached, new_screenshot = is_end_of_scroll(driver, prev_screenshot)
    if end_reached:
        print("🚧 Reached end of scrollable content.")
        break

    prev_screenshot = new_screenshot

# Final result
if not element:
    print("❌ Could not find the text after scrolling to end.")

driver.quit()
