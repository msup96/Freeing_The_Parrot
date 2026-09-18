import subprocess
import time
import pyautogui

SCAN_UTILITY = r"C:\Program Files (x86)\Canon\IJ Scan Utility\SCANUTILITY.exe"

# Current working Scan button coordinates
SCAN_X = 854
SCAN_Y = 509


def trigger_scan():
    print("[SCAN] Opening IJ Scan Utility...")

    subprocess.Popen([SCAN_UTILITY])

    time.sleep(3)

    print("[SCAN] Moving to Scan button...")
    pyautogui.moveTo(SCAN_X, SCAN_Y, duration=0.5)

    time.sleep(1)

    print(f"[SCAN] Clicking Scan at X={SCAN_X}, Y={SCAN_Y}...")
    pyautogui.click()

    print("[SCAN] Scan command sent.")

    return True


if __name__ == "__main__":
    trigger_scan()