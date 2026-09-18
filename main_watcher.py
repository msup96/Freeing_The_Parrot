# ============================================================
# FREEING THE PARROT
# MAIN WATCHER
# OCR -> NAVARASA ENGINE -> DATABASE
# ============================================================

import os
import re
import time
import json
import sqlite3
from datetime import datetime

import cv2
import pytesseract

from navarasa_engine import analyse_text


# ============================================================
# PATHS
# ============================================================

BASE_DIR = r"C:\freeing_the_parrot"

WATCH_DIR = os.path.join(BASE_DIR, "input_scans")
DB_FILE = os.path.join(BASE_DIR, "emotional_database.db")
SESSION_FILE = os.path.join(BASE_DIR, "db_session.json")
SCAN_STATUS_FILE = os.path.join(BASE_DIR, "scan_status.json")
TEMP_DIR = os.path.join(BASE_DIR, "ocr_temp")


# ============================================================
# LIVE INTERFACE STATUS
# ============================================================

def update_scan_status(
    status,
    progress,
    message,
    lines=None,
    result=None
):
    try:
        previous_lines = []

        if os.path.exists(SCAN_STATUS_FILE):
            try:
                with open(
                    SCAN_STATUS_FILE,
                    "r",
                    encoding="utf-8"
                ) as file:
                    previous = json.load(file)
                    previous_lines = previous.get("lines", [])
            except Exception:
                previous_lines = []

        new_lines = lines or []

        for new_line in new_lines:
            if new_line not in previous_lines:
                previous_lines.append(new_line)

        payload = {
            "status": status,
            "progress": progress,
            "message": message,
            "lines": previous_lines,
            "result": result or {}
        }

        with open(
            SCAN_STATUS_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                payload,
                file,
                indent=2,
                ensure_ascii=False
            )

    except Exception as exc:
        print(
            f"[STATUS WARNING] "
            f"Could not update interface status: {exc}"
        )


# ============================================================
# TESSERACT
# ============================================================

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
else:
    print("[WARNING] Tesseract executable not found at:")
    print(TESSERACT_PATH)
    print("[WARNING] Using Tesseract from PATH instead.")


# ============================================================
# SUPPORTED IMAGE TYPES
# ============================================================

SUPPORTED_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff"
)


# ============================================================
# OCR SETTINGS
# ============================================================

OCR_CONFIGS = [
    ("psm6", "--psm 6"),
    ("psm11", "--psm 11"),
]


# ============================================================
# DIRECTORY SETUP
# ============================================================

os.makedirs(WATCH_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


# ============================================================
# DISPLAY HELPERS
# ============================================================

def line(char="=", length=60):
    print(char * length)


def header(title):
    line("=")
    print(title)
    line("=")


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def remove_grid_lines(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        15
    )

    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (40, 1)
    )

    horizontal_lines = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        horizontal_kernel,
        iterations=1
    )

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, 40)
    )

    vertical_lines = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        vertical_kernel,
        iterations=1
    )

    grid_lines = cv2.bitwise_or(
        horizontal_lines,
        vertical_lines
    )

    cleaned = cv2.subtract(
        binary,
        grid_lines
    )

    cleaned = cv2.bitwise_not(cleaned)

    return cleaned


def create_ocr_variants(file_path):
    image = cv2.imread(file_path)

    if image is None:
        raise ValueError(
            f"Could not read image: {file_path}"
        )

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    grayscale = gray

    _, otsu = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    adaptive = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15
    )

    grid_removed = remove_grid_lines(image)

    return {
        "grayscale": grayscale,
        "otsu": otsu,
        "adaptive": adaptive,
        "grid_removed": grid_removed
    }


# ============================================================
# OCR QUALITY SCORING
# ============================================================

