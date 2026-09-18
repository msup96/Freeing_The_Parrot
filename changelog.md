## 2026-08-24 — Session Lifecycle Refresh + iPad Physical Display

### Automatic Session Refresh

- Refined the HTML session lifecycle so the interface refreshes only after the current interaction has physically completed its print cycle.
- The existing 5-second post-print refresh has been retained.
- The refresh is now triggered by the print engine reaching a `complete` state rather than by the type of print event.
- This allows both normal conversation printing and expletive-triggered printing to follow the same lifecycle.

### Updated lifecycle

Normal conversation:

```text
USER INTERACTION
      ↓
10-SECOND SILENCE
      ↓
SESSION TERMINATED
      ↓
AUTOMATIC CONVERSATION PRINT
      ↓
PRINT COMPLETE
      ↓
5-SECOND WAIT
      ↓
INTERFACE REFRESH

## 2026-08-22 — Automatic Physical Record of Every Conversation

### Automatic Conversation Printing
- Removed the requirement for the user to manually click `PRINT CONVERSATION`.
- The thermal printer is now integrated into the natural lifecycle of the interaction.
- When a normal conversation reaches its existing 10-second silence/session-termination condition, the system automatically prints the complete conversation.
- The printed output contains the conversation as it occurred, rather than a generated summary.
- The HTML interface now reflects the automatic print process through the existing print-engine progress and status display.
- The existing 5-second interface refresh after successful conversation printing has been retained.

### Expletive Intervention
- Expletive detection remains an independent behavioural trigger.
- When an expletive is detected, the system generates its behavioural response first and then automatically initiates a physical print.
- The resulting receipt contains the complete conversation up to that point, including the system's response to the expletive.
- The intervention receipt includes:

  `TO KEEP YOURSELF AND WHAT YOU SHARE IN CHECK.`

  `THE PARROT JUST PECKED YOUR HAND.`

- Automatic expletive printing bypasses the manual print interface entirely.

### Duplicate Print Protection
- Added a session-level automatic-print guard.
- Prevents the same conversation from being printed more than once when multiple session/status events occur.
- Normal session-end printing and expletive-triggered printing now share the same underlying thermal print engine.

### Prototype Validation
- Automatic conversation printing has been implemented and successfully validated.
- Normal conversation → session termination → automatic thermal print: **WORKING**
- Expletive → system response → automatic thermal print: **IMPLEMENTED**
- Manual `PRINT CONVERSATION` control: **REMOVED**
- POS58 physical printer pipeline: **WORKING**
- HTML print telemetry: **WORKING**
- Automatic post-print refresh: **WORKING**

This completes the transition from user-invoked printing to an autonomous physical response system: the machine decides when an interaction has become a physical record.

## 2026-08-22 — Thermal Printer Integration + Automatic Expletive Intervention

### Hardware Integration
- Connected the POS58 thermal receipt printer to the Freeing the Parrot system.
- Installed and verified the required Windows printer driver.
- Confirmed the printer is recognised by Windows as `POS58 Printer`.
- Verified RAW thermal printing through the Python print pipeline.
- Successfully produced a physical thermal receipt from the system.

### Print Engine — Final Prototype State
- Finalised the 58 mm thermal receipt layout.
- Integrated the conversation print engine into the HTML interface.
- Added browser-visible print progress and live print-engine status.
- The interface now mirrors the underlying PowerShell print process.
- The system can print the complete conversation transcript rather than a generated summary.
- Added the closing behavioural disclaimer:
  - `"It is better to be Homo Sapiens than Robo Sapiens."`
  - `"The machine can reflect. You still have to think."`
- Physical printer output has been successfully tested.

### Automatic Expletive Intervention
- Expletive detection is confirmed to work independently of the manual print button.
- The intended interaction has been redesigned so an expletive becomes an autonomous machine intervention.
- On detecting an expletive, the system should:
  1. Detect and flag the expletive.
  2. Generate the system's behavioural response.
  3. Append that response to the conversation.
  4. Automatically trigger the thermal printer without user intervention.
  5. Print the complete conversation up to that point.
  6. Append a behavioural warning:
     
     `TO KEEP YOURSELF AND WHAT YOU SHARE IN CHECK.`

     `THE PARROT JUST PECKED YOUR HAND.`

- The automatic expletive-print pathway has been implemented in code and syntax-validated.
- **Physical validation of the automatic expletive → full conversation → printer pathway remains the next hardware test.**

### Current Prototype Status
- Scanner → OCR → analysis → HTML interface: **WORKING**
- Conversation engine → behavioural layer: **WORKING**
- Manual conversation → thermal printer: **PHYSICALLY TESTED AND WORKING**
- Expletive detection → behavioural response: **WORKING**
- Expletive → automatic full-conversation thermal print: **IMPLEMENTED; PHYSICAL TEST PENDING**

This marks the transition from a software prototype into a physically responsive interactive system.

## 2026-08-21 — Thermal Printer Integration & Final Prototype Success

### Hardware
- Connected the POS58 58 mm thermal printer to the system.
- Completed Windows driver installation and printer configuration.
- Confirmed successful communication with the physical thermal printer.
- Successfully executed a physical test print.

### Conversation Printing Pipeline
- Added thermal-printing support through `printer.py`.
- Implemented a dedicated thermal receipt layout for the project.
- Configured the printer for RAW thermal output at 32 characters per line.
- Added conversation transcript generation directly from the active interface session.
- The printed output preserves the **entire chronological conversation between the user and system**, rather than generating a summary.
- Long conversations therefore remain intentionally long on paper, preserving repetition, awkwardness, glitches and unexpected exchanges as part of the project's interaction.

### Realtime Print Interface
- Integrated the print engine into `interface_server.py`.
- Added realtime print-status reporting through `print_status.json`.
- Added `/api/print-status` and `/api/print-reset` endpoints.
- Added realtime print progress polling to the HTML interface.
- PowerShell print-engine activity is now relayed to the HTML interface in realtime.
- Print stages currently include:
  - Session received
  - Conversation message count
  - Transcript construction
  - Transcript ready
  - Sending to POS58
  - Print complete / error state

### Print Output
- Added project identity and session transcript formatting.
- Added emotional-analysis output to the thermal print layout.
- Added the project disclaimer:

> "It is better to be Homo Sapiens than Robo Sapiens."

- Added the closing statement:

> "The machine can reflect. You still have to think."

### End-to-End Validation
The complete working loop has now been successfully tested:

**User interaction → HTML interface → session capture → transcript generation → realtime print engine → Windows printer → POS58 thermal output**

### Prototype Milestone

**FINAL PROTOTYPE — 100% WORKING**

The core prototype is now operational from interaction through physical output.

The system can:
1. Accept a user interaction.
2. Capture the complete conversation.
3. Process scanned documents through OCR and the Navarasa analysis pipeline.
4. Display processing activity in realtime.
5. Generate the complete conversation transcript.
6. Send the transcript to the POS58 thermal printer.
7. Produce a physical thermal printout.
8. Relay print-engine progress and completion status back to the HTML interface.

### Status

**Prototype integration complete.**

Next phase: fine-tuning, edge-case testing, OCR precision improvements, print-layout refinement, complete-loop validation and final prototype documentation.

## 2026-08-21 - Real-time scan pipeline - working

Connected the document scanner → Python watcher → OCR → Navarasa Engine → database → web interface pipeline.
Scan progress and processing logs are now relayed to the HTML interface in real time, rather than appearing only in PowerShell.
The interface now visibly follows the machine’s processing sequence:
Document detected
OCR preprocessing
OCR variant testing and scoring
Selected OCR result
Navarasa analysis
Sentiment analysis
Database storage
Scan completion
Added live progress updates and scrolling system logs to the scan interface.
Final processed output is automatically displayed in the PROCESSED OUTPUT panel.
Verified end-to-end operation with a handwritten document.
Confirmed successful extraction of emotional words, primary Rasa, Rasa scores, sentiment values, and analysis quality.
The machine now exposes its internal processing as it happens.

Status: OPERATIONAL

Milestone:
SCANNER → OCR → NAVARASA → DATABASE → INTERFACE
FULL PIPELINE VERIFIED

## 2026-08-20 — Document Input / Scan Engine Interface

### What changed

A document-processing stage was added to the interface before the conversational system.

The user is now asked to feed a document to the machine before entering the chat experience.

The interface displays:

```text
\[ DOCUMENT INPUT / SCAN ENGINE ]

