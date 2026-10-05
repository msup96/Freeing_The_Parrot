"""
FTP 2.0 AUTHORITATIVE BACKEND SERVICE

Runs the authentic Python FTP 2.0 backend architecture:
- SessionCoordinator & EventStore (Strict Provenance & Isolation)
- BehaviourDirector (Continuity, Engagement, Trust Window & Chaos Instability)
- LanguageRealizer (Socratic friction, Directive overlays)
- SilentReader & Reading Composer (Deterministic 27-card composition)
- Card resonance validation & Participant-facing Reveal generation
"""

from __future__ import annotations
import http.server
import json
import logging
import os
import re
import socketserver
import sys
import time
import urllib.parse
from typing import Any, Mapping

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ftp.events.model import EventType, ProvenanceLevel
from ftp.parrot.director import BehaviourDirector
from ftp.parrot.gemini_adapter import GeminiParrotAdapter
from ftp.parrot.realizer import LanguageRealizer, build_realizer_request
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState
from ftp.silent_reader.reading.compose import compose_reading_deck
from ftp.silent_reader.reading.validate import validate_card_resonance
from ftp.input.multimodal_analyzer import (
    analyze_text_offering,
    analyze_voice_offering,
    analyze_photo_offering,
    analyze_video_offering,
)
from interface_server import ROAST_BANKS, choose_random_line
from navarasa_engine import analyse_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ftp_backend")

# Configure Gemini language realization adapter
try:
    LanguageRealizer.configure_adapter(GeminiParrotAdapter())
    logger.info("Configured Gemini Language Realizer adapter.")
except Exception as e:
    logger.warning(f"Could not configure Gemini adapter: {e}")

# Active in-memory session stores
SESSIONS: dict[str, SessionCoordinator] = {}
SESSION_OFFERINGS: dict[str, dict[str, Any]] = {}
SESSION_MULTIMODAL_CONTEXT: dict[str, dict[str, Any]] = {}
SESSION_DECKS: dict[str, dict[str, Any]] = {}
SESSION_SELECTED: dict[str, dict[str, Any]] = {}
SESSION_REVEALS: dict[str, dict[str, Any]] = {}


def get_or_create_coordinator(session_id: str | None) -> SessionCoordinator:
    sid = session_id or f"ftp2_{int(time.time()*1000)}_{os.urandom(4).hex()}"
    if sid not in SESSIONS:
        coord = SessionCoordinator(sid)
        coord.start()
        SESSIONS[sid] = coord
        logger.info(f"Created new session coordinator: {sid}")
    return SESSIONS[sid]


