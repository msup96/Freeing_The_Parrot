# FREEING THE PARROT

### The machine doesn't know you. It just knows how to sound like it does.

Freeing the Parrot is an interactive physical-digital installation that explores why AI can feel emotionally responsive even when what happens underneath is pattern recognition, classification and programmed response.

The project asks:

> What happens when the feeling of being heard becomes easier to find in a machine than in another human being?

The GitHub version is a locally runnable prototype connecting handwritten input, a scanned image, OCR, a Navarasa-based emotional classification engine, a conversational interface and a digitally generated Mirror Report.


---

# 1. WHAT THE GITHUB VERSION DOES

The current GitHub version follows this complete interaction:

    HANDWRITTEN INPUT
            ↓
    SCAN USING ANY SCANNER APP
            ↓
    SAVE AS PNG / JPG / JPEG
            ↓
       IMAGE UPLOAD
            ↓
            OCR
            ↓
      NAVARASA ANALYSIS
            ↓
       PARROT SESSION
            ↓
        I AM DONE!
            ↓
    DIGITAL MIRROR REPORT


The participant writes something personal on paper.

The note is scanned using any scanner app or scanning software. The resulting image is saved as PNG, JPG or JPEG and uploaded through the Freeing the Parrot interface.

The uploaded image is processed by `main_watcher.py`, which performs OCR and passes the extracted text to the Navarasa engine.

The resulting classification influences the Parrot's programmed behaviour during the conversation.

When the participant chooses `I AM DONE!`, the complete session is turned into a digital Mirror Report that visually resembles a scanned or printed receipt.

IMPORTANT:

You DO NOT run `main_watcher.py` separately.

`interface_server.py` imports the required processing functions from `main_watcher.py` and starts the scan-processing pathway when an image is uploaded.


---

# 2. THE IDEA

The project is built around a simple tension.

## WHAT THE MACHINE APPEARS TO DO

Listen.
Understand.
Remember.
Reflect.
Encourage.


## WHAT IT ACTUALLY DOES

Reads your input.
Looks for emotional signals.
Maps them to a category.
Selects a programmed response.
Keeps the interaction going.


> It doesn't understand the feeling.
> It recognises a pattern and performs a response.


The Parrot is deliberately designed to sometimes reassure, sometimes question, sometimes become sarcastic, sometimes glitch and sometimes appear irritated.

These behaviours are programmed.

The machine isn't reflecting on your life.

It is performing the idea of reflection.


---

# 3. WHY A PARROT?

The Parrot is a reference to Kili Josiyam — a familiar cultural form in which a parrot selects a card and a fortune teller interprets it for a person.

The project borrows that structure and replaces the traditional parrot with a computational system.

The familiar question becomes:

> If something outside ourselves appears to tell us something about ourselves, how much of that meaning is actually coming from the system — and how much are we supplying ourselves?

Tamil title:

கிளி ஜோசியம்


---

# 4. WHY DOES THE MACHINE FEEL PERSONAL?

The project draws attention to several psychological effects that can make general or programmed responses feel personally meaningful.

## SUBJECTIVE VALIDATION

We find personal meaning in vague or open-ended responses.

## CONFIRMATION BIAS

We notice information that confirms what we already believe.

## POPULARITY BIAS

Familiar or repeated responses can feel more credible.

## FORER–BARNUM EFFECT

General statements can feel as though they were written specifically for us.


> The machine doesn't need to know you for you to feel seen.


---

# 5. THE NAVARASA ENGINE

The system uses the traditional Navarasa framework as a conceptual classification layer.

The nine rasas used in the system are:

    SHANTA      — Peace
    KARUNA      — Compassion / sorrow
    RAUDRA      — Anger
    BHAYANAKA   — Fear
    VEERA       — Courage
    ADBHUTA     — Wonder
    HASYA       — Humour
    BIBHATSA    — Disgust
    SHRINGARA   — Love / attraction


The system looks for emotional signals in the participant's written input and maps them to one of these nine categories.

The detected rasa influences the Parrot's programmed questions, responses, roasts, glitches and other behaviours.

The classification is not intended to be a psychological diagnosis.

It is a deliberately simplified computational interpretation used as part of the artwork.


---

# 6. HOW THE SCAN PIPELINE WORKS

