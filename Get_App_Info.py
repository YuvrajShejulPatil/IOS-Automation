import subprocess
import re
import csv
from datetime import datetime

def run_adb_command(command):
    result = subprocess.run(
        ["adb"] + command.split(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",     # ✅ Proper encoding
        errors="replace"      # ✅ Avoid crash on bad characters
    )
    return result.stdout.strip()


def get_app_label(package):
    output = run_adb_command(f"shell dumpsys package {package}")
    match = re.search(r'application-label:\s*(.+)', output)
    return match.group(1).strip() if match else "Unknown App"

def get_user_installed_apps():
    print("[*] Getting user-installed apps...")
    raw_output = run_adb_command("shell pm list packages -3 -f")
    apps = []

    for line in raw_output.splitlines():
        try:
            line = line.replace("package:", "")
            parts = line.split("=")
            apk_path = parts[0].strip()
            package = parts[-1].strip()
            app_name = get_app_label(package)
            apps.append({
                "App Name": app_name,
                "Package": package,
                "APK Path": apk_path,
                "Data Dir": f"/data/data/{package}"
            })
        except Exception:
            continue

    return apps

def export_to_csv(apps):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mobile_app_data_{timestamp}.csv"

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["App Name", "Package", "APK Path", "Data Dir"])
        writer.writeheader()
        writer.writerows(apps)

    print(f"\n✅ Exported to: {filename}\n")

# --- MAIN EXECUTION ---
devices_output = run_adb_command("devices")
if "device" not in devices_output.splitlines()[1]:
    print("[!] No device connected.")
    exit()

apps = get_user_installed_apps()
export_to_csv(apps)
