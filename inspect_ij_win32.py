from pywinauto import Desktop
import time

print("Looking for Canon IJ Scan Utility using Win32 backend...")

time.sleep(2)

for window in Desktop(backend="win32").windows():
    try:
        title = window.window_text()

        if "Canon IJ Scan Utility" in title:
            print("\nFOUND:")
            print(title)

            print("\nWINDOW HANDLE:")
            print(window.handle)

            print("\nCONTROLS:")
            window.print_control_identifiers()

    except Exception as e:
        print("Error:", e)