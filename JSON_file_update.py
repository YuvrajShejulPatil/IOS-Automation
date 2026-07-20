import json
import sys
import os
from pathlib import Path

# ==========================================================
# Step 1: Resolve Project Paths
# ==========================================================
try:
    BASE_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = BASE_DIR.parent.parent

    json_path = PROJECT_ROOT / "Appium" / "Capabilities" / "Capabilities.json"

    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Capabilities Path: {json_path}")

except Exception as e:
    print(f"Error resolving paths: {e}")
    sys.exit(1)


# ==========================================================
# Step 2: Validate Input
# ==========================================================
if len(sys.argv) < 2:
    print("Error: No input string received.")
    sys.exit(1)

input_string = sys.argv[1]

try:
    deviceName, platformVersion, appPackage, appActivity, udid = input_string.split(",")
except ValueError:
    print("Error: Expected 5 comma-separated values")
    print("Format: deviceName,platformVersion,appPackage,appActivity,udid")
    sys.exit(1)


# ==========================================================
# Step 3: Load Existing JSON
# ==========================================================
caps = {}

if os.path.exists(json_path):
    try:
        with open(json_path, "r") as file:
            caps = json.load(file)
    except json.JSONDecodeError:
        print("Warning: JSON corrupted. Creating new JSON.")
        caps = {}
    except Exception as e:
        print(f"Error reading JSON: {e}")
        sys.exit(1)


# ==========================================================
# Step 4: Update Capabilities
# ==========================================================
caps.update({

    "deviceName": deviceName,
    "udid": udid,
    "platformVersion": platformVersion,
    "platformName": "Android",

    "automationName": "UiAutomator2",

    "appPackage": appPackage,
    "appActivity": appActivity,

    "noReset": True,
    "autoGrantPermissions": False,

    "skipDeviceInitialization": True,
    "skipServerInstallation": True,

    "ignoreHiddenApiPolicyError": True,
    "disableWindowAnimation": True,

    "adbExecTimeout": 30000,
    "uiautomator2ServerLaunchTimeout": 30000,

    "enforceAppInstall": False,
    "newCommandTimeout": 3600
})


# ==========================================================
# Step 5: Save JSON
# ==========================================================
try:
    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    with open(json_path, "w") as file:
        json.dump(caps, file, indent=2)

    print("SUCCESS: Capabilities JSON updated.")

except Exception as e:
    print(f"Error writing JSON: {e}")
    sys.exit(1)


# ==========================================================
# Step 6: Return Success (for LabVIEW)
# ==========================================================
print("RESULT:PASS")
sys.exit(0)