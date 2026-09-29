# FREEING THE PARROT 2.0 (FTP 2.0)
## Test Strategy & Verification Specification

> *"Quality assurance in FTP 2.0 enforces ethical boundaries, architectural ignorance, and artistic intent."*

---

## 1. Test Strategy Overview

The testing architecture for FTP 2.0 validates not only functional correctness and hardware stability, but also enforces **non-functional ethical invariants**:
* The live conversational engine must remain ignorant of participant profiling.
* State transitions must remain sovereign to the participant and deterministic guards.
* Generated readings must never leak mechanical spoilers prior to the reveal.
* Consent mechanisms must guarantee complete data purging when requested.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FTP 2.0 TEST PYRAMID                            │
│                                                                             │
│                [ E2E / Hardware Installation Test Suite ]                  │
│                (Scanner, Web Interface, POS58 Thermal Spool)               │
│                                                                             │
│          [ Behavioral & Ethical Invariant Contract Tests ]                  │
│          (Parrot Ignorance, 27-Card Invariants, Consent Purge)              │
│                                                                             │
│       [ Integration & Event Bus Normalization Test Suite ]                  │
│       (Event Store, Gemini Schema, Navarasa Parity, Telemetry)              │
│                                                                             │
│    [ Isolated Unit Tests: Lexicon, State Transitions, Wrappers ]            │
│    (navarasa_engine, state_machine, textwrap, regex patterns)               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Dedicated Test Suites & Verification Specifications

### 2.1 Parrot Ignorance & Information Isolation Tests
* **Objective:** Ensure the live Parrot process memory cannot access Silent Reader telemetry, Gemini synthesis, or historical participant profiles.
* **Test Cases:**
  * `test_parrot_context_injection_rejection`: Pass an event containing `silent_reader_telemetry` or `gemini_inferences` into `parrot_engine.generate_reply()`. Assert that the function raises a `StrictBoundaryViolationError`.
  * `test_parrot_memory_leakage_audit`: Perform AST and runtime introspection on `parrot_engine` to verify it has no active database queries targeting `inferences`, `cards`, or `telemetry` tables.
  * `test_parrot_response_invariance`: Feed the identical chat conversation to two sessions—one with intense background hesitation telemetry and one with zero hesitation. Assert that `parrot_engine` produces mathematically identical response candidates.

---

### 2.2 State Machine & Transition Boundary Tests
* **Objective:** Verify deterministic state transitions and ensure AI outputs never trigger state changes.
* **Test Cases:**
  * `test_ai_output_cannot_transition_state`: Mock Gemini / Parrot returning malicious transition strings (e.g., `{"next_state": "S8_DATA_WALL_CONSENT"}`). Assert state remains in `S2_LIVE_CONVERSATION`.
  * `test_trust_window_enforcement`: Run 5,000 simulated turns on Turns 1, 2, and 3. Assert 100% of responses are classified as `"understanding"`.
  * `test_gradual_instability_curve`: Run 50,000 simulated turns across Turns 4–15. Assert instability probability adheres to $P = \min(0.70, 0.08 + (\text{turn} - 4) \times 0.055)$ within a 2.5% statistical margin.
  * `test_recovery_possibility`: Assert that even at Turn 50, `"understanding"` mode is observed in at least 25% of responses.

---

### 2.3 Event Integrity & Microsecond Ordering Tests
* **Objective:** Validate append-only event store guarantees and timestamp precision.
* **Test Cases:**
  * `test_event_immutability`: Attempt an `UPDATE` or `DELETE` query directly on `event_store`. Assert database triggers reject the operation.
  * `test_microsecond_monotonicity`: Ingest 100 events in rapid succession across multiple threads. Assert sequential event sequence IDs match chronological microsecond timestamps.

---

### 2.4 Multimodal Normalization Tests
* **Objective:** Validate normalization across Text, Image, Audio, and Video.
* **Test Cases:**
  * `test_image_ocr_normalization`: Ingest standard handwritten scan fixture (`test_scan.png`). Verify grid removal, OCR variant scoring, and generation of `OCR_TEXT_EXTRACTED` event.
  * `test_audio_asr_normalization`: Ingest standard audio speech fixture (`test_voice.wav`). Verify ASR transcript generation and temporal latency tagging.
  * `test_empty_input_fallback`: Ingest corrupt or blank image. Verify `input_manager` dispatches `EVT_INPUT_NORMALIZATION_FAILED` without crashing the state machine.

---

### 2.5 Navarasa Engine Preservation & Parity Tests
* **Objective:** Ensure FTP 2.0 Navarasa classification produces 100% parity with legacy FTP 1.0 `navarasa_engine.py`.
* **Test Cases:**
  * `test_navarasa_golden_dataset_parity`: Execute classification against 250 benchmark sentences across all 9 Rasas. Assert exact floating-point score parity with FTP 1.0.
  * `test_negation_and_intensity_handling`: Verify sentences with *"not happy"*, *"extremely angry"*, and *"slightly sad"* match expected valence inversions.