def score_ocr_text(text, confidence_values):
    if not text or not text.strip():
        return 0.0

    words = re.findall(
        r"[A-Za-z]+",
        text
    )

    if not words:
        return 0.0

    valid_confidences = [
        float(c)
        for c in confidence_values
        if str(c).strip() not in ("", "-1")
    ]

    confidence_score = (
        sum(valid_confidences)
        / len(valid_confidences)
        if valid_confidences
        else 0.0
    )

    word_score = min(
        len(words) * 2.0,
        30.0
    )

    fragments = sum(
        1
        for word in words
        if len(word) <= 1
    )

    fragment_penalty = fragments * 3.0

    score = (
        confidence_score
        + word_score
        - fragment_penalty
    )

    return round(
        max(score, 0.0),
        2
    )


# ============================================================
# RUN OCR
# ============================================================

def run_ocr(image, config):
    data = pytesseract.image_to_data(
        image,
        config=config,
        output_type=pytesseract.Output.DICT
    )

    pieces = []
    confidences = []

    for i, raw_word in enumerate(
        data["text"]
    ):
        word = raw_word.strip()

        if not word:
            continue

        pieces.append(word)

        try:
            confidence = float(
                data["conf"][i]
            )
            confidences.append(
                confidence
            )
        except (
            ValueError,
            TypeError
        ):
            pass

    text = " ".join(pieces)

    score = score_ocr_text(
        text,
        confidences
    )

    return (
        text,
        confidences,
        score
    )


# ============================================================
# OCR CLEANUP
# ============================================================

