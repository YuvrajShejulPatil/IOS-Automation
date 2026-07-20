import subprocess
import re

def get_resolution():
    try:
        result = subprocess.check_output(['adb', 'shell', 'wm', 'size'], encoding='utf-8')
        match = re.search(r'Physical size:\s*(\d+)x(\d+)', result)
        if match:
            width, height = match.groups()
            return f"{width}x{height}"  # Return as single string
        else:
            return "ERROR: Unable to parse resolution"
    except Exception as e:
        return f"ERROR: {str(e)}"