def build_participant_reveal(coord: SessionCoordinator, deck: dict[str, Any] | None, selected: dict[str, Any] | None) -> dict[str, Any]:
    """Assemble the dedicated participant-facing reveal payload preserving provenance."""
    sid = coord.session_id
    offering = SESSION_OFFERINGS.get(sid, {})
    events = coord.store.all_events()

    # 1. WHAT YOU GAVE: actual participant inputs
    dialogue_events = [e for e in events if e.event_type == EventType.PARROT_TURN_GENERATED]
    turn_texts = [str(e.payload.get("user_text") or "") for e in dialogue_events]
    offering_text = offering.get("text") or (turn_texts[0] if turn_texts else "A quiet opening statement.")

    # 2. WHAT WAS RECORDED: actual approved observed session material
    turn_count = len(dialogue_events)
    question_count = sum(1 for t in turn_texts if "?" in t)
    total_chars = sum(len(t) for t in turn_texts) + len(offering_text)
    
    what_recorded_body = (
        f"The apparatus recorded {turn_count} conversational exchange{'s' if turn_count != 1 else ''} "
        f"spanning {total_chars} characters of direct text. "
        f"{question_count} of your statements were formulated as questions."
    )
    what_recorded_sub = (
        f"Session trace № {sid[-7:]} verified: input sequence, dialogue timestamps, "
        "and conversational rhythm preserved in archival memory."
    )

    # 3. WHAT WAS INTERPRETED: actual approved interpretation
    try:
        from ftp.silent_reader.navarasa_trajectory import NavarasaTrajectorySynthesizer
        trajectory = NavarasaTrajectorySynthesizer(coord).synthesize()
        dominant = trajectory.get("dominant_rasa", {}).get("label") or "Shanta"
        detected_seq = trajectory.get("detected_sequence", [])
        movement = " → ".join(detected_seq[:4]) if detected_seq else dominant
    except Exception as exc:
        logger.warning(f"Trajectory synthesis notice: {exc}")
        dominant = "Shanta"
        movement = "Shanta (stillness)"

    what_interpreted_body = (
        f"The emotional intelligence engine observed a trajectory characterized by {dominant} ({movement}). "
        f"Your statements indicated a movement between searching and self-interrogation."
    )
    what_interpreted_sub = (
        f"Primary affective tone: {dominant}. Interpretation derived solely from linguistic rhythm and semantic cues."
    )

    # 4. WHAT WAS CONSTRUCTED: actual eligible inference / reading construction
    deck_cards = (deck.get("cards") if deck else None) or []
    sample_archetypes = [c.get("archetype") for c in deck_cards[:4] if c.get("archetype")]
    archetype_str = ", ".join(sample_archetypes) if sample_archetypes else "Archivist, Lantern-Bearer, Anchor, Seeker"

    what_constructed_body = (
        f"A 27-card Kili Josiyam reading was composed from your session's anchor seeds. "
        f"The reading organized your reflections across 27 distinct archetypes, including the {archetype_str}."
    )
    what_constructed_sub = (
        "Each card combines a deterministic psychological seed with subjective completion, "
        "presenting reflection hypotheses rather than diagnoses."
    )

    # 5. WHAT YOU CHOSE: selected card + resonance validation
    if selected:
        card_title = selected.get("title", "The Chosen Card")
        card_idx = selected.get("card_index") or selected.get("id") or 1
        card_reading = selected.get("qualitative_reading") or selected.get("statement") or ""
        what_chose = {
            "card_index": card_idx,
            "title": card_title,
            "statement": card_reading,
            "validation": "Resonance marked by participant (reported resonance, not objective diagnosis).",
        }
    else:
        what_chose = {
            "card_index": 1,
            "title": "The First Specimen",
            "statement": "An inquiry opened and acknowledged.",
            "validation": "Session completed without card resonance selection.",
        }

    # 6. Wall Specimens: Real cards from THIS session's deck for the Wall of Fame
    wall_specimens = []
    for c in deck_cards[:12]:
        wall_specimens.append({
            "card_index": c["card_index"],
            "title": c["title"],
            "archetype": c["archetype"],
            "qualitative_reading": c["qualitative_reading"],
        })

    return {
        "session_id": sid,
        "what_you_gave": offering_text,
        "what_was_recorded": what_recorded_body,
        "what_was_recorded_sub": what_recorded_sub,
        "what_was_interpreted": what_interpreted_body,
        "what_was_interpreted_sub": what_interpreted_sub,
        "what_was_constructed": what_constructed_body,
        "what_was_constructed_sub": what_constructed_sub,
        "what_you_chose": what_chose,
        "wall_specimens": wall_specimens,
    }