FEED A DOCUMENT TO THE MACHINE.

Handwritten text preferred.
The machine will attempt to read it.

## 2026-08-20 — Randomised Behavioural Failure Layer

### What changed

The conversational system was expanded beyond a fixed roast/glitch progression.

The machine can now behave unpredictably during an otherwise normal conversation. Its behaviour is deliberately randomised rather than following a fixed sequence.

Possible behaviours include:

- Normal conversational response
- Roast / irritation
- Absurd or irrelevant system output
- Memory loss
- Fake system errors
- Requests for the user to help reconstruct context
- Combinations of multiple behaviours

### Design change

Earlier versions followed a more recognisable progression:

Normal → Roast → Glitch → Shutdown

This was changed because a predictable sequence allowed the user to understand and anticipate the machine's behaviour.

The new system makes a fresh behavioural decision during each interaction. Previous behaviour is considered only to reduce repetitive behaviour; it does not determine what happens next.

The result is intended to make the machine feel unreliable, fallible and difficult to predict while still retaining its core conversational function.

### Important distinction

The random behavioural glitches are separate from the inactivity mechanism.

While the user is actively responding, the machine may randomly experience behavioural failures.

If the user becomes inactive for more than 10 seconds, the existing silence mechanism takes over:

User inactivity → escalating waiting state → mega meltdown → system shutdown.

