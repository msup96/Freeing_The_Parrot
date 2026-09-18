
from pathlib import Path
import shutil

TARGET = Path(r"C:\freeing_the_parrot\scripts\interface_server.py")
BACKUP = TARGET.with_name("interface_server_before_print_realtime.py")

if not TARGET.exists():
    raise SystemExit(f"ERROR: File not found: {TARGET}")

source = TARGET.read_text(encoding="utf-8")

# 1. BACKUP
shutil.copy2(TARGET, BACKUP)

# 2. CONFIG
old = 'SCAN_STATUS_FILE = BASE_DIR / "scan_status.json"\nINPUT_SCAN_DIR = BASE_DIR / "input_scans"'
new = 'SCAN_STATUS_FILE = BASE_DIR / "scan_status.json"\nPRINT_STATUS_FILE = BASE_DIR / "print_status.json"\nINPUT_SCAN_DIR = BASE_DIR / "input_scans"'

if old not in source:
    raise SystemExit("STOP: CONFIG anchor not found. No changes made.")
source = source.replace(old, new, 1)

# 3. BACKEND PRINT ENGINE
anchor = '''# ============================================================
# ANALYSIS
# ============================================================

def analyse_message(text):'''

block = r'''# ============================================================
# REALTIME CONVERSATION PRINTER
# ============================================================

PRINT_PRINTER_NAME = "POS58"


def write_print_status(status, progress, message, lines=None, result=None):
    payload = {
        "status": status,
        "progress": int(progress),
        "message": message,
        "lines": lines or [],
        "result": result or {},
    }

    PRINT_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_file = PRINT_STATUS_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    temp_file.replace(PRINT_STATUS_FILE)


def build_conversation_receipt(session):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages = session.get("messages", [])

    lines = [
        "================================",
        "       FREEING THE PARROT",
        "     -- SESSION TRANSCRIPT --",
        "================================",
        f"TIME: {timestamp}",
        "",
        "[CONVERSATION]",
        "--------------------------------",
        "SYSTEM:",
        "SYSTEM READY.",
        "",
        "Tell me what you came here wanting to know.",
        "",
        "The machine will analyse the emotional signal,",
        "but it will not predict your future,",
        "diagnose you,",
        "or manufacture validation.",
        "",
    ]

    for message in messages:
        role = str(message.get("role", "system")).upper()
        text = str(message.get("text", ""))

        lines.append(f"{role}:")
        lines.extend(text.splitlines() or [""])
        lines.append("")

    lines.extend([
        "--------------------------------",
        "",
        '"It is better to be Homo Sapiens',
        ' than Robo Sapiens."',
        "",
        "The machine can reflect.",
        "You still have to think.",
        "",
        "================================",
        "          END OF SESSION",
        "================================",
        "",
        "",
    ])

    return "\n".join(lines)


def run_conversation_print(session):
    lines = []

    def log(progress, message):
        lines.append(message)
        write_print_status(
            "printing",
            progress,
            message,
            lines=list(lines),
        )
        print(message, flush=True)

    try:
        log(5, "[PRINT ENGINE] SESSION RECEIVED")

        messages = session.get("messages", [])

        log(
            15,
            f"[PRINT ENGINE] CONVERSATION MESSAGES: {len(messages)}"
        )

        receipt_text = build_conversation_receipt(session)

        log(30, "[PRINT ENGINE] BUILDING SESSION TRANSCRIPT")

        receipt_dir = BASE_DIR / "receipts"
        receipt_dir.mkdir(parents=True, exist_ok=True)

        receipt_path = receipt_dir / datetime.datetime.now().strftime(
            "conversation_%Y%m%d_%H%M%S.txt"
        )

        receipt_path.write_text(
            receipt_text,
            encoding="utf-8"
        )

        log(45, "[PRINT ENGINE] TRANSCRIPT READY")
        log(55, f"[PRINT ENGINE] SENDING TO {PRINT_PRINTER_NAME}")

        import win32print

        printer = win32print.OpenPrinter(PRINT_PRINTER_NAME)

        try:
            win32print.StartDocPrinter(
                printer,
                1,
                ("Freeing the Parrot - Conversation", None, "RAW")
            )

            win32print.StartPagePrinter(printer)

            win32print.WritePrinter(
                printer,
                receipt_text.encode("cp437", errors="replace")
            )

            log(85, "[PRINT ENGINE] DATA TRANSMITTED")

            win32print.EndPagePrinter(printer)
            win32print.EndDocPrinter(printer)

        finally:
            win32print.ClosePrinter(printer)

        log(100, "[PRINT ENGINE] PRINT COMPLETE")

        write_print_status(
            "complete",
            100,
            "[PRINT ENGINE] PRINT COMPLETE",
            lines=list(lines),
            result={
                "printer": PRINT_PRINTER_NAME,
                "receipt": str(receipt_path),
                "messages": len(messages),
            },
        )

    except Exception as exc:
        error_line = f"[PRINT ERROR] {exc}"
        lines.append(error_line)
        print(error_line, flush=True)

        write_print_status(
            "error",
            0,
            error_line,
            lines=list(lines),
            result={},
        )


# ============================================================
# ANALYSIS
# ============================================================

def analyse_message(text):'''

