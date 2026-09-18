import time
import pyautogui

print("Opening Canon IJ Scan Utility...")

pyautogui.hotkey("win", "r")
time.sleep(1)

pyautogui.write(
    r"C:\Program Files (x86)\Canon\IJ Scan Utility\SCANUTILITY.exe",
    interval=0.01
)

pyautogui.press("enter")

print("Waiting for IJ Scan Utility...")
time.sleep(5)

print("\nMove your mouse over the SCAN button.")
print("The mouse coordinates will be displayed every second.")
print("Press Ctrl+C when you have the coordinates.")
print()

try:
    while True:
        x, y = pyautogui.position()
        print(f"Mouse position: X={x}, Y={y}")
        time.sleep(1)

except KeyboardInterrupt:
    print("\nInspection stopped.")