The scan pathway is part of the current GitHub implementation.

    Participant writes on paper
                ↓
      Any scanner app/software
                ↓
       Scan saved as PNG /
          JPG / JPEG
                ↓
          Image uploaded
                ↓
         main_watcher.py
                ↓
         Image processing
                ↓
          Tesseract OCR
                ↓
          Extracted text
                ↓
        Navarasa engine
                ↓
         Rasa classification
                ↓
       Session / database
                ↓
         Parrot behaviour


The participant does not need a specific physical scanner connected to the computer running the GitHub version.

The note can be scanned beforehand using any scanner app or scanning software.

Once the resulting image is uploaded through the interface, the server starts the image-processing function from `main_watcher.py`.

The processing therefore happens automatically as part of the interface flow.


---

# 7. REPOSITORY STRUCTURE

    Freeing_The_Parrot/
    │
    ├── interface_server.py
    ├── main_watcher.py
    ├── navarasa_engine.py
    ├── ocr_repair.py
    ├── ocr_semantic_corrector.py
    │
    ├── printer.py
    ├── trigger_scan.py
    │
    ├── audit_parrot_behaviour.py
    ├── parrot_behaviour_patch_v3.py
    ├── patch_print_realtime.py
    │
    ├── inspect_ij_controls.py
    ├── inspect_ij_win32.py
    ├── inspect_scan_utility.py
    │
    ├── changelog.md
    ├── README.md
    ├── index.html
    └── ...


## Main files

### `interface_server.py`

The main Flask application.

It provides:

- participant-facing interface
- session logic
- image upload pathway
- conversation behaviour
- session management
- digital Mirror Report generation


### `main_watcher.py`

Processes uploaded scans.

It performs:

- image processing
- OCR
- text extraction
- Navarasa analysis integration
- database/session updates


### `navarasa_engine.py`

Contains the Navarasa analysis logic used to classify emotional signals.


### `ocr_repair.py`

Contains OCR-repair functionality used in the text-processing pipeline.


### `ocr_semantic_corrector.py`

Contains additional semantic correction functionality for OCR output.


### `trigger_scan.py`

Contains scanner-trigger functionality developed during the prototype process.


### Supporting scripts

The repository also contains printer-related, behaviour-audit, patch and scanner-inspection scripts created during development and testing.


---

# 8. REQUIREMENTS

The current prototype is designed around a Windows local environment.

You need:

- Windows
- Python 3.x
- Flask
- OpenCV
- PyTesseract
- Tesseract OCR
- A browser
- A scanner app or scanning software for creating the handwritten-note image


The prototype uses:

    Tesseract OCR
    OpenCV
    Flask
    SQLite
    Python


You do NOT need a physical scanner connected to the computer running the GitHub version.

You simply need a scanned image of the handwritten note in:

    PNG
    JPG
    JPEG


The current implementation contains installation-specific paths and should therefore be treated as a local prototype rather than a plug-and-play hosted web application.


---

# 9. DETAILED SETUP

## STEP 1 — CLONE THE REPOSITORY

Open Windows PowerShell.

Run:

    git clone https://github.com/msup96/Freeing_The_Parrot.git


The current implementation expects the project directory to be:

    C:\freeing_the_parrot


If you clone the repository somewhere else, installation-specific paths may need to be changed.


---

## STEP 2 — OPEN THE SCRIPTS DIRECTORY

Run:

    cd C:\freeing_the_parrot\scripts


The main Python application files are inside the `scripts` directory.


---

## STEP 3 — INSTALL THE PYTHON DEPENDENCIES

From your Python environment, run:

    pip install flask opencv-python pytesseract


If a package is already installed, that is fine.


---

## STEP 4 — INSTALL TESSERACT OCR

The current prototype expects Tesseract at:

    C:\Program Files\Tesseract-OCR\tesseract.exe


This path is defined in `main_watcher.py`.

If Tesseract is installed somewhere else, update:

    TESSERACT_PATH


inside `main_watcher.py`.


---

## STEP 5 — SCAN YOUR NOTE AND PREPARE THE IMAGE

Write your note on paper.

Scan the note using **any scanner app or scanning software**.

Save the scanned note as one of the supported image formats:

    PNG
    JPG
    JPEG


You do NOT need to use Canon IJ Scan Utility.

You do NOT need to connect a physical scanner to the computer running the GitHub version.

The important part is that you have a clear image of your handwritten note ready to upload.

Then open the Freeing the Parrot interface and upload the scanned image.

The uploaded image is passed into the OCR and Navarasa processing pipeline.


---

# 10. START THE APPLICATION

From:

    C:\freeing_the_parrot\scripts


run:

    python .\interface_server.py


