# ============================================================
# FREEING THE PARROT
# THERMAL PRINTER MODULE
# ============================================================

import datetime
import textwrap
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(r"C:\freeing_the_parrot")

RECEIPT_DIR = BASE_DIR / "receipts"

# Leave as None for the first test.
# We will set the exact Windows printer name after
# confirming it with Get-Printer.
PRINTER_NAME = "POS58 Printer"

# 58 mm thermal printers usually work well around
# 32 characters per line.
LINE_WIDTH = 32


# ============================================================
# RECEIPT HELPERS
# ============================================================

def separator(char="-"):
    return char * LINE_WIDTH


def heavy_separator():
    return "=" * LINE_WIDTH


def wrap_text(text):
    """
    Wrap text to the physical width of the thermal printer.

    Existing line breaks are preserved.
    """

    if text is None:
        return []

    text = str(text)

    lines = []

    for original_line in text.splitlines():

        if not original_line.strip():
            lines.append("")
            continue

        wrapped = textwrap.wrap(
            original_line,
            width=LINE_WIDTH,
            break_long_words=True,
            break_on_hyphens=False
        )

        if wrapped:
            lines.extend(wrapped)
        else:
            lines.append("")

    return lines


def add_labelled_message(lines, speaker, text):

    lines.append("")
    lines.append(speaker)
    lines.append(separator())

    lines.extend(
        wrap_text(text)
    )


# ============================================================
# STATIC TEST RECEIPT
# ============================================================

def build_test_receipt():

    now = datetime.datetime.now().strftime(
        "%d %b %Y · %H:%M"
    )

    lines = []

    lines.append(
        heavy_separator()
    )

    lines.append(
        "FREEING THE PARROT"
    )

    lines.append(
        "SESSION TRANSCRIPT"
    )

    lines.append(
        heavy_separator()
    )

    lines.append("")

    lines.append(
        now
    )

    lines.append("")

    # --------------------------------------------------------
    # TEST CONVERSATION
    # --------------------------------------------------------

    add_labelled_message(
        lines,
        "USER:",
        "I don't know. I'm tired."
    )

    add_labelled_message(
        lines,
        "SYSTEM:",
        "You appear to be avoiding the question."
    )

    add_labelled_message(
        lines,
        "USER:",
        "I'm literally just tired."
    )

    add_labelled_message(
        lines,
        "SYSTEM:",
        "Interesting."
    )

    add_labelled_message(
        lines,
        "USER:",
        "Why are you being weird?"
    )

    add_labelled_message(
        lines,
        "SYSTEM:",
        "I don't remember being weird."
    )

    add_labelled_message(
        lines,
        "USER:",
        "You just said—"
    )

    add_labelled_message(
        lines,
        "SYSTEM:",
        "I said what?"
    )

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    lines.append("")
    lines.append(
        separator()
    )
    lines.append(
        "EMOTIONAL ANALYSIS"
    )
    lines.append(
        separator()
    )

    lines.append("")
    lines.append("PRIMARY RASA")
    lines.append("Shringara")

    lines.append("")
    lines.append("RASA SCORES")
    lines.append("Shringara       1.00")
    lines.append("Adbhuta         0.50")

    lines.append("")
    lines.append("SENTIMENT")
    lines.append("Positive        0.293")
    lines.append("Neutral         0.707")
    lines.append("Negative        0.000")
    lines.append("Compound        0.995")

    # --------------------------------------------------------
    # DISCLAIMER
    # --------------------------------------------------------

    lines.append("")
    lines.append(
        separator()
    )

    lines.append("")

    lines.extend(
        wrap_text(
            '"It is better to be Homo Sapiens '
            'than Robo Sapiens."'
        )
    )

    lines.append("")

    lines.extend(
        wrap_text(
            "The machine can reflect. "
            "You still have to think."
        )
    )

    lines.append("")

    lines.append(
        heavy_separator()
    )

    lines.append(
        "END OF SESSION"
    )

    lines.append(
        heavy_separator()
    )

    # Add a little paper feed at the end.
    lines.append("")
    lines.append("")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# SAVE RECEIPT
# ============================================================

def save_receipt(receipt_text):

    RECEIPT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = datetime.datetime.now().strftime(
        "test_receipt_%Y%m%d_%H%M%S.txt"
    )

    path = RECEIPT_DIR / filename

    path.write_text(
        receipt_text,
        encoding="utf-8"
    )

    return path


# ============================================================
# WINDOWS THERMAL PRINTING
# ============================================================

def print_receipt(receipt_text):

    if PRINTER_NAME is None:
        raise RuntimeError(
            "PRINTER_NAME is not configured yet."
        )

    try:

        import win32print

    except ImportError:

        raise RuntimeError(
            "pywin32 is not installed.\n\n"
            "Run:\n"
            "python -m pip install pywin32"
        )

    printer = win32print.OpenPrinter(
        PRINTER_NAME
    )

    try:

        win32print.StartDocPrinter(
            printer,
            1,
            (
                "Freeing the Parrot",
                None,
                "RAW"
            )
        )

        win32print.StartPagePrinter(
            printer
        )

        win32print.WritePrinter(
            printer,
            receipt_text.encode(
                "cp437",
                errors="replace"
            )
        )

        win32print.EndPagePrinter(
            printer
        )

        win32print.EndDocPrinter(
            printer
        )

    finally:

        win32print.ClosePrinter(
            printer
        )


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 60)
    print("FREEING THE PARROT")
    print("THERMAL PRINTER TEST")
    print("=" * 60)

    receipt = build_test_receipt()

    path = save_receipt(
        receipt
    )

    print()
    print("[PRINTER TEST] Layout generated.")
    print(
        f"[PRINTER TEST] Saved preview:"
    )
    print(
        f"                {path}"
    )

    print()
    print("[PRINTER TEST] Preview:")
    print("-" * 60)
    print(receipt)
    print("-" * 60)

    if PRINTER_NAME is None:

        print()
        print(
            "[PRINTER TEST] PHYSICAL PRINT NOT YET ENABLED."
        )
        print(
            "[PRINTER TEST] Configure PRINTER_NAME after"
        )
        print(
            "[PRINTER TEST] confirming the Windows printer name."
        )

        return

    print()
    print(
        f"[PRINTER] Sending to: {PRINTER_NAME}"
    )

    print_receipt(
        receipt
    )

    print(
        "[PRINTER] Print job sent successfully."
    )


if __name__ == "__main__":
    main()