if anchor not in source:
    raise SystemExit("STOP: ANALYSIS anchor not found. No changes made.")
source = source.replace(anchor, block, 1)

# 4. HTML PRINT PANEL
anchor = '''</div>

<div class="grid">

<div class="panel chat">'''

block = '''</div>

<div class="panel" id="print-panel">
    <h2>[ PRINT ENGINE ]</h2>

    <p>
        PRINT THE ENTIRE CONVERSATION.
    </p>

    <button
        id="print-button"
        onclick="printConversation()"
    >
        PRINT CONVERSATION
    </button>

    <div class="progress-container">
        <div
            id="print-progress"
            class="progress-bar"
        ></div>
    </div>

    <div
        id="print-progress-text"
        class="scan-progress-text"
    >
        0%
    </div>

    <div
        id="print-log"
        class="scan-log"
    >
        SYSTEM READY. PRINT ENGINE STANDBY.
    </div>
</div>

<div class="grid">

<div class="panel chat">'''

if anchor not in source:
    raise SystemExit("STOP: HTML insertion anchor not found. No changes made.")
source = source.replace(anchor, block, 1)

# 5. JAVASCRIPT PRINT POLLING
anchor = '''const inputBox =
    document.getElementById("input");'''

block = r'''let printPollingTimer = null;
let printLogLines = [];


function resetPrintInterface() {
    printLogLines = [];

    const progress = document.getElementById("print-progress");
    const progressText = document.getElementById("print-progress-text");
    const log = document.getElementById("print-log");

    if (progress) progress.style.width = "0%";
    if (progressText) progressText.textContent = "0%";
    if (log) log.textContent = "SYSTEM READY. PRINT ENGINE STANDBY.";
}


function appendPrintLines(incomingLines) {
    const incoming = Array.isArray(incomingLines)
        ? incomingLines.map(line => String(line))
        : [];

    if (!incoming.length) return;

    let overlap = 0;
    const maxOverlap = Math.min(
        printLogLines.length,
        incoming.length
    );

    for (let size = maxOverlap; size > 0; size--) {
        const tail = printLogLines.slice(-size);
        const head = incoming.slice(0, size);

        if (tail.every((value, index) => value === head[index])) {
            overlap = size;
            break;
        }
    }

    const additions = incoming.slice(overlap);

    if (additions.length) {
        printLogLines.push(...additions);
    }

    const log = document.getElementById("print-log");

    if (log) {
        log.textContent = printLogLines.join("\n");
        log.scrollTop = log.scrollHeight;
    }
}


function startPrintPolling() {
    stopPrintPolling();
    printPollingTimer = setInterval(pollPrintStatus, 250);
    pollPrintStatus();
}


function stopPrintPolling() {
    if (printPollingTimer !== null) {
        clearInterval(printPollingTimer);
        printPollingTimer = null;
    }
}


async function pollPrintStatus() {
    try {
        const response = await fetch(
            "/api/print-status",
            { cache: "no-store" }
        );

        const data = await response.json();
        updatePrintInterface(data);

    } catch (error) {
        console.error("Print status error:", error);
    }
}


function updatePrintInterface(data) {
    const progress = document.getElementById("print-progress");
    const progressText = document.getElementById("print-progress-text");
    const button = document.getElementById("print-button");

    const status = data.status || "idle";
    const progressValue = Number(data.progress || 0);

    if (progress) {
        progress.style.width = `${progressValue}%`;
    }

    if (progressText) {
        progressText.textContent = `${progressValue}%`;
    }

    appendPrintLines(data.lines);

    if (status === "complete" || status === "error") {
        if (button) {
            button.disabled = false;
            button.textContent = "PRINT CONVERSATION";
        }

        stopPrintPolling();
        return;
    }

    if (button && status !== "idle") {
        button.disabled = true;
        button.textContent = "PRINTING...";
    }
}


async function printConversation() {
    const button = document.getElementById("print-button");

    try {
        if (!sessionId) {
            throw new Error("No active conversation session.");
        }

        await fetch(
            "/api/print-reset",
            {
                method: "POST",
                cache: "no-store"
            }
        );

        resetPrintInterface();
        startPrintPolling();

        if (button) {
            button.disabled = true;
            button.textContent = "PRINTING...";
        }

        const response = await fetch(
            "/api/print-conversation",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: sessionId
                })
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(
                data.error || "Could not start printing."
            );
        }

    } catch (error) {
        console.error("[PRINT] Connection error:", error);

        const log = document.getElementById("print-log");

        if (log) {
            log.textContent = "[PRINT ERROR]\n" + error.message;
        }

        stopPrintPolling();

        if (button) {
            button.disabled = false;
            button.textContent = "PRINT CONVERSATION";
        }
    }
}


const inputBox =
    document.getElementById("input");'''