The 10-second inactivity and meltdown logic was deliberately left unchanged.

### Why this matters

The system is designed to demonstrate that an AI interface can appear functional while simultaneously exposing its own limitations.

The machine can:

- remember
- forget
- reason
- produce nonsense
- become irritated
- recover
- contradict itself
- ask the user for help

The inconsistency is therefore part of the interaction rather than an accidental software failure.

### Implementation

Added a behavioural interference layer to `interface\_server.py`.

The layer sits after the core response generation and before the response is returned to the interface.

Conceptually:

User input
→ Emotional analysis
→ Core response
→ Random behavioural intervention
→ Final response

The core response remains intact so that the system can continue functioning even when the behavioural layer introduces absurdity or memory failure.

### Status

Implemented and tested.

The 10-second inactivity shutdown remains functional.

The system can now move unpredictably between normal behaviour, roasting, absurdity, memory failure and other glitches without following a fixed conversational pattern.

# Changelog — Freeing the Parrot

> \*\*Project:\*\* Freeing the Parrot  
> \*\*System type:\*\* Deterministic / rule-based interactive art installation  
> \*\*Current state:\*\* Local Flask interface + Navarasa analysis + Socratic chat + escalation/glitch system  
> \*\*Last documented:\*\* 2026-08-18

This document records the technical development of \*\*Freeing the Parrot\*\* from the first executable implementation through the current working interface.

The project deliberately avoids generative AI. The computational pipeline is based on classical OCR/computer vision, deterministic dictionaries and pattern matching, VADER sentiment scoring, Navarasa classification, SQLite/JSON persistence, and rule-based interaction logic.

---

## 0. Concept → Technical Translation

### Initial technical intention

The original installation concept was translated into a machine that does \*\*not\*\* behave as an oracle. Instead, it should:

1. receive a human input;
2. extract and classify emotional signals;
3. map the signal into the nine Navarasas;
4. detect attempts to obtain validation, reassurance or prediction;
5. refuse oracle-like output;
6. redirect the participant into Socratic reflection;
7. deliberately expose uncertainty, fallibility and system glitches;
8. progressively increase interactional friction when the participant keeps outsourcing the answer;
9. terminate when the participant stops responding;
10. preserve the transaction as a local, inspectable system record.

The central interaction principle became:

> \*\*The machine is not your oracle. It is your mirror.\*\*

---

# Phase 1 — Initial OCR \& Watcher Baseline

## \[0.1.0] — 2026-08-18

### Added

- Initial Python directory-watcher architecture for incoming scanned images.
- Tesseract OCR pipeline for extracting handwritten/printed text from scans.
- NLTK VADER polarity scoring for deterministic sentiment metrics.
- Initial Navarasa lexicon mapping using keyword lists.
- Levenshtein-distance matching for approximate keyword recognition.
- JSON persistence through `db\_session.json`.
- Local processing architecture intended to keep the installation sovereign and offline.

### Intended execution flow

```text
SCAN
  ↓
OCR
  ↓
TEXT CLEANING
  ↓
SENTIMENT / KEYWORD ANALYSIS
  ↓
NAVARASA MAPPING
  ↓
GATE DECISION
  ↓
THERMAL RECEIPT / SYSTEM RESPONSE
```

