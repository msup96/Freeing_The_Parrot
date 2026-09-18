# FREEING THE PARROT

> **The machine doesn't know you. It just knows how to sound like it does.**

An interactive physical-digital installation exploring the illusion of emotional understanding in AI.

---

## THE QUESTION

What happens when the feeling of being heard becomes easier to find in a machine than in another human being?

Freeing the Parrot explores why AI can feel emotionally responsive even when what happens underneath is pattern recognition, classification and programmed response.

The project is not asking people to stop using AI.

It asks us to notice **what we are projecting onto it.**

---

## THE EXPERIENCE
## 1. Technical setup
Open TWO PowerShell windows.

WINDOW 1 — Start the web interface:
cd C:\freeing_the_parrot\scripts
python -u interface_server.py
Keep this window running. Website: http://localhost:5000

WINDOW 2 — Start the emotional scan watcher:
cd C:\freeing_the_parrot\scripts
python -u main_watcher.py
Keep this window running. It should end with the watcher waiting for a NEW scan.

## 2. The process
A participant is invited to write something personal on paper — an anecdote, a memory, a question, a difficult moment, or simply whatever they are willing to share.

The paper enters the machine.

The system:

**reads the input → identifies emotional signals → maps them to a rasa → responds through a programmed conversational system → produces a Mirror Report.**

The final interaction leaves the screen as a digital artefact: a receipt-like record of the conversation.

### Experience flow

```text
WRITE
  ↓
SCAN
  ↓
OCR
  ↓
NAVARASA CLASSIFICATION
  ↓
PARROT CONVERSATION
  ↓
PROGRAMMED BEHAVIOURS
  ↓
MIRROR REPORT