You should see startup information similar to:

    FREEING THE PARROT
    INTERFACE SERVER
    [ENGINE] Navarasa engine loaded.
    [DATABASE] SQLite: C:\freeing_the_parrot\emotional_database.db
    [CHAT] Validation gate: ONLINE
    [CHAT] Fast-relief gate: ONLINE
    [CHAT] Socratic engine: ONLINE
    [TERMINATION] User-controlled shutdown: ONLINE
    [INTERFACE] http://localhost:5000


Then open your browser and go to:

    http://localhost:5000


---

# 11. IMPORTANT — DO NOT START `main_watcher.py` SEPARATELY

This is important.

Do NOT run:

    python .\main_watcher.py


The interface server already imports:

    from main_watcher import process_image, update_scan_status


When an image is uploaded, `interface_server.py` starts the processing function automatically.

The intended launch command is simply:

    python .\interface_server.py


There should be one main application process:

    interface_server.py


`main_watcher.py` functions as part of that application.


---

# 12. RUN A COMPLETE SESSION

Once the server is running:

## 1. Open the interface

Go to:

    http://localhost:5000


## 2. Start the Parrot interaction

The participant-facing interface will guide the interaction.


## 3. Write something on paper

The participant can write:

- an anecdote
- a memory
- a question
- a letter
- a difficult moment
- something they are thinking about
- anything personal they are willing to put on paper


## 4. Scan your note

Use **any scanner app or scanning software** to scan the handwritten note.

Save the result as:

    PNG
    JPG
    JPEG


## 5. Upload the scanned image

Upload the scanned image through the Freeing the Parrot interface.

The image is passed to the local Flask server and then into the OCR and Navarasa processing pipeline.


## 6. OCR processes the handwriting

`main_watcher.py` receives the uploaded image.

Tesseract OCR extracts text from the scan.


## 7. Navarasa analysis runs

The extracted text is passed through the Navarasa engine.

The system looks for emotional signals and maps the input to a rasa.


## 8. The Parrot responds

The detected classification influences the programmed behaviour of the Parrot.

The Parrot may:

- ask questions
- provide reassurance
- continue the conversation
- become sarcastic
- appear irritated
- glitch
- challenge the participant


These behaviours are intentionally programmed.


## 9. Continue the interaction

The participant continues responding to the Parrot.

The system maintains the session and records the conversation.


## 10. End the session

When finished, select:

    I AM DONE!


This gives the participant control over when the interaction ends.


## 11. Generate the Mirror Report

The system generates the final digital session output.


---

# 13. DIGITAL MIRROR REPORT

The current GitHub version does NOT depend on a thermal printer for the final session output.

Instead, the complete conversation is generated as a digital image.

The output retains the visual language of a physical receipt:

- narrow receipt-like proportions
- monospaced typography
- off-white paper
- subtle texture
- scanned/printed quality
- complete conversation transcript
- token telemetry
- final Parrot response


The refinement keeps the visual language of a receipt while removing the dependency on physical thermal printing.


---

# 14. WHY THE OUTPUT LOOKS LIKE A RECEIPT

A conversation with an AI normally disappears back into the screen.

This project wanted the interaction to leave something behind.

The Mirror Report turns the machine's interpretation into a physical-looking artefact — something that can be viewed, saved and questioned.

It looks personal.

But how personal is a response built from patterns?


---

# 15. TOKEN TELEMETRY

The session output includes estimated token information.

The prototype uses:

    characters / 4 ≈ tokens


The report can show:

    USER TOKENS
    EST. MACHINE TOKENS
    EST. TOTAL TOKENS


These are estimates, not measurements of actual model-token usage.

The purpose is to make the computational footprint of the interaction visible.


---

# 16. THE PARROT DOESN'T ACTUALLY HELP YOU

The Parrot:

> plays along.

> asks questions.

> gives reassurance.

> appears to remember.

> gets irritated.

> glitches.


All of these behaviours are programmed.

The machine isn't reflecting on your life.

**It is performing the idea of reflection.**


The sarcasm is intentional.

The glitches are intentional.

The irritation is intentional.

They interrupt the expectation that the machine should simply make us feel better.


---

# 17. WIZARD-OF-OZ PROTOTYPING

The prototype includes a Wizard-of-Oz component.

The participant experiences the scanning and processing interaction as part of the functioning system, while parts of the backend workflow can be triggered or controlled during testing.

This is an intentional prototype strategy.

The goal is not to automate every possible operation.