\---

# Phase 2 — OCR Failure, False Positives \& Lexicon Control

## \[0.1.1] — 2026-08-18

### Problems identified

The first deterministic text classification approach produced excessive cross-bucket matches.

Examples included ordinary words being pulled into unrelated emotional categories because of aggressive synonym expansion:

* `story` / `stories` could trigger Raudra and Adbhuta through WordNet relationships.
* `tell` could trigger Karuna through unrelated grief/pain definitions.
* `stout` could trigger Karuna through heavy/burden-related synonyms.

### Fixed

* Introduced single-bucket claiming / priority logic.
* Reduced cross-bucket leakage caused by broad WordNet synonym expansion.
* Treated lexical ambiguity as a system-design problem rather than attempting to make the classifier appear artificially intelligent.

\---

# Phase 3 — Cursive OCR → Structured Handwriting Strategy

### Architectural pivot

Freeform cursive handwriting produced unreliable OCR because ligatures and connected strokes were being interpreted as corrupted character sequences.

The system therefore moved toward a more controlled visual input strategy:

* block-letter / comb-grid handwriting;
* clearer segmentation boundaries;
* OpenCV preprocessing;
* morphological grid removal;
* OCR after visual cleanup.

This was a deliberate trade-off: the installation prioritises **traceability and visible computation** over pretending that classical OCR can understand arbitrary handwriting perfectly.

\---

# Phase 4 — OpenCV Preprocessing \& Scanner Reliability

## \[0.2.0] — 2026-08-18

### Added

* OpenCV morphological grid subtraction.
* Horizontal and vertical structural kernels for detecting handwriting-grid lines.
* Grid masks subtracted from the source image before OCR.
* Narrative/filler blocklists to prevent ordinary story words from dominating emotional classification.
* More controlled PyTesseract configuration, including `--psm 6` and character whitelisting where appropriate.

### Scanner safety

A file-stability watcher was introduced so the OCR engine does not open an image while the scanner is still writing it.

### Result

The pipeline became:

```text
SCANNER
  ↓
WAIT UNTIL FILE IS STABLE
  ↓
OPENCV PREPROCESSING
  ↓
GRID REMOVAL
  ↓
TESSERACT OCR
  ↓
TEXT NORMALISATION
  ↓
NAVARASA + SENTIMENT ANALYSIS
```

\---

# Phase 5 — Navarasa + Gate Architecture

### Core interaction logic established

The system was formalised around three behavioural gates.

### Gate 1 — Oracle / Validation Intercept

The system detects requests such as:

* “Tell me I am doing enough.”
* “Did I do the right thing?”
* “Will everything be okay?”
* requests for prediction;
* requests for reassurance or instant emotional relief.

Instead of supplying validation, the system refuses the oracle role and redirects the participant inward.

### Gate 2 — Socratic Friction

Reflective inputs enter a question-and-response loop.

The system asks structured questions such as:

* What evidence do you currently have for that fear?
* What became quieter when you stopped trying to solve everything?
* What part of this situation is actually within your control?
* What exactly are you afraid will happen?

### Gate 3 — Mirror / Reflection

The system stops pretending to possess the missing answer. The participant is left with their own language and assumptions rather than an externally manufactured conclusion.

\---

# Phase 6 — Thermal Receipt / Physical Output Logic

The installation was designed around a physical receipt as a tangible record of the human-machine transaction.

The receipt structure includes:

* timestamp;
* scan ID;
* processing node;
* raw OCR transcript;
* detected Navarasa;
* keywords isolated;
* gate decision;
* system response;
* glitch/error state where appropriate.

### Documented test states

**2026-08-14 11:55 IST — Scan #0482**

A validation/prediction request was used to demonstrate the mirror-report structure.

**2026-08-14 11:58 IST — Scan #0483**

A direct reassurance request demonstrated the Gate 1 intercept and refusal to manufacture validation.

**2026-08-14 12:10 IST — Scan #0484**

A conflicting emotional input demonstrated the deliberate System Critical Error / Glitch state, including conflicting Navarasa vectors and binary output.

These examples established that system failure could itself become part of the artwork rather than something hidden from the participant.

\---

# Phase 7 — First Browser Interface

## \[0.3.0] — 2026-08-18