def clean_ocr_text(text):
    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    text = re.sub(
        r"(?<![A-Za-z])[|~`^]+(?![A-Za-z])",
        " ",
        text
    )

    text = text.replace(
        "â€œ",
        '"'
    ).replace(
        "â€",
        '"'
    ).replace(
        "â€™",
        "'"
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# OCR CORRECTION
# ============================================================

def conservative_ocr_correction(text):
    if not text:
        return ""

    corrections = {
        "absolutelu": "absolutely",
        "absolutelv": "absolutely",
        "beauriful": "beautiful",
        "woder": "wonder",
        "wond er": "wonder",
        "meeung": "meeting",
        "meetng": "meeting",
        "trav el": "travel",
    }

    words = text.split()
    corrected = []

    for word in words:
        key = word.lower()

        if key in corrections:
            replacement = corrections[key]

            if word.isupper():
                replacement = replacement.upper()
            elif word[:1].isupper():
                replacement = (
                    replacement[:1].upper()
                    + replacement[1:]
                )

            corrected.append(
                replacement
            )
        else:
            corrected.append(word)

    return " ".join(corrected)


# ============================================================
# OCR PIPELINE
# ============================================================

def extract_text(file_path):
    header("[OCR] Loading image")

    variants = create_ocr_variants(
        file_path
    )

    candidates = []

    print(
        "[OCR] Generating preprocessing variants..."
    )

    total_tests = (
        len(variants) *
        len(OCR_CONFIGS)
    )

    completed = 0

    for variant_name, image in variants.items():

        for config_name, config in OCR_CONFIGS:

            print(
                f"[OCR] Testing variant: "
                f"{variant_name} + {config_name}"
            )

            try:
                (
                    text,
                    confidences,
                    score
                ) = run_ocr(
                    image,
                    config
                )

                candidates.append({
                    "variant": variant_name,
                    "config": config_name,
                    "text": text,
                    "confidence": (
                        sum(confidences)
                        / len(confidences)
                        if confidences
                        else 0
                    ),
                    "score": score
                })

            except Exception as exc:
                print(
                    f"[OCR WARNING] "
                    f"{variant_name} + "
                    f"{config_name} failed: "
                    f"{exc}"
                )

            # ------------------------------------------------
            # LIVE OCR PROGRESS
            # This MUST remain inside both OCR loops.
            # ------------------------------------------------

            completed += 1

            progress = int(
                20 +
                (
                    completed /
                    max(total_tests, 1)
                ) * 45
            )

            update_scan_status(
                "scanning",
                progress,
                (
                    "[OCR] Testing variant: "
                    f"{variant_name} + {config_name}"
                ),
                [
                    "[OCR] Generating preprocessing variants...",
                    (
                        "[OCR] Testing variant: "
                        f"{variant_name} + {config_name}"
                    )
                ]
            )

    if not candidates:
        raise RuntimeError(
            "No OCR candidate was generated."
        )

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    best = candidates[0]

    print()
    print("[OCR CANDIDATES]")
    line("-")

    for candidate in candidates:
        print(
            f"{candidate['variant']} + "
            f"{candidate['config']} "
            f"→ score "
            f"{candidate['score']:.2f}"
        )

    print()
    print("[OCR] Selected:")
    print(
        f"       Variant = {best['variant']}"
    )
    print(
        f"       Config  = {best['config']}"
    )
    print(
        f"       Score   = {best['score']:.2f}"
    )

    candidate_lines = []

    for candidate in candidates:
        candidate_lines.append(
            f"{candidate['variant']} + "
            f"{candidate['config']} "
            f"→ score "
            f"{candidate['score']:.2f}"
        )

    update_scan_status(
        "ocr_selected",
        70,
        (
            "[OCR] Selected: "
            f"{best['variant']} + "
            f"{best['config']}"
        ),
        [
            "[OCR CANDIDATES]",
            *candidate_lines,
            "",
            "[OCR] Selected:",
            f"Variant = {best['variant']}",
            f"Config  = {best['config']}",
            f"Score   = {best['score']:.2f}"
        ]
    )

    raw_text = best["text"]

    corrected_text = clean_ocr_text(
        raw_text
    )

    corrected_text = conservative_ocr_correction(
        corrected_text
    )

    print()
    header("[OCR RESULT]")
    print(corrected_text)

    update_scan_status(
        "ocr_complete",
        76,
        "[OCR] Text extraction complete.",
        [
            "[OCR RESULT]",
            "============================================================",
            corrected_text
        ],
        {
            "ocr_text": corrected_text
        }
    )

    return (
        raw_text,
        corrected_text,
        {
            "selected_variant": best["variant"],
            "selected_config": best["config"],
            "ocr_score": best["score"],
            "candidate_count": len(candidates)
        }
    )


# ============================================================
# DATABASE
# ============================================================

def ensure_database():
    connection = sqlite3.connect(
        DB_FILE
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS emotional_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            filename TEXT,
            raw_ocr_text TEXT,
            corrected_text TEXT,
            primary_rasa TEXT,
            rasa_scores_json TEXT,
            emotional_evidence_json TEXT,
            emotional_words_json TEXT,
            analysis_quality TEXT,
            sentiment_json TEXT,
            full_analysis_json TEXT,
            ocr_metadata_json TEXT
        )
        """
    )

    connection.commit()

    cursor.execute(
        "PRAGMA table_info(emotional_scans)"
    )

    existing_columns = {
        row[1]
        for row in cursor.fetchall()
    }

    required_columns = {
        "timestamp": "TEXT",
        "filename": "TEXT",
        "raw_ocr_text": "TEXT",
        "corrected_text": "TEXT",
        "primary_rasa": "TEXT",
        "rasa_scores_json": "TEXT",
        "emotional_evidence_json": "TEXT",
        "emotional_words_json": "TEXT",
        "analysis_quality": "TEXT",
        "sentiment_json": "TEXT",
        "full_analysis_json": "TEXT",
        "ocr_metadata_json": "TEXT"
    }

    for column, column_type in required_columns.items():

        if column not in existing_columns:
            print(
                f"[DATABASE] Adding missing "
                f"column: {column}"
            )

            cursor.execute(
                f"""
                ALTER TABLE emotional_scans
                ADD COLUMN {column} {column_type}
                """
            )

    connection.commit()
    connection.close()

    print(
        f"[DATABASE] SQLite ready: {DB_FILE}"
    )


def save_analysis_to_database(
    file_path,
    raw_text,
    corrected_text,
    analysis,
    ocr_metadata
):
    ensure_database()

    timestamp = datetime.now().isoformat(
        timespec="seconds"
    )

    primary_rasa = analysis.get(
        "primary_rasa",
        "Shanta"
    )

    rasa_scores = analysis.get(
        "rasa_scores",
        {}
    )

    evidence = analysis.get(
        "evidence",
        {}
    )

    emotional_words = analysis.get(
        "emotional_words",
        []
    )

    analysis_quality = analysis.get(
        "analysis_quality",
        "unknown"
    )

    sentiment = analysis.get(
        "sentiment",
        {}
    )

    connection = sqlite3.connect(
        DB_FILE
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO emotional_scans (
            timestamp,
            filename,
            raw_ocr_text,
            corrected_text,
            primary_rasa,
            rasa_scores_json,
            emotional_evidence_json,
            emotional_words_json,
            analysis_quality,
            sentiment_json,
            full_analysis_json,
            ocr_metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp,
            os.path.basename(file_path),
            raw_text,
            corrected_text,
            primary_rasa,
            json.dumps(
                rasa_scores,
                ensure_ascii=False
            ),
            json.dumps(
                evidence,
                ensure_ascii=False
            ),
            json.dumps(
                emotional_words,
                ensure_ascii=False
            ),
            analysis_quality,
            json.dumps(
                sentiment,
                ensure_ascii=False
            ),
            json.dumps(
                analysis,
                ensure_ascii=False
            ),
            json.dumps(
                ocr_metadata,
                ensure_ascii=False
            )
        )
    )

    connection.commit()
    connection.close()

    print(
        "[DATABASE] Emotional scan "
        "permanently stored."
    )


# ============================================================
# SESSION JSON
# ============================================================

def update_session(
    file_path,
    analysis
):
    session = {
        "last_updated": datetime.now().isoformat(
            timespec="seconds"
        ),
        "last_file": os.path.basename(
            file_path
        ),
        "primary_rasa": analysis.get(
            "primary_rasa",
            "Shanta"
        ),
        "rasa_scores": analysis.get(
            "rasa_scores",
            {}
        ),
        "emotional_words": analysis.get(
            "emotional_words",
            []
        ),
        "analysis_quality": analysis.get(
            "analysis_quality",
            "unknown"
        ),
        "sentiment": analysis.get(
            "sentiment",
            {}
        )
    }

    with open(
        SESSION_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            session,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"[SESSION] Updated: "
        f"{SESSION_FILE}"
    )


# ============================================================
# PRINT NAVARASA PROFILE
# ============================================================

def print_analysis_profile(analysis):
    header("[NAVARASA PROFILE]")

    scores = analysis.get(
        "rasa_scores",
        {}
    )

    evidence = analysis.get(
        "evidence",
        {}
    )

    if not scores:
        print(
            "No emotional signals detected."
        )
    else:
        ordered = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True
        )

        for rasa, score in ordered:

            print()
            print(rasa)
            print(
                f"Score: {score}"
            )

            for item in evidence.get(
                rasa,
                []
            ):
                word = item.get(
                    "word",
                    ""
                )

                confidence = item.get(
                    "confidence",
                    0
                )

                intensity = item.get(
                    "intensity",
                    1
                )

                reason = item.get(
                    "reason",
                    ""
                )

                occurrences = item.get(
                    "occurrences"
                )

                occurrence_text = ""

                if occurrences is not None:
                    occurrence_text = (
                        f" | occurrences="
                        f"{occurrences}"
                    )

                print(
                    "  • "
                    f"{word} | "
                    f"confidence={confidence} | "
                    f"intensity={intensity} | "
                    f"{reason}"
                    f"{occurrence_text}"
                )

    print()
    print("PRIMARY RASA:")
    print(
        analysis.get(
            "primary_rasa",
            "Shanta"
        )
    )


# ============================================================
# PRINT SENTIMENT
# ============================================================

def print_sentiment(analysis):
    sentiment = analysis.get(
        "sentiment",
        {}
    )

    print()
    header("[SENTIMENT]")

    print(
        f"Positive : "
        f"{sentiment.get('positive', 0):.3f}"
    )

    print(
        f"Negative : "
        f"{sentiment.get('negative', 0):.3f}"
    )

    print(
        f"Neutral  : "
        f"{sentiment.get('neutral', 0):.3f}"
    )

    print(
        f"Compound : "
        f"{sentiment.get('compound', 0):.3f}"
    )


# ============================================================
# PROCESS ONE IMAGE
# ============================================================

def process_image(file_path):
    header("[ENGINE] NEW SCAN DETECTED")

    print(
        f"[FILE] {file_path}"
    )

    try:

        # ----------------------------------------------------
        # OCR
        # ----------------------------------------------------

        raw_text, corrected_text, ocr_metadata = (
            extract_text(file_path)
        )

        # ----------------------------------------------------
        # NAVARASA ENGINE
        # ----------------------------------------------------

        print()
        header("[NAVARASA ENGINE]")

        print(
            "Analysing emotional meaning..."
        )

        update_scan_status(
            "analysing",
            80,
            "[NAVARASA ENGINE] Analysing emotional meaning...",
            [
                "[NAVARASA ENGINE]",
                "Analysing emotional meaning..."
            ]
        )

        analysis = analyse_text(
            corrected_text
        )

        if not isinstance(
            analysis,
            dict
        ):
            raise TypeError(
                "navarasa_engine.analyse_text() "
                "did not return a dictionary."
            )

        # ----------------------------------------------------
        # PROFILE
        # ----------------------------------------------------

        print_analysis_profile(
            analysis
        )

        scores = analysis.get(
            "rasa_scores",
            {}
        )

        profile_lines = [
            "[NAVARASA PROFILE]",
            ""
        ]

        for rasa, score in sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True
        ):
            profile_lines.append(
                f"{rasa}"
            )

            profile_lines.append(
                f"Score: {score}"
            )

        profile_lines.append("")
        profile_lines.append(
            "PRIMARY RASA:"
        )
        profile_lines.append(
            analysis.get(
                "primary_rasa",
                "Shanta"
            )
        )

        update_scan_status(
            "navarasa_complete",
            84,
            (
                "[NAVARASA ENGINE] "
                "Analysis complete."
            ),
            profile_lines,
            {
                "primary_rasa": analysis.get(
                    "primary_rasa",
                    "Shanta"
                ),
                "rasa_scores": scores
            }
        )

        # ----------------------------------------------------
        # SENTIMENT
        # ----------------------------------------------------

        print_sentiment(
            analysis
        )

        sentiment = analysis.get(
            "sentiment",
            {}
        )

        update_scan_status(
            "sentiment_complete",
            87,
            "[SENTIMENT] Analysis complete.",
            [
                "[SENTIMENT]",
                f"Positive : {sentiment.get('positive', 0):.3f}",
                f"Negative : {sentiment.get('negative', 0):.3f}",
                f"Neutral  : {sentiment.get('neutral', 0):.3f}",
                f"Compound : {sentiment.get('compound', 0):.3f}"
            ]
        )

        # ----------------------------------------------------
        # QUALITY
        # ----------------------------------------------------

        print()
        header("[ANALYSIS QUALITY]")

        print(
            analysis.get(
                "analysis_quality",
                "unknown"
            )
        )

        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        save_analysis_to_database(
            file_path,
            raw_text,
            corrected_text,
            analysis,
            ocr_metadata
        )

        # ----------------------------------------------------
        # SESSION
        # ----------------------------------------------------

        update_session(
            file_path,
            analysis
        )

        update_scan_status(
            "storing",
            94,
            "[DATABASE] Emotional scan permanently stored.",
            [
                "[DATABASE] SQLite ready.",
                "[DATABASE] Emotional scan permanently stored.",
                "[SESSION] Session updated."
            ]
        )

        update_scan_status(
            "complete",
            100,
            "[ENGINE] SCAN COMPLETE",
            [
                "[ENGINE] SCAN COMPLETE",
                (
                    "[ENGINE] PRIMARY RASA → "
                    f"{analysis.get('primary_rasa', 'Shanta')}"
                )
            ],
            {
                "primary_rasa": analysis.get(
                    "primary_rasa",
                    "Shanta"
                ),
                "rasa_scores": analysis.get(
                    "rasa_scores",
                    {}
                ),
                "emotional_words": analysis.get(
                    "emotional_words",
                    []
                ),
                "analysis_quality": analysis.get(
                    "analysis_quality",
                    "unknown"
                ),
                "sentiment": analysis.get(
                    "sentiment",
                    {}
                )
            }
        )

        # ----------------------------------------------------
        # RAW JSON
        # ----------------------------------------------------

        print()
        header("[RAW JSON]")

        print(
            json.dumps(
                analysis,
                indent=2,
                ensure_ascii=False
            )
        )

        # ----------------------------------------------------
        # COMPLETE
        # ----------------------------------------------------

        print()
        line("=")
        print(
            "[ENGINE] SCAN COMPLETE"
        )
        print(
            "[ENGINE] PRIMARY RASA → "
            f"{analysis.get('primary_rasa', 'Shanta')}"
        )
        line("=")

    except Exception as exc:

        print()
        header("[ENGINE ERROR]")

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print()
        print(
            "[ENGINE] Scan was NOT written "
            "as a successful emotional scan."
        )

        update_scan_status(
            "error",
            0,
            f"[ENGINE ERROR] {type(exc).__name__}: {exc}",
            [
                "[ENGINE ERROR]",
                f"{type(exc).__name__}: {exc}",
                "",
                "[ENGINE] Scan was NOT written "
                "as a successful emotional scan."
            ]
        )


# ============================================================
# FILE STABILITY CHECK
# ============================================================

def wait_until_file_is_ready(
    file_path,
    checks=3,
    delay=0.5
):
    previous_size = -1
    stable_count = 0

    for _ in range(20):

        if not os.path.exists(
            file_path
        ):
            return False

        try:
            current_size = os.path.getsize(
                file_path
            )
        except OSError:
            time.sleep(delay)
            continue

        if current_size == previous_size:

            stable_count += 1

            if stable_count >= checks:
                return True

        else:

            stable_count = 0
            previous_size = current_size

        time.sleep(delay)

    return False


# ============================================================
# WATCHER
# ============================================================

def main():

    header(
        "🦜 FREEING THE PARROT\n"
        "EMOTIONAL SCAN ENGINE"
    )

    print(
        "[WATCHDOG] Monitoring:"
    )

    print(
        f"           {WATCH_DIR}"
    )

    print(
        "[DATABASE]"
    )

    print(
        f"           {DB_FILE}"
    )

    print(
        "[SESSION]"
    )

    print(
        f"           {SESSION_FILE}"
    )

    line("=")

    ensure_database()

    processed_files = set()

    try:
        processed_files = {
            filename
            for filename in os.listdir(
                WATCH_DIR
            )
            if filename.lower().endswith(
                SUPPORTED_EXTENSIONS
            )
        }
    except OSError:
        pass

    print(
        f"[WATCHDOG] Existing scans ignored: "
        f"{len(processed_files)}"
    )

    print(
        "[WATCHDOG] Waiting for a NEW scan..."
    )

    line("=")

    try:

        while True:

            try:

                current_files = {
                    filename
                    for filename in os.listdir(
                        WATCH_DIR
                    )
                    if filename.lower().endswith(
                        SUPPORTED_EXTENSIONS
                    )
                }

            except OSError as exc:

                print(
                    f"[WATCHDOG WARNING] "
                    f"Could not read folder: {exc}"
                )

                time.sleep(2)
                continue

            new_files = (
                current_files
                - processed_files
            )

            for filename in sorted(
                new_files
            ):

                full_path = os.path.join(
                    WATCH_DIR,
                    filename
                )

                print()
                print(
                    f"[WATCHDOG] New file detected: "
                    f"{filename}"
                )

                update_scan_status(
                    "detected",
                    5,
                    f"[WATCHDOG] New file detected: {filename}",
                    [
                        "[WATCHDOG] NEW DOCUMENT DETECTED",
                        f"[FILE] {filename}"
                    ]
                )

                if not wait_until_file_is_ready(
                    full_path
                ):

                    print(
                        "[WATCHDOG] File did not "
                        "become stable."
                    )

                    processed_files.add(
                        filename
                    )

                    continue

                time.sleep(0.5)

                process_image(
                    full_path
                )

                processed_files.add(
                    filename
                )

            time.sleep(1)

    except KeyboardInterrupt:

        print()
        print(
            "[WATCHDOG] Stopped by user."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()