if anchor not in source:
    raise SystemExit("STOP: JavaScript anchor not found. No changes made.")
source = source.replace(anchor, block, 1)

# 6. PRINT ROUTES
anchor = '''@app.route(
    "/api/scan-upload",
    methods=["POST"]
)'''

block = r'''@app.route("/api/print-status")
def print_status():
    if not PRINT_STATUS_FILE.exists():
        return jsonify({
            "status": "idle",
            "progress": 0,
            "message": "SYSTEM READY. PRINT ENGINE STANDBY.",
            "lines": []
        })

    try:
        with open(
            PRINT_STATUS_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return jsonify(json.load(file))

    except Exception as exc:
        return jsonify({
            "status": "error",
            "progress": 0,
            "message": str(exc),
            "lines": []
        })


@app.route("/api/print-reset", methods=["POST"])
def print_reset():
    try:
        write_print_status(
            "idle",
            0,
            "SYSTEM READY. PRINT ENGINE STANDBY.",
            lines=[
                "SYSTEM READY. PRINT ENGINE STANDBY."
            ],
        )

        return jsonify({"ok": True})

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 500


@app.route(
    "/api/print-conversation",
    methods=["POST"]
)
def print_conversation():
    data = request.get_json(silent=True) or {}

    session_id = data.get("session_id")
    session = SESSIONS.get(session_id)

    if session is None:
        return jsonify({
            "success": False,
            "error": "Session not found."
        }), 404

    if not session.get("messages"):
        return jsonify({
            "success": False,
            "error": "There is no conversation to print."
        }), 400

    import threading

    thread = threading.Thread(
        target=run_conversation_print,
        args=(session,),
        daemon=True,
    )

    thread.start()

    return jsonify({
        "success": True,
        "message": "Conversation print started."
    })


@app.route(
    "/api/scan-upload",
    methods=["POST"]
)'''

if anchor not in source:
    raise SystemExit("STOP: ROUTE anchor not found. No changes made.")
source = source.replace(anchor, block, 1)

# 7. WRITE
TARGET.write_text(source, encoding="utf-8")

print("PATCHED SUCCESSFULLY")
print(f"Target : {TARGET}")
print(f"Backup : {BACKUP}")
print("")
print("NEXT COMMAND:")
print(r'python -m py_compile "C:\freeing_the_parrot\scripts\interface_server.py"')
