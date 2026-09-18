from pywinauto import Desktop
import time

print("Looking for IJ Scan Utility...")

for window in Desktop(backend="uia").windows():
    try:
        title = window.window_text()
        if title:
            print(f"WINDOW: {title}")
    except Exception:
        pass

print("\nWaiting for IJ Scan Utility...")
time.sleep(2)

for window in Desktop(backend="uia").windows():
    try:
        title = window.window_text()

        if "IJ Scan Utility" in title:
            print("\nFOUND:")
            print(title)
            print("\nCONTROLS:")
            window.print_control_identifiers()

    except Exception:
        pass