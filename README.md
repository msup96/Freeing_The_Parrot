# FREEING THE PARROT

> **The machine doesn't know you. It just knows how to sound like it does.**

An interactive physical-digital installation exploring the illusion of emotional understanding in AI.

---

## ABOUT

Freeing the Parrot explores what happens when we look to a machine for something that has traditionally come from another person — listening, reassurance, encouragement and the feeling of being seen.

The project asks:

> **What happens when the feeling of being heard becomes easier to find in a machine than in another human being?**

The installation was originally built and tested as a physical experience in college.

This GitHub repository contains the **software prototype and documentation behind that installation**, adapted to be publicly accessible as a local Windows setup.

---

# WHAT IS THE GITHUB VERSION?

The GitHub version is a **local software prototype** of Freeing the Parrot.

It contains the systems responsible for:

- the interactive interface
- scanned document processing
- OCR
- emotional signal detection
- Navarasa classification
- programmed conversational behaviour
- session management
- Digital Mirror Report generation

The original college installation included the physical elements — scanner, computer, paper input and display.

The GitHub repository preserves the **digital system behind that experience**.

It is not a hosted website and it is not currently packaged as a plug-and-play application.

The current prototype is configured for a **Windows environment**.

---

# HOW THE SYSTEM WORKS

```text
Participant writes on paper
            ↓
      Physical scanner
            ↓
    Interface server
            ↓
      OCR processing
            ↓
    Emotional signals
            ↓
     Navarasa engine
            ↓
   Programmed behaviour
            ↓
      Conversation

## Detailed Instructions.

REPOSITORY STRUCTURE
Freeing_The_Parrot/
│
├── interface_server.py
├── main_watcher.py
├── navarasa_engine.py
├── ocr_repair.py
├── ocr_semantic_corrector.py
├── changelog.md
├── README.md
└── ...
interface_server.py

The main entry point for the installation.

It runs the Flask interface, handles the browser interaction, manages sessions and receives scanned documents.

main_watcher.py

The document-processing pipeline.

It handles the OCR workflow, image preprocessing, OCR correction and passes the resulting text into the Navarasa engine.

It is not launched separately.

navarasa_engine.py

The emotional classification layer.

It analyses the extracted text and maps emotional signals to the nine Navarasas.

ocr_repair.py

Supporting OCR correction and repair logic.

ocr_semantic_corrector.py

Supporting semantic correction for OCR output.

REQUIREMENTS

The current prototype is designed for:

Windows
Python 3.x
Tesseract OCR
OpenCV
PyTesseract
Flask
A compatible document scanner
Canon IJ Scan Utility for the physical scanning workflow

The current code also uses paths from the original installation environment.

SETUP
01 — CLONE THE REPOSITORY

Open Windows PowerShell.

git clone https://github.com/msup96/Freeing_The_Parrot.git

The current prototype expects the project to be located at:

C:\freeing_the_parrot

So the resulting structure should look approximately like:

C:\freeing_the_parrot
│
├── changelog.md
├── ...
│
└── scripts
    ├── interface_server.py
    ├── main_watcher.py
    ├── navarasa_engine.py
    ├── ocr_repair.py
    └── ocr_semantic_corrector.py
02 — START THE INTERFACE

Open Windows PowerShell and navigate to the scripts directory:

cd C:\freeing_the_parrot\scripts

Start the interface server:

python .\interface_server.py

If everything is configured correctly, PowerShell will display:

[INTERFACE] http://localhost:5000

You may also see a local network address such as:

http://192.168.x.x:5000

Keep the PowerShell window running.

03 — OPEN THE PARROT

Open a browser and go to:

http://localhost:5000

The Freeing the Parrot interface should appear.

If the interface is being displayed on another device connected to the same local network, use the network address shown by Flask.

For example:

http://192.168.x.x:5000

The exact address depends on the computer and network.

04 — WRITE SOMETHING

Take a sheet of paper.

Write something you are willing to share with the machine.

It can be:

an anecdote
a memory
a question
something that happened today
something you are thinking about
or simply whatever you want the parrot to know

There is no required format.

05 — SCAN THE PAPER

Place the paper on the connected scanner.

On the interface, select:

SCAN DOCUMENT

The Canon IJ Scan Utility will open.

Select:

Document

Keep an eye on the taskbar after clicking Scan Document on the interface.

Once the scan is received, the processing pipeline begins automatically.

06 — YOU ONLY START ONE PYTHON FILE

The operator only needs to run:

python .\interface_server.py

You do not need to separately run:

python .\main_watcher.py

interface_server.py imports the processing functions from main_watcher.py.

When a scanned document is uploaded, the interface server automatically starts the document-processing pipeline.

The relationship is:

interface_server.py
        │
        │ receives scan
        ▼
main_watcher.py
        │
        ├── image preprocessing
        ├── OCR
        ├── OCR correction
        │
        ▼
navarasa_engine.py
        │
        ▼
emotional classification
        │
        ▼
programmed conversation
        │
        ▼
Digital Mirror Report

interface_server.py is the entry point.

07 — TALK TO THE PARROT

Once your writing has been processed, the parrot begins the interaction.

Respond to its questions through the interface.

The detected emotional classification can influence the parrot's programmed behaviour.

The parrot may:

ask questions
reassure you
challenge you
roast you
become irritated
glitch
appear to remember
or behave unexpectedly

There is no correct way to answer.

08 — END THE SESSION

When you are finished, click:

I AM DONE!

The system generates a Digital Mirror Report.

The interface will display:

GENERATING DIGITAL MIRROR REPORT...

and then:

DIGITAL MIRROR REPORT READY.

The report contains the conversation, system responses and session information.

It is generated digitally as an image designed to resemble a scanned thermal receipt.
            ↓
   Digital Mirror Report