---

### 2.6 Silent Reader Isolation & Telemetry Tests
* **Objective:** Ensure passive background telemetry runs asynchronously without adding latency to live chat.
* **Test Cases:**
  * `test_silent_reader_zero_chat_latency`: Measure roundtrip response latency of `parrot_engine` with Silent Reader active vs disabled. Assert latency delta $< 5\text{ ms}$.
  * `test_telemetry_capture_completeness`: Simulate typing sequence with backspaces and pauses. Verify `TELEMETRY_RECORDED` event captures exact pause durations.

---

### 2.7 Gemini Post-Session Schema & Timeout Fallback Tests
* **Objective:** Verify post-session JSON schema compliance and timeout resilience.
* **Test Cases:**
  * `test_gemini_27_card_schema_conformance`: Mock Gemini payload. Validate against JSON schema (`KiliJosiyamCardDeck`).
  * `test_gemini_timeout_recovery`: Mock Gemini API hanging for $> 8000\text{ ms}$. Assert state machine falls back to deterministic 27-card baseline deck without error.

---

### 2.8 Exactly 27 Unique Cards Invariant Tests
* **Objective:** Ensure generated deck contains exactly 27 unique, qualitative readings with zero analytical spoilers.
* **Test Cases:**
  * `test_deck_contains_exactly_27_cards`: Validate `len(cards) == 27` and indices are $1 \dots 27$.
  * `test_card_uniqueness`: Assert all 27 `card_id` and `qualitative_reading` texts are pairwise distinct.
  * `test_no_premature_analytical_spoilers`: Scan all 27 card texts using regex for banned diagnostic keywords (*"you said"*, *"system matched"*, *"Navarasa"*, *"OCR detected"*, *"sentiment score"*). Assert zero matches.

---

### 2.9 Card Evidence & Underlying Provenance Mapping Tests
* **Objective:** Ensure every card retains structured underlying evidence for the reveal phase.
* **Test Cases:**
  * `test_card_evidence_references_valid_events`: Validate that all `triggering_event_refs` point to valid `event_id` records in the active session Event Store.
  * `test_barnum_technique_classification`: Verify every card declares an explicit `barnum_technique` enum value.

---

### 2.10 "RESONATES" Validation Interaction Tests
* **Objective:** Ensure participant validation is typed as subjective resonance, not scientific truth.
* **Test Cases:**
  * `test_user_resonance_payload_typing`: When user selects a card, assert emitted event is `CARD_RESONANCE_MARKED` with `provenance_level: "VALIDATED"`.
  * `test_provenance_disclaimer_present`: Assert payload contains the mandatory disclaimer: *"Participant asserted subjective resonance with this card. This endorsement reflects personal projection, not verified biographical truth."*

---

### 2.11 Profile Reveal & Deconstruction Tests
* **Objective:** Ensure Profile Reveal accurately deconstructs the illusion of understanding.
* **Test Cases:**
  * `test_reveal_payload_construction`: Assert `reveal_engine` builds a complete mapping from user raw inputs $\rightarrow$ detected Rasas $\rightarrow$ selected cards $\rightarrow$ Barnum mechanics.
  * `test_forer_barnum_explanation_rendered`: Verify the deconstruction text includes explicit educational reflections on subjective validation.

---

### 2.12 Consent, Anonymization & Purge Tests
* **Objective:** Guarantee absolute compliance with participant data sovereignty.
* **Test Cases:**
  * `test_keep_private_executes_hard_purge`: Trigger `consent = "KEEP_PRIVATE"`. Assert `SELECT * FROM chat_interactions WHERE session_id = ?` returns zero rows, raw scan files are unlinked, and RAM is cleared.
  * `test_share_applies_pii_scrubbing`: Trigger `consent = "SHARE"`. Assert named entity recognition scrubs names, phone numbers, and addresses, replacing them with `[REDACTED]`.

---

### 2.13 Printer & Output Decoupling Tests
* **Objective:** Ensure receipt printing and digital output are completely decoupled from data consent.
* **Test Cases:**
  * `test_print_without_consent_purges_data`: Print physical receipt on a session with `consent = "KEEP_PRIVATE"`. Verify receipt prints successfully AND all backend data is purged.
  * `test_receipt_formatting_line_width`: Verify all generated receipt lines adhere strictly to `LINE_WIDTH = 32`.
  * `test_disclaimers_always_present`: Verify printed text always includes: *"It is better to be Homo Sapiens than Robo Sapiens."*

---

### 2.14 Hardware Fault Tolerance & Failure Recovery Tests
* **Objective:** Ensure hardware disconnection does not crash the installation.
* **Test Cases:**
  * `test_scanner_offline_graceful_handling`: Disconnect scanner. Ingest via web fallback. Assert smooth transition to `S2_LIVE_CONVERSATION`.
  * `test_printer_offline_fallback`: Disconnect thermal printer. Trigger print. Assert system writes digital receipt to disk, displays download link, and transitions cleanly to `S10_PURGE_RESET`.
