import subprocess
from time import sleep

DEVICE_ID = None
PASSWORD = "oelinux123"


# -------------------------------
# Step 1: Get ADB devices
# -------------------------------
def adb_devices():
    try:
        print("Fetching ADB devices...")

        result = subprocess.run(
            "adb devices",
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )

        sleep(1)

        if not result.stdout:
            print("No output from adb devices")
            return None

        print("ADB Devices:\n", result.stdout)
        return result.stdout

    except subprocess.CalledProcessError as e:
        print("Failed to execute adb devices:", e)
        return None
    except Exception as e:
        print("Unexpected error in adb_devices:", e)
        return None


# -------------------------------
# Step 2: Get nth device safely
# -------------------------------
def get_nth_device(n=2):
    try:
        output = adb_devices()

        if not output:
            print("No device output received")
            return None

        lines = output.strip().split("\n")[1:]  # Skip header

        devices = []
        for line in lines:
            try:
                if line.strip() and line.strip().endswith("device"):
                    devices.append(line.split()[0])
            except Exception:
                continue  # skip malformed line

        if len(devices) >= n:
            return devices[n - 1]

        print(f"Less than {n} devices found")
        return None

    except Exception as e:
        print("Error in get_nth_device:", e)
        return None


# -------------------------------
# Step 3: Enable root
# -------------------------------
def adb_root():
    global DEVICE_ID
    try:
        print("Trying adb root...")

        subprocess.run(
            f"adb -s {DEVICE_ID} root",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        sleep(2)
        print("ADB root enabled")
        return True

    except subprocess.CalledProcessError:
        print("adb root not supported, will use su")
        return False

    except Exception as e:
        print("Error in adb_root:", e)
        return False


# -------------------------------
# Step 4: Run root command safely
# -------------------------------
def run_root_command(command):
    global DEVICE_ID

    try:
        if not DEVICE_ID:
            print("DEVICE_ID not set")
            return ""

        full_cmd = f'adb -s {DEVICE_ID} shell "echo {PASSWORD} | su -c \'{command}\'"'

        output = subprocess.check_output(
            full_cmd,
            shell=True,
            stderr=subprocess.DEVNULL
        ).decode(errors="ignore")

        return output if output else ""

    except subprocess.CalledProcessError as e:
        print("Command execution failed:", e)
        return ""
    except Exception as e:
        print("Unexpected error in run_root_command:", e)
        return ""


# -------------------------------
# Step 5: CPU Utilisation Logic
# -------------------------------
def calculateCPUUtilisation():
    global DEVICE_ID

    try:
        counter=0
        # Get second device
        DEVICE_ID = get_nth_device(2)

        if not DEVICE_ID:
            print("No valid second device found. Exiting...")
            return

        print("Using Device:", DEVICE_ID)

        adb_root()

        # IMPORTANT: use batch mode
        sample_output = run_root_command("top -bn1")
        
        # print(sample_output)

        if not sample_output:
            print("No output from top command")
            return
        lines = [line.strip() for line in sample_output.splitlines() if line.strip()]

        process_lines = []
        start_collecting = False

        for line in lines:
            
            if "PID" in line:
                start_collecting = True
                continue  # skip header if you don’t want it

            if start_collecting and counter<=10:
                process_lines.append(line)
                counter+=1

        # # filtered_lines = [line for line in process_lines if "{top}" not in line]

        filtered_lines = [
            line for line in process_lines
            if "{top}" not in line and "su -c" not in line
        ]
        filtered_string = "\n".join(filtered_lines)

        # print(filtered_string) # String


        # cpu_util = []
        # feature = []

        # for line in filtered_lines:
        #     try:
        #         parts = line.split()

        #         if len(parts) < 2:
        #             continue

        #         # Extract all float numbers from line
        #         floats = []
        #         for item in parts:
        #             try:
        #                 floats.append(float(item))
        #             except ValueError:
        #                 continue

        #         if not floats:
        #             continue

        #         cpu = floats[-1]   # LAST float is CPU
        #         cmd = parts[-1]    # Last column is command

        #         cpu_util.append(cpu)
        #         feature.append(cmd)

        #     except Exception:
        #         continue
        
        return filtered_string
        
        


    except Exception as e:
        print("Critical failure in calculateCPUUtilisation:", e)


# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    try:
        print(calculateCPUUtilisation())
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print("Fatal error:", e)