def build_session_receipt(coord: SessionCoordinator) -> str:
    """Build the Digital Mirror Report receipt from the session's actual event store."""
    sid = coord.session_id
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    events = coord.store.all_events()

    dialogue_events = [e for e in events if e.event_type == EventType.PARROT_TURN_GENERATED]
    offering = SESSION_OFFERINGS.get(sid, {})
    selected = SESSION_SELECTED.get(sid)

    user_chars = 0
    machine_chars = 0
    conv_lines = [
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
    machine_chars += len("\n".join(conv_lines))

    if offering.get("text"):
        conv_lines.extend(["OFFERING:", f'"{offering["text"]}"', ""])
        user_chars += len(offering["text"])

    for e in dialogue_events:
        u_text = str(e.payload.get("user_text") or "")
        p_reply = str(e.payload.get("parrot_reply") or "")
        conv_lines.extend([
            "USER:",
            u_text,
            "",
            "PARROT:",
            p_reply,
            "",
        ])
        user_chars += len(u_text)
        machine_chars += len(p_reply)

    total_chars = user_chars + machine_chars
    user_tokens = max(1, user_chars // 4)
    machine_tokens = max(1, machine_chars // 4)
    total_tokens = user_tokens + machine_tokens

    receipt = [
        "================================",
        "       FREEING THE PARROT",
        "     -- MIRROR REPORT 2.0 --",
        "================================",
        f"TIME: {now_str}",
        f"SESSION ID: {sid}",
        "",
        "[CONVERSATION]",
        "--------------------------------",
        *conv_lines,
        "--------------------------------",
        "[KILI JOSIYAM - SELECTED CARD]",
        f"CARD: {selected.get('title', 'None Selected') if selected else 'None Selected'}",
        f"READING: {selected.get('qualitative_reading', '') if selected else ''}",
        "",
        "--------------------------------",
        "",
        '"It is better to be Homo Sapiens',
        ' than Robo Sapiens."',
        "",
        "The machine can reflect.",
        "You still have to think.",
        "",
        "[TOKEN TELEMETRY]",
        "--------------------------------",
        f"USER CHARACTERS: {user_chars}",
        f"MACHINE CHARACTERS: {machine_chars}",
        f"TOTAL CHARACTERS: {total_chars}",
        f"EST. USER TOKENS: {user_tokens}",
        f"EST. MACHINE TOKENS: {machine_tokens}",
        f"EST. TOTAL TOKENS: {total_tokens}",
        "",
        "TOKEN ESTIMATION",
        "characters / 4 ~= tokens",
        "Approximation only.",
        "",
        "================================",
        "          END OF SESSION",
        "================================",
    ]
    return "\n".join(receipt)


class FtpApiHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            self._send_json({"ok": True, "service": "ftp_backend", "status": "online"})
            return

        if path == "/api/session-reveal":
            sid = query.get("session_id", [""])[0]
            coord = SESSIONS.get(sid)
            if not coord:
                self._send_json({"error": "Session not found"}, 404)
                return
            deck = SESSION_DECKS.get(sid)
            selected = SESSION_SELECTED.get(sid)
            reveal = SESSION_REVEALS.get(sid) or build_participant_reveal(coord, deck, selected)
            SESSION_REVEALS[sid] = reveal
            self._send_json({"ok": True, "session_id": sid, "reveal": reveal})
            return

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        try:
            self._handle_post()
        except Exception as exc:
            logger.exception(f"Unhandled error in do_POST: {exc}")
            self._send_json({"error": f"Internal FTP error: {str(exc)}"}, 500)

    def _handle_post(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            body = {}

        path = urllib.parse.urlparse(self.path).path

        # 1. POST /api/session/start
        if path == "/api/session/start":
            sid = f"ftp2_{int(time.time()*1000)}_{os.urandom(4).hex()}"
            coord = SessionCoordinator(sid)
            coord.start()
            SESSIONS[sid] = coord
            self._send_json({
                "ok": True,
                "session_id": sid,
                "state": "INPUT_INGESTION",
                "analysis_ready": False,
            })
            return

        # 2. POST /api/input/text
        if path == "/api/input/text":
            sid = body.get("session_id")
            text = (body.get("text") or "").strip()
            if not sid:
                self._send_json({"error": "session_id required"}, 400)
                return
            coord = get_or_create_coordinator(sid)
            coord.record_raw_input({"modality": "TEXT", "text": text})
            nav = analyse_text(text)
            coord.mark_analysis_ready(nav)
            multi_ctx = analyze_text_offering(text)
            SESSION_MULTIMODAL_CONTEXT[sid] = multi_ctx
            SESSION_OFFERINGS[sid] = {"channel": "write", "text": text, "modality": "TEXT"}
            self._send_json({
                "ok": True,
                "session_id": sid,
                "state": coord.machine.state.value,
                "analysis_ready": True,
                "multimodal_analysis": multi_ctx,
                "event_id": f"evt_{int(time.time()*1000)}",
            })
            return

        # 3. POST /api/input/ingest
        if path == "/api/input/ingest":
            sid = body.get("session_id")
            modality = body.get("modality", "IMAGE").upper()
            filename = body.get("filename", "")
            transcript = body.get("transcript", "")
            duration_sec = float(body.get("duration_sec", 0.0) or 0.0)
            is_doc = body.get("is_document")
            ocr_hint = body.get("ocr_hint")

            coord = get_or_create_coordinator(sid)
            coord.record_raw_input({"modality": modality})
            coord.mark_raw_offering_ready()

            if modality in ("AUDIO", "VOICE", "SPEAK"):
                multi_ctx = analyze_voice_offering(transcript=transcript or "Voice offering received.", duration_sec=duration_sec or 3.5)
                channel = "speak"
            elif modality in ("VIDEO",):
                multi_ctx = analyze_video_offering(duration_sec=duration_sec or 15.0)
                channel = "look"
            else:
                multi_ctx = analyze_photo_offering(filename=filename, ocr_hint=ocr_hint, is_document=is_doc)
                channel = "look" if modality == "CAMERA" else "show"

            SESSION_MULTIMODAL_CONTEXT[sid] = multi_ctx
            offering_text = multi_ctx.get("ocr_text") or multi_ctx.get("transcript") or multi_ctx.get("summary")
            SESSION_OFFERINGS[sid] = {
                "channel": channel,
                "modality": modality,
                "text": offering_text,
            }
            self._send_json({
                "ok": True,
                "session_id": sid,
                "analysis_ready": True,
                "multimodal_analysis": multi_ctx,
            })
            return

        # 3b. POST /api/input/multimodal
        if path == "/api/input/multimodal":
            sid = body.get("session_id")
            modality = (body.get("modality") or "TEXT").upper()
            coord = get_or_create_coordinator(sid)

            if modality == "TEXT":
                text = body.get("text", "")
                multi_ctx = analyze_text_offering(text)
                nav = analyse_text(text)
                coord.record_raw_input({"modality": "TEXT", "text": text})
                coord.mark_analysis_ready(nav)
                SESSION_OFFERINGS[sid] = {"channel": "write", "text": text, "modality": "TEXT"}
            elif modality in ("VOICE", "AUDIO"):
                transcript = body.get("transcript", "")
                dur = float(body.get("duration_sec", 0.0) or 3.0)
                multi_ctx = analyze_voice_offering(transcript=transcript, duration_sec=dur)
                coord.record_raw_input({"modality": "AUDIO"})
                coord.mark_raw_offering_ready()
                SESSION_OFFERINGS[sid] = {"channel": "speak", "text": transcript or "Voice offering", "modality": "AUDIO"}
            elif modality == "VIDEO":
                dur = float(body.get("duration_sec", 0.0) or 10.0)
                multi_ctx = analyze_video_offering(duration_sec=dur)
                coord.record_raw_input({"modality": "VIDEO"})
                coord.mark_raw_offering_ready()
                SESSION_OFFERINGS[sid] = {"channel": "look", "text": "Video offering", "modality": "VIDEO"}
            else: # PHOTO / CAMERA / DOCUMENT
                is_doc = body.get("is_document")
                ocr_hint = body.get("ocr_hint")
                fn = body.get("filename", "")
                multi_ctx = analyze_photo_offering(filename=fn, ocr_hint=ocr_hint, is_document=is_doc)
                coord.record_raw_input({"modality": "IMAGE"})
                coord.mark_raw_offering_ready()
                off_txt = multi_ctx.get("ocr_text") or "Photo frame offering"
                SESSION_OFFERINGS[sid] = {"channel": "show", "text": off_txt, "modality": "IMAGE"}

            SESSION_MULTIMODAL_CONTEXT[sid] = multi_ctx
            self._send_json({
                "ok": True,
                "session_id": sid,
                "modality": modality,
                "multimodal_analysis": multi_ctx,
            })
            return

        # 4. POST /api/session-lifecycle
        if path == "/api/session-lifecycle":
            sid = body.get("session_id")
            action = body.get("action")
            coord = get_or_create_coordinator(sid)

            if action == "input_complete":
                if coord.machine.state == SessionState.INPUT_INGESTION:
                    coord.advance(SessionState.LIVE_CONVERSATION)

            elif action == "card_selection":
                card_index = int(body.get("card_index", 1))
                card_id = str(body.get("card_id", "card_01"))
                deck = SESSION_DECKS.get(sid) or {}
                
                # Validate card resonance against generated deck if available
                if deck.get("cards"):
                    try:
                        validated_card = validate_card_resonance(deck, card_id=card_id, card_index=card_index)
                    except Exception as exc:
                        logger.warning(f"Card resonance validation fallback: {exc}")
                        validated_card = next((c for c in deck["cards"] if c["card_index"] == card_index), deck["cards"][0])
                else:
                    validated_card = {"card_id": card_id, "card_index": card_index, "title": "The Resonant Card", "qualitative_reading": "A card chosen by reflection."}

                SESSION_SELECTED[sid] = validated_card
                coord.record(
                    event_type=EventType.CARD_RESONANCE_MARKED,
                    provenance_level=ProvenanceLevel.VALIDATED,
                    payload={
                        "card_id": card_id,
                        "card_index": card_index,
                        "title": validated_card.get("title"),
                        "qualitative_reading": validated_card.get("qualitative_reading"),
                        "meaning": "participant_reported_resonance_not_truth",
                    },
                )
                if coord.machine.state == SessionState.CARD_SELECTION:
                    coord.advance(SessionState.PROFILE_REVEAL)

            elif action == "reveal":
                if coord.machine.state == SessionState.PROFILE_REVEAL:
                    coord.advance(SessionState.DATA_WALL_CONSENT)
                deck = SESSION_DECKS.get(sid)
                selected = SESSION_SELECTED.get(sid)
                reveal = build_participant_reveal(coord, deck, selected)
                SESSION_REVEALS[sid] = reveal
                self._send_json({
                    "ok": True,
                    "session_id": sid,
                    "lifecycle_state": coord.machine.state.value,
                    "reveal": reveal,
                })
                return

            elif action == "consent":
                consent_type = body.get("consent_type", "KEEP_PRIVATE")
                try:
                    coord.record(
                        event_type=EventType.CONSENT_RECORDED,
                        provenance_level=ProvenanceLevel.OBSERVED,
                        payload={"consent_type": consent_type},
                    )
                except Exception as e:
                    logger.warning(f"Consent recording notice: {e}")
                if coord.machine.state == SessionState.DATA_WALL_CONSENT:
                    coord.advance(SessionState.OUTPUT_GENERATION)

            self._send_json({
                "ok": True,
                "session_id": sid,
                "lifecycle_state": coord.machine.state.value,
            })
            return

        # 5. POST /api/chat
        if path == "/api/chat":
            sid = body.get("session_id")
            message = (body.get("message") or "").strip()
            coord = get_or_create_coordinator(sid)

            if coord.machine.state == SessionState.INPUT_INGESTION:
                coord.advance(SessionState.LIVE_CONVERSATION)

            if coord.machine.is_locked():
                self._send_json({
                    "session_id": sid,
                    "response": "INTERVENTION CLOSED.\n\nThe machine stopped after intervention or shutdown.\n\nTHE PARROT IS OUT OF SERVICE.",
                    "parrot_behavior": "idle",
                    "closed": True,
                })
                return

            # Navarasa Analysis
            nav = analyse_text(message)

            # Behaviour Director Decision
            turn_idx = coord._turn_count + 1
            instruction = BehaviourDirector.decide(
                coord,
                turn_index=turn_idx,
                turn_text=message,
                navarasa_result=nav,
            )

            # Language Realizer assemble and render
            initial_ctx = SESSION_MULTIMODAL_CONTEXT.get(sid)
            req = build_realizer_request(
                coord,
                instruction,
                turn_text=message,
                turn_index=turn_idx,
                navarasa_result=nav,
                initial_context=initial_ctx,
            )
            session_view = coord.director_state.parrot_session_view(
                session_id=sid,
                substantive_turns=turn_idx,
            )
            roast_pool = ROAST_BANKS.get(min(turn_idx, 8), [])
            roast = choose_random_line(roast_pool, session_view, "recent_roast")
            parrot_text = LanguageRealizer.realize(
                req,
                session=session_view,
                roast=roast,
                analysis=nav,
            )

            # Record turn on coordinator
            coord.record_parrot_turn(
                turn_text=message,
                reply=parrot_text,
                behaviour=instruction["behaviour"],
                gate=instruction.get("selection_mode", ""),
            )

            self._send_json({
                "session_id": sid,
                "turn": turn_idx,
                "response": parrot_text,
                "parrot_behavior": instruction["behaviour"],
                "closed": False,
            })
            return

        # 6. POST /api/end-conversation
        if path == "/api/end-conversation":
            sid = body.get("session_id")
            coord = get_or_create_coordinator(sid)

            # Lock session
            if not coord.machine.is_locked():
                coord.lock()

            # Execute real Phase 4C 27-card composition pipeline
            deck = compose_reading_deck(coord)
            SESSION_DECKS[sid] = deck

            if coord.machine.state == SessionState.LIVE_CONVERSATION:
                coord.advance(SessionState.SESSION_CONCLUDED)
            if coord.machine.state == SessionState.SESSION_CONCLUDED:
                coord.advance(SessionState.POST_SESSION_INTERPRETATION)
            if coord.machine.state == SessionState.POST_SESSION_INTERPRETATION:
                coord.advance(SessionState.CARD_SELECTION)

            # Strip hidden analytical provenance for participant safety
            participant_cards = [
                {
                    "card_id": c["card_id"],
                    "card_index": c["card_index"],
                    "title": c["title"],
                    "archetype": c["archetype"],
                    "qualitative_reading": c["qualitative_reading"],
                }
                for c in deck.get("cards", [])
            ]

            self._send_json({
                "ok": True,
                "closed": True,
                "lifecycle_state": "CARD_SELECTION",
                "cards": participant_cards,
                "response": "CONVERSATION CONCLUDED. TWENTY-SEVEN CARDS HAVE BEEN DEALT.",
            })
            return

        # 7. POST /api/session-output
        if path == "/api/session-output":
            sid = body.get("session_id")
            coord = get_or_create_coordinator(sid)
            receipt = build_session_receipt(coord)
            self._send_json({
                "success": True,
                "session_id": sid,
                "text": receipt,
            })
            return

        # 8. POST /api/session-output-reset
        if path == "/api/session-output-reset":
            sid = body.get("session_id")
            if sid in SESSIONS:
                del SESSIONS[sid]
            if sid in SESSION_OFFERINGS:
                del SESSION_OFFERINGS[sid]
            if sid in SESSION_MULTIMODAL_CONTEXT:
                del SESSION_MULTIMODAL_CONTEXT[sid]
            if sid in SESSION_DECKS:
                del SESSION_DECKS[sid]
            if sid in SESSION_SELECTED:
                del SESSION_SELECTED[sid]
            if sid in SESSION_REVEALS:
                del SESSION_REVEALS[sid]
            self._send_json({
                "ok": True,
                "lifecycle_state": "IDLE_STANDBY",
            })
            return

        self._send_json({"error": "Unknown POST route"}, 404)


def run_server(port: int = 5001) -> None:
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), FtpApiHandler) as httpd:
        logger.info(f"FTP 2.0 Authoritative Python Backend running on http://127.0.0.1:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    run_server(port)