### Added

* Flask-based live dashboard through `interface\_server.py`.
* Browser interface for exposing the backend state.
* Dark green / terminal aesthetic.
* Monospace typography and system-style panels.
* Backend telemetry panel.
* Live state polling.
* Navarasa, sentiment, gate and processing information exposed visually.

### Interface principle

The browser was not treated as a generic chatbot UI. It was designed as a visible machine interface: the participant sees the system's internal categories and processing states rather than only receiving a conversational answer.

\---

# Phase 8 — Socratic Chat Engine

### Major architectural change

The interface evolved from displaying the result of a scanned document into an actual multi-turn Socratic interaction.

The Flask backend gained `/api/chat` and session state management.

Each interaction now maintains:

* session ID;
* turn count;
* answered count;
* current Navarasa;
* gate state;
* roast / irritation level;
* whether the system is waiting for an answer;
* silence timer state;
* whether the intervention has closed;
* shutdown state.

Interactions are also stored locally in SQLite through the `chat\_interactions` table.

\---

# Phase 9 — Roast / Irritation Escalation

### Added

The machine became progressively irritated when the participant repeatedly answered questions without taking ownership of the reflection.

The escalation was intentionally behavioural rather than abusive toward the participant.

The machine roasts the **interaction pattern** — repeated outsourcing of thinking, validation-seeking and attempts to make the machine solve the participant's problem.

Example escalation logic:

```text
ANSWER COUNT
     ↓
ROAST LEVEL INCREASES
     ↓
GLITCHES APPEAR
     ↓
SYSTEM IRRITATION INCREASES
     ↓
MEGA MELTDOWN
     ↓
SHUTDOWN
```

The waiting/silence logic was deliberately kept separate from roast escalation.

\---

# Phase 10 — Glitch Engine

### Added

The machine was given multiple glitch states so that the interaction does not produce the same “roast → question” rhythm indefinitely.

Glitch states include deliberately absurd system outputs such as:

* thought-buffer warnings;
* missing meaning;
* administrative paperwork;
* internal-parrot recursion;
* system desynchronisation;
* questionable memory / logic;
* binary strings;
* “BANANA PROTOCOL”; and
* the machine consulting an imaginary secondary parrot.

The glitches intentionally expose the constructed nature of the system.

\---

# Phase 11 — Expletive Detection

### Added

A separate deterministic profanity detector was introduced.

Detected general expletives are surfaced in backend telemetry as:

```text
EXPLETIVE: DETECTED
```

The system then adds an explicit machine reaction:

```text
EXPLETIVE DETECTED.

The machine has registered the profanity.
It remains unimpressed.
```

Profanity increases machine irritation but does **not** override or interfere with the silence mechanism.

The detector is deliberately limited to general expletives and does not use protected-class slurs as triggers.

\---

# Phase 12 — Typing-Aware Silence Logic

### Problem identified

The original shutdown timer could interpret an active typing participant as silent.

That created the wrong interaction: the machine could begin its 10-second shutdown sequence while the participant was still composing an answer.

### Fixed

The interface now explicitly tracks whether the participant is actively typing.

Frontend behaviour:

```text
USER TYPES
   ↓
/api/typing
   ↓
SERVER RESETS INACTIVITY CLOCK
   ↓
USER STOPS TYPING
   ↓
10-SECOND SILENCE WINDOW BEGINS
```

The browser does not poll the silence endpoint while active typing is detected.

This preserves the original waiting behaviour while making it semantically correct: **silence means no typing / no response, not simply time elapsed since the question appeared.**

\---

# Phase 13 — Mega Meltdown \& Shutdown

### Final interaction condition

The participant is intentionally required to keep responding.

If the participant continues answering, the system escalates:

```text
ROAST
→ GLITCH
→ ROAST
→ GLITCH
→ INCREASING IRRITATION
→ MELTDOWN PRECURSOR
```

If the participant stops responding for more than 10 seconds, the system terminates the intervention.

The final state includes:

```text
================================================
          INTERVENTION TERMINATED
================================================

NO RESPONSE DETECTED FOR MORE THAN 10 SECONDS.

SYSTEM DESYNCHRONISATION.
QUESTION.EXE = QUESTION
ANSWER.EXE = MISSING
MEANING = NOT FOUND

BANANA PROTOCOL ENGAGED.
THE CEILING FAN HAS NO OPINION ON THIS.
01001000 01000101 01001100 01010000

SYSTEM INTEGRITY: QUESTIONABLE.

The machine has reached the end of its patience.
It will not ask another question.
It will not manufacture an answer.

THE PARROT IS OUT OF SERVICE.
================================================
```

