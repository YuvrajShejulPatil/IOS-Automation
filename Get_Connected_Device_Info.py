import subprocess

def get_connected_devices():
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')[1:]
    devices = [line.split()[0] for line in lines if 'device' in line]
    return devices

for device in get_connected_devices():
    print(device)