The goal is to make the parts that matter to the participant's experience real while simulating or controlling parts that introduce unnecessary technical risk.


> Good prototyping isn't about automating everything. It's about knowing what needs to be real, what can be simulated, and where the risk isn't worth it.


---

# 18. LIMITATIONS

This repository is a working prototype, not a one-click installation package.

The current version has installation-specific assumptions, including:

- Windows
- local Python environment
- local Tesseract installation
- local filesystem paths
- local SQLite database
- local browser
- OCR-dependent handwriting recognition


The implementation currently uses paths based around:

    C:\freeing_the_parrot


A different computer may therefore require configuration changes before the prototype runs correctly.


---

# 19. PRIVACY

The project is designed as a local prototype.

Participant-written material is processed by the local system as part of the installation workflow.

Anyone adapting this repository for public deployment should independently review:

- where scanned documents are stored
- how long they are retained
- database contents
- generated session outputs
- access to the local server
- whether external APIs or services are introduced


The GitHub repository should not be treated as a guarantee of privacy for modified or redeployed versions.


---

# 20. DEVELOPMENT REFLECTIONS

## From code-averse to technically curious

I started as someone who was reluctant to even read the first few lines of code; by the end, I had built the entire setup, worked through 5,000+ lines of code, understood what individual scripts, functions and CSS sections were doing, and experimented through trial and error.

More importantly, I reached a point where I could identify and flag errors myself before ChatGPT did, instead of depending on it to tell me what was wrong.


## From making a system to questioning one

The project began as an attempt to build an interactive AI system.

Building it forced me to question what the system was actually doing and what people might assume it was doing.


## From “AI understands” to “AI appears to understand”

Working through the interaction made the distinction between emotional understanding and computational response much more tangible.


## From cultural reference to conceptual framework

Kili Josiyam started as a cultural reference.

It became a way to think about why people seek meaning from something outside themselves.


## From building features to designing behaviour

The project shifted from asking:

> What can the system do?

to:

> How should the system behave to expose the assumptions people bring to it?


## From prototype as outcome to prototype as argument

The final prototype is not only a demonstration of technical functionality.

The interaction itself is part of the argument.


---

# 21. THE AUTOSCAN LESSON

What looked like a small convenience became a system risk.

I initially explored making the scanning process fully automatic — the system would detect the document, trigger the scan and continue the interaction without intervention.

In testing, I realised that adding automation at the hardware/software boundary introduced more failure points than value, so I stepped back and used a Wizard-of-Oz approach for the prototype.

The takeaway:

> Good prototyping isn't about automating everything. It's about knowing what needs to be real, what can be simulated, and where the risk isn't worth it.


---

# 22. PROJECT STATUS

The repository contains the working prototype used to demonstrate the Freeing the Parrot interaction.

The current version includes:

- participant-facing Flask interface
- handwritten input workflow
- scanned-image upload pathway
- OCR processing
- Navarasa classification
- Parrot conversation
- programmed behavioural responses
- user-controlled session termination
- digital Mirror Report generation
- token telemetry
- supporting development scripts


The system remains a local prototype.


---

# 23. FINAL POWERSHELL COMMANDS

For someone who has already completed setup, these are the only commands needed to launch the application.

Open **Windows PowerShell**:

    cd C:\freeing_the_parrot\scripts
    python .\interface_server.py


Then open the interface in your browser:

    http://localhost:5000


Leave the PowerShell window running while using the application.

When you are finished with the prototype, return to the same PowerShell window and press:

    Ctrl + C


### DO NOT RUN THIS:

    python .\main_watcher.py


`main_watcher.py` is imported automatically by `interface_server.py`.


---

# 24. QUICK START

If setup is already complete:

    cd C:\freeing_the_parrot\scripts
    python .\interface_server.py


Open:

    http://localhost:5000


Then:

    1. Write your note.
    2. Scan it using any scanner app/software.
    3. Save it as PNG, JPG or JPEG.
    4. Upload the scanned image.
    5. Let the system process the note.
    6. Talk to the Parrot.
    7. Select I AM DONE!
    8. View the Digital Mirror Report.


---

# 25. REPOSITORY

GitHub:

https://github.com/msup96/Freeing_The_Parrot


---

# WHO IS DOING THE EMOTIONAL WORK?

If the machine only gives us patterns we are willing to interpret as meaningful:

> Is the machine understanding us — or are we understanding ourselves through it?


# FREE THE PARROT.

The machine can reflect.

**You still have to think.**