This became the definitive shutdown state: the participant is not rewarded with an answer; the machine simply stops.

\---

# Phase 14 — Backend Telemetry

### Current telemetry exposes

* Primary Rasa
* Validation detection
* Fast-relief detection
* Expletive detection
* Anxiety signal
* Current gate
* Roast / glitch level
* VADER sentiment compound score
* Rasa scores
* Session ID
* Turn count
* Printer state where applicable

The interface therefore exposes not only the conversational layer but also the underlying deterministic decision system.

\---

# Phase 15 — Changelog as Part of the Interface

## \[Current — 2026-08-18]

### Added

A **CHANGELOG** control was added to the top-right of the interface.

Clicking it opens a full-screen system-history overlay rather than navigating the participant away from the installation.

The interface calls:

```text
GET /api/changelog
```

The backend reads the local:

```text
changelog.md
```

and returns the complete development record to the browser.

### Design intention

The changelog is not hidden developer documentation.

It is deliberately exposed as part of the installation because the project is about making computational decision-making visible and contestable.

The participant can therefore inspect:

* what the system is built from;
* what failed;
* what changed;
* why architectural decisions were made;
* how the interaction evolved;
* where glitches were deliberately introduced;
* how the final chat behaviour was constructed.

This directly supports the project's emphasis on **traceability, fallibility and visible system logic**.

\---

# Current Architecture

```text
                    ┌─────────────────────┐
                    │     HUMAN INPUT     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  TEXT / OCR INPUT   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ NAVARASA + VADER    │
                    │ RULE-BASED ANALYSIS │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    GATE DETECTION   │
                    └───────┬─┬─┬─────────┘
                            │ │ │
                 validation │ │ │ reflection
                            │ │ │
                            ▼ │ ▼
                       INTERCEPT │ SOCRATIC LOOP
                                 │      │
                                 │      ▼
                                 │  ANSWER COUNT
                                 │      │
                                 │      ▼
                                 │  ROAST / GLITCH
                                 │      │
                                 │      ▼
                                 │   MELTDOWN
                                 │
                                 └──────────────┐
                                                ▼
                                      10 SECOND SILENCE
                                                │
                                                ▼
                                            SHUTDOWN

                     ┌─────────────────────────────┐
                     │       SQLITE / JSON         │
                     │     LOCAL STATE RECORD      │
                     └─────────────────────────────┘

                     ┌─────────────────────────────┐
                     │      FLASK INTERFACE        │
                     │ conversation + telemetry    │
                     │ changelog + system status   │
                     └─────────────────────────────┘
```

\---

# Current Technical Position

### Working

* Local Flask interface.
* Multi-turn chat.
* Navarasa mapping.
* Validation detection.
* Fast-relief detection.
* Anxiety detection.
* Expletive detection.
* Progressive roast escalation.
* Glitch escalation.
* Typing-aware silence handling.
* 20-second intervention shutdown.
* SQLite interaction logging.
* Backend telemetry.
* Thermal receipt generation / local receipt saving.
* Changelog overlay and backend endpoint.

### Known architectural principle

The project remains intentionally deterministic and inspectable.

No LLM is required for the interaction engine.

The system's apparent “personality” is produced by:

* rules;
* pattern matching;
* dictionaries;
* deterministic scoring;
* state transitions;
* predefined response banks;
* controlled randomness / glitch selection where explicitly implemented;
* and the participant's own input.

\---

# Important Development Decisions

## Ollama was rejected

Ollama was considered and explicitly rejected because running an LLM locally would still make the installation generative-AI driven.

The project's conceptual strength depends on the participant being able to inspect a machine that is **not secretly relying on an LLM to perform the psychological interaction**.

## Imperfection was retained

OCR errors, categorisation limits and deliberate glitches are not treated solely as defects.

They are part of the installation's argument:

> A machine that classifies a human emotion is itself a constructed, limited system.

## The interface became part of the research argument

The dashboard does not hide the machinery behind a friendly conversational layer.

It exposes the machine's categories, gates, counters, state, failures and history.

That makes the interface itself part of the critique.

\---

# 2026-08-18 — Current Milestone

**Freeing the Parrot is now a functioning interactive system rather than a static concept.**

The major transition completed in this development cycle was:

```text
CONCEPT
  ↓
OCR EXPERIMENT
  ↓
CLASSICAL EMOTION ENGINE
  ↓
NAVARASA MAPPING
  ↓
GATE LOGIC
  ↓
PHYSICAL RECEIPT CONCEPT
  ↓
LIVE HTML INTERFACE
  ↓
MULTI-TURN SOCRATIC CHAT
  ↓
ROAST / GLITCH ESCALATION
  ↓
TYPING-AWARE SILENCE
  ↓
MEGA MELTDOWN / SHUTDOWN
  ↓
VISIBLE DEVELOPMENT HISTORY
```

The parrot is no longer merely analysing the participant.

**The participant is now also able to inspect the machine.**

\---

# 2026-08-27 — Prototype Readiness / Interface Refinement

The prototype was prepared for first-year student testing. The underlying interaction architecture and deterministic behavioural logic were retained; the changes below refine presentation, timing, observability and physical output.

### Interface and interaction refinements

1. **Inactivity window extended**
   - Extended the active-response silence window from 10 seconds to 20 seconds.
   - The typing-aware behaviour remains in place so active composition is not treated as silence.

2. **Print Engine repositioned**
   - Repositioned the Print Engine beside the Conversation panel for a clearer primary interaction layout.

3. **System Logic display cleaned up**
   - Removed the redundant scanner-logic display and the two obsolete pre-prototype-readiness points from the lower diagnostic area.
   - The underlying processing logic was not changed.

4. **Navarasa visual colour coding added**
   - Detected Navarasa statements in the conversation now receive emotion-specific visual colour cues.
   - The colour treatment is a presentation layer only; it does not alter classification or scoring.

5. **Automatic refresh returns to the top**
   - After the post-print automatic refresh, the browser now returns to the top of the interface rather than reopening at the previous scroll position.

6. **Enter-to-send behaviour repaired**
   - Diagnosed and repaired a JavaScript syntax problem caused by a duplicated section of the message-handling code.
   - Enter now submits a message in the Windows browser; Shift+Enter remains available for a line break.

### Token Telemetry

- Added visible conversation token telemetry using character counting.
- The interface reports user characters, machine characters, total characters, estimated user tokens, estimated machine tokens and estimated total tokens.
- The estimation is intentionally transparent and approximate: **characters ÷ 4 ≈ tokens**.
- The same token telemetry is now appended to the physical conversation receipt so the printed record contains the complete conversation and its calculated interaction volume.
- This is an estimation layer, not a claim of exact model-token accounting.

### Prototype state

The interface now exposes the conversation, machine telemetry, token telemetry, system logic and physical-print state without introducing a generative model or changing the core interaction architecture. These refinements are intended to make the prototype ready for first-year student testing while preserving the installation's deliberate sense of a machine that appears more autonomous than its deterministic construction actually is.

---

## Timestamp Integrity Note

Exact clock times are preserved above where they are explicitly present in the project records (for example, the 2026-08-14 thermal-receipt test runs). For development milestones where only the date is recoverable from the available technical record, no artificial clock time has been invented.

This is intentional: the changelog should document the actual development history, not manufacture precision that the source record does not contain.

# 2026-08-27 — Social / Anthropomorphic Interaction Cases

During preparation for first-year student testing, two recurring conversational possibilities were identified: participants may begin with a simple salutation, or they may ask the machine how it is doing / feeling. These cases are now treated as explicit interaction patterns rather than left to chance emotional classification.

### Added

- **Greeting handling** for inputs such as “hi”, “hello”, “hey” and time-of-day greetings.
- **Machine-wellbeing handling** for questions such as “how are you?”, “are you okay?”, “how are you feeling?” and “do you have feelings?”.
- Added a small response bank that lets the machine report operational status while refusing to invent a subjective inner state.
- Added follow-up questions that turn the participant's assumption about machine personhood back toward the participant.
- Added these cases as an explicit `social_intercept` within the deterministic interaction architecture.

### Design intention

These encounters are important because the participant may spontaneously treat the interface as a social or emotional agent before revealing anything personal. The system therefore acknowledges the social gesture, then exposes the assumption behind it.

The responses deliberately preserve the installation's central tension: the machine can **sound socially responsive without possessing a lived emotional experience**. The interaction should create the impression of a thinking, responsive parrot while the exposed architecture remains deterministic, rule-based and inspectable.

This also expands the question bank so the interaction does not depend on every participant entering directly through an emotional disclosure.

---

# 2026-08-28 — Behavioural Architecture Refinement

The conversational system was refined to make the Parrot's behavioural instability feel intentional rather than like a fixed escalation script.

### Key changes

- Introduced explicit behavioural state tracking for the conversational experience.
- Added separate counters for salutations, apparent-understanding interactions and chaotic behavioural events.
- Added behavioural memory so the system can consider recent behaviour and avoid immediate repetition without following a predetermined sequence.
- Preserved apparent understanding as a possible recovery state even after chaotic behaviour has begun.
- Expanded the behavioural field to include:
  - apparent understanding
  - absurdity
  - memory loss
  - system glitches
  - roasting / irritation
  - requests for user assistance
  - mirroring
  - mixed behaviours
  - deliberate absurdity

### Design decision

The interaction was deliberately moved away from a predictable:

NORMAL → ROAST → GLITCH → SHUTDOWN

progression.

Instead, the machine makes a fresh behavioural decision during the conversation. The participant cannot reliably predict which failure or recovery state will appear next.

The inactivity / silence mechanism remains a separate system from the active conversational behavioural layer.

---

# 2026-08-29 — Salutation Protection & Behavioural Onset

The opening interaction was separated from the behavioural deterioration system.

### Salutation protection

- Greetings are now treated as an opening social handshake rather than a substantive conversational turn.
- A greeting does not consume an understanding interaction.
- A greeting does not increase chaos.
- A greeting does not increase the roast level.
- A greeting does not trigger behavioural glitches.
- The machine can respond socially while remaining explicit that its apparent social responsiveness is constructed.

This prevents a simple "hello" from prematurely advancing the participant into the unstable behavioural system.

### Controlled perceived understanding

The first three substantive conversational interactions now establish a deliberate period of apparent understanding.

The machine initially creates the impression:

> "It understood what I wrote."

Only after these initial interactions does the behavioural field become active.

The transition is state-based rather than tied to a fixed conversational script.

### Behavioural field activation

From the fourth substantive interaction onward, the Parrot can enter its unpredictable behavioural field.

The system combines:

- state tracking
- controlled randomness
- behavioural memory
- prevention of immediate repetition
- progressive instability

The probability of chaotic behaviour increases with interaction length but never reaches 100%, allowing the machine to recover and appear helpful again.

### Validation of the interaction model

The revised system was tested through repeated multi-turn conversations.

The intended interaction was successfully observed:

SUBSTANTIVE INPUT
→ APPARENT UNDERSTANDING
→ APPARENT UNDERSTANDING
→ APPARENT UNDERSTANDING
→ BEHAVIOURAL INSTABILITY
→ SOCRATIC CONTINUATION

The machine can therefore disrupt the participant's expectation of consistent emotional understanding without terminating the conversation immediately.

This preserves the central conceptual tension of the installation:

**The machine appears to understand, then reveals its own constructed and fallible nature.**

---

# 2026-08-29 — Prototype Behavioural System Validated

The revised conversational architecture has now been successfully tested end-to-end.

The Parrot can maintain an initial impression of understanding, transition into unpredictable behavioural states, continue asking reflective questions, and retain the broader interaction and shutdown mechanisms.

The system is now behaving as intended as a deterministic, rule-based interactive installation whose apparent personality emerges from rules, state, predefined response banks and controlled randomness rather than a generative language model.

**Current prototype status: WORKING.**

---

## 2026-08-30 — Opening Help Intent & Perceived Understanding Layer

- Added detection for opening help requests such as "Can you help me?", "I need your help", "Help me", and equivalent variants.
- Opening help requests now receive a dedicated perceived-understanding response instead of falling through to the generic first-turn response bank.
- Preserved the salutation layer so greetings such as "Hi" and "Hello" remain separate from substantive conversational turns.
- Help-specific opening responses are selected from a response bank to maintain variation across sessions.
- The change does not alter the core Navarasa detection, conversation history, behavioural randomization, or later-stage interaction logic.
- The three-interaction understanding phase remains intact before the stochastic behavioural field becomes eligible.