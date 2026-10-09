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
import socketserver
import json
import logging
import os
import re
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
from ftp.session.neon_persistence import build_neon_persistence
from ftp.session.states import SessionState
from ftp.silent_reader.reading.compose import compose_reading_deck
from ftp.silent_reader.reading.validate import validate_card_resonance
from ftp.input.multimodal_analyzer import (
    analyze_text_offering,
    analyze_voice_offering,
    analyze_photo_offering,
    analyze_video_offering,
)
from interface_server import ROAST_BY_LEVEL as ROAST_BANKS, choose_random_line
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
SESSION_CREATED_AT: dict[str, float] = {}
SESSION_TTL_SECONDS = max(60, int(os.environ.get("FTP_SESSION_TTL_SECONDS", "3600")))


def persist_artifact(coord: SessionCoordinator, session_id: str, artifact: str, value: Any) -> None:
    if coord._persistence is not None:
        coord._persistence.update_artifact(session_id, artifact, value)


def purge_expired_sessions(now: float | None = None) -> list[str]:
    """Purge expired in-memory and durable session state."""
    current = now if now is not None else time.time()
    expired = [sid for sid, created_at in SESSION_CREATED_AT.items()
               if current - created_at >= SESSION_TTL_SECONDS]
    for sid in expired:
        for store in (SESSIONS, SESSION_OFFERINGS, SESSION_MULTIMODAL_CONTEXT,
                      SESSION_DECKS, SESSION_SELECTED, SESSION_REVEALS, SESSION_CREATED_AT):
            store.pop(sid, None)
        logger.info("Purged expired in-memory FTP session: %s", sid)

    # Durable expiry is authoritative across backend restarts. When durable
    # sessions are enabled, a database failure must surface rather than silently
    # treating expired or inaccessible sessions as valid.
    persistence = build_neon_persistence()
    if persistence is not None:
        durable_expired = persistence.purge_expired_sessions()
        for sid in durable_expired:
            for store in (SESSIONS, SESSION_OFFERINGS, SESSION_MULTIMODAL_CONTEXT,
                          SESSION_DECKS, SESSION_SELECTED, SESSION_REVEALS, SESSION_CREATED_AT):
                store.pop(sid, None)
            if sid not in expired:
                expired.append(sid)
            logger.info("Purged expired durable FTP session: %s", sid)
    return expired


def create_session() -> SessionCoordinator:
    purge_expired_sessions()
    sid = f"ftp2_{int(time.time()*1000)}_{os.urandom(8).hex()}"
    # New sessions remain memory-only until the participant explicitly
    # chooses Memory Chest. Durable persistence is attached after consent.
    coord = SessionCoordinator(sid, persistence=None)
    coord.start()
    if os.environ.get("FTP_PARROT_VARIABILITY", "on").strip().lower() != "off":
        coord.director_state.randomize_temperament()
    SESSIONS[sid] = coord
    SESSION_CREATED_AT[sid] = time.time()
    logger.info("Created new session coordinator: %s", sid)
    return coord


def get_session(session_id: str | None) -> SessionCoordinator | None:
    purge_expired_sessions()
    if not session_id:
        return None
    sid = str(session_id)
    cached = SESSIONS.get(sid)
    if cached is not None:
        return cached
    persistence = build_neon_persistence()
    if persistence is None:
        return None
    try:
        events = persistence.load_events(sid)
        if not events:
            return None
        coord = SessionCoordinator(sid, persistence=persistence)
        coord.hydrate_from_persistence()
        artifacts = persistence.load_artifacts(sid) or {}
        for store, key in (
            (SESSION_OFFERINGS, "offerings"),
            (SESSION_MULTIMODAL_CONTEXT, "multimodal_context"),
            (SESSION_DECKS, "decks"),
            (SESSION_SELECTED, "selected"),
            (SESSION_REVEALS, "reveals"),
        ):
            value = artifacts.get(key)
            if value:
                store[sid] = value
        SESSIONS[sid] = coord
        SESSION_CREATED_AT.setdefault(sid, time.time())
        logger.info("Hydrated FTP session coordinator: %s", sid)
        return coord
    except Exception as exc:
        logger.warning("Could not hydrate FTP session %s: %s", sid, exc)
        return None


def require_session(session_id: str | None) -> SessionCoordinator:
    coord = get_session(session_id)
    if coord is None:
        raise KeyError("Session not found or expired")
    return coord


def get_or_create_coordinator(session_id: str | None) -> SessionCoordinator:
    """Backward-compatible name; unknown IDs are never silently created."""
    return require_session(session_id)


# Plain-language wording for limitation codes already emitted by the evidence/inference layers.
# Unknown codes are skipped, never guessed at.
_LIMITATION_TEXT: dict[str, str] = {
    "fewer_than_two_turns": "Whether anything changed across the conversation: there were fewer than two turns to compare.",
    "message_length_change_unavailable": "Whether your messages grew or shrank: this session gave no measurable change.",
    "question_rate_unavailable": "How often you asked questions: this could not be measured for this session.",
    "self_reference_unavailable": "How you referred to yourself: this could not be measured for this session.",
    "detected_rasa_unavailable": "Any stable emotional label: no turn contained lexicon evidence for one.",
    "defaulted_shanta_not_detected_evidence": "Turns labelled Shanta by default carry no evidence. A default is not a detection.",
    "engagement_state_insufficient": "How the interaction was going: there was not enough evidence to label it.",
    "response_latency_unavailable": "How quickly you replied: this session did not record a usable response time.",
    "no_eligible_inference": "Any claim about you: no claim met the evidence threshold in this session.",
    "bundle_insufficient": "A fuller reading: the session was too short to support one.",
    "interaction_state_not_a_person_claim": "Anything about you as a person from the interaction-state label: it describes this exchange only.",
    "contradiction_blocks_claim": "A claim that the session's own evidence contradicted.",
}


def _limitation_notes(codes: Any) -> list[str]:
    """Plain-language notes for the limitation codes attached to one evidence or inference record."""
    return [_LIMITATION_TEXT[c] for c in (codes or []) if c in _LIMITATION_TEXT]


def _participant_limitations(bundle: dict[str, Any], evaluation: dict[str, Any]) -> list[str]:
    """Epistemic limits the backend itself reports, in plain language, plus the evidence contract's prohibitions."""
    from ftp.silent_reader.inference import PROHIBITED_INFERENCE_CATEGORIES

    codes: list[str] = list(bundle.get("limitations") or [])
    for item in bundle.get("evidence_items") or []:
        codes.extend(item.get("limitations") or [])
    codes.extend(evaluation.get("limitations") or [])
    for record in evaluation.get("records") or []:
        codes.extend(record.get("limitations") or [])
    out: list[str] = []
    for code in codes:
        text = _LIMITATION_TEXT.get(code)
        if text and text not in out:
            out.append(text)
    categories = ", ".join(sorted(c.replace("_", " ") for c in PROHIBITED_INFERENCE_CATEGORIES))
    out.append(f"The evidence contract does not permit the system to infer: {categories}.")
    return out


def _session_archetype(interaction_profile: dict[str, Any], selection_pattern: dict[str, Any], trajectory: dict[str, Any]) -> dict[str, str]:
    """Create a session-scoped archetype from observed interaction and choices."""
    questions = float(interaction_profile.get("question_count") or 0)
    turns = max(float(interaction_profile.get("turn_count") or 1), 1.0)
    selection_count = float(selection_pattern.get("selected_count") or 0)
    question_density = questions / turns
    dominant = str(trajectory.get("dominant_rasa", {}).get("label") or "")
    if question_density >= 0.35 or dominant in {"Adbhuta", "Vira"}:
        return {"name": "The Curious Cartographer", "basis": "question density, exploratory turns, and selected territories"}
    if selection_count >= 3 or interaction_profile.get("readings_constructed", 0) >= 27:
        return {"name": "The Pattern Keeper", "basis": "breadth of interaction and the pattern of selected readings"}
    if interaction_profile.get("self_reference_mean") and float(interaction_profile["self_reference_mean"]) >= 0.2:
        return {"name": "The Inner Witness", "basis": "self-reference and reflective selection signals"}
    return {"name": "The Quiet Observer", "basis": "the measured shape of this single interaction"}


def build_participant_reveal(coord: SessionCoordinator, deck: dict[str, Any] | None, selected: dict[str, Any] | None) -> dict[str, Any]:
    """Assemble the dedicated participant-facing reveal payload preserving provenance."""
    sid = coord.session_id
    offering = SESSION_OFFERINGS.get(sid, {})
    events = coord.store.all_events()

    # 1. WHAT YOU GAVE: actual participant inputs
    dialogue_events = [e for e in events if e.event_type == EventType.PARROT_TURN_GENERATED]
    turn_texts = [str(e.payload.get("user_text") or "") for e in dialogue_events]
    offering_text = offering.get("text") or (turn_texts[0] if turn_texts else "")

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
        f"Session trace № {sid[-7:]}: counts and measurements taken from your text. Observed, not interpreted."
    )

    # 3. WHAT WAS INTERPRETED: expose the actual evidence-backed interpretation.
    # This is deliberately computed at reveal time from the locked session rather
    # than reconstructed from generic copy.
    trajectory: dict[str, Any] = {
        "detected_sequence": [],
        "dominant_rasa": {"label": None, "status": "insufficient_evidence"},
        "quality_limitations": {"status": "insufficient_evidence"},
    }
    try:
        from ftp.silent_reader.engagement import EngagementSynthesizer
        from ftp.silent_reader.inference import build_deep_reader_packet, evaluate_bundle
        from ftp.silent_reader.linguistic import LinguisticTrajectorySynthesizer
        from ftp.silent_reader.navarasa_trajectory import NavarasaTrajectorySynthesizer
        from ftp.silent_reader.trajectories import TemporalTrajectorySynthesizer

        bundle = coord.build_evidence_bundle()
        evaluation = evaluate_bundle(bundle)
        deep_reader_packet = build_deep_reader_packet(bundle, evaluation)
        linguistic = LinguisticTrajectorySynthesizer(coord).synthesize()
        temporal = TemporalTrajectorySynthesizer(coord).synthesize()
        engagement = EngagementSynthesizer(coord).synthesize()
        trajectory = NavarasaTrajectorySynthesizer(coord).synthesize()
        detected_seq = trajectory.get("detected_sequence", [])
        dominant = trajectory.get("dominant_rasa", {}).get("label")
        eligible = [
            item for item in evaluation.get("records", [])
            if item.get("eligibility") == "eligible"
        ]
        interpretations = [str(item.get("claim")) for item in eligible if item.get("claim")]
        evidence_items = bundle.get("evidence_items", [])
        evidence_count = len(evidence_items)
    except Exception as exc:
        logger.warning(f"Reveal analysis notice: {exc}")
        bundle = {}
        evaluation = {}
        deep_reader_packet = {}
        linguistic = {}
        temporal = {}
        engagement = {}
        detected_seq = []
        dominant = None
        interpretations = []
        evidence_count = 0

    trajectory_text = " → ".join(str(label) for label in detected_seq[:4]) or "no stable trajectory was available"
    interpretation_text = "; ".join(interpretations[:2]) or "no eligible session-specific inference was supported"
    what_interpreted_body = (
        f"The locked session contained {evidence_count} evidence item(s). "
        f"Its observed affective sequence was {trajectory_text}. "
        f"The evidence contract retained this interpretation: {interpretation_text}."
    )
    what_interpreted_sub = (
        f"Observed trajectory label: {dominant or 'unavailable'}. "
        "Interpretation is session-specific and is not a claim about the participant beyond this interaction."
    )

    # 4. WHAT WAS CONSTRUCTED: actual 27-card reading output and its provenance.
    deck_cards = (deck.get("cards") if deck else None) or []
    sample_archetypes = [c.get("archetype") for c in deck_cards[:4] if c.get("archetype")]
    archetype_str = ", ".join(sample_archetypes) if sample_archetypes else "no archetype output"
    what_constructed_body = (
        f"The locked reading composer produced {len(deck_cards)} card(s) from this session's "
        f"evidence-backed anchors, including {archetype_str}."
    )
    what_constructed_sub = (
        "Cards are INFERRED reflection hypotheses. Their hidden provenance retains the inference and evidence IDs; they are not diagnoses."
    )

    # 5. WHAT YOU CHOSE: preserve the participant's complete selection pattern.
    selected_cards = selected if isinstance(selected, list) else ([selected] if selected else [])
    selected_cards = [card for card in selected_cards if isinstance(card, dict)]
    first_selected = selected_cards[0] if selected_cards else None
    selection_pattern = {
        "selected_count": len(selected_cards),
        "selected_card_ids": [str(card.get("card_id", "")) for card in selected_cards],
        "selected_card_indices": [int(card.get("card_index", 0)) for card in selected_cards],
        "selection_order": [str(card.get("card_id", "")) for card in selected_cards],
        "semantic_anchors": [str(card.get("semantic_anchor")) for card in selected_cards if card.get("semantic_anchor")],
        "semantic_motifs": [str(card.get("semantic_motif")) for card in selected_cards if card.get("semantic_motif")],
        "archetypes": [str(card.get("archetype")) for card in selected_cards if card.get("archetype")],
        "categories": [str(card.get("category")) for card in selected_cards if card.get("category")],
        "reading_groups": [str(card.get("reading_group")) for card in selected_cards if card.get("reading_group")],
        "resonance_recorded": bool(selected_cards),
    }
    if first_selected:
        card_title = first_selected.get("title", "The Chosen Card")
        card_idx = first_selected.get("card_index") or first_selected.get("id") or 1
        card_reading = first_selected.get("qualitative_reading") or first_selected.get("statement") or ""
        what_chose = {
            "card_index": card_idx,
            "title": card_title,
            "statement": card_reading,
            "validation": "Resonance marked by participant (reported resonance, not objective diagnosis).",
        }
    else:
        what_chose = {
            "card_index": None,
            "title": None,
            "statement": None,
            "validation": "No card resonance was recorded for this session.",
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

    limitations = _participant_limitations(bundle, evaluation)

    observed_signals = [
        {
            "evidence_id": item.get("evidence_id"),
            "signal_type": item.get("signal_type"),
            "value": item.get("value"),
            "observation": item.get("observation"),
            "source_event_ids": item.get("source_event_ids", []),
            "provenance_level": item.get("provenance_level"),
            "scope": item.get("scope"),
            "limitations": item.get("limitations", []),
            "limitation_notes": _limitation_notes(item.get("limitations")),
            "eligibility": item.get("eligibility", "observed"),
        }
        for item in evidence_items
    ]
    inference_records = [
        {**record, "limitation_notes": _limitation_notes(record.get("limitations"))}
        for record in (evaluation.get("records") or [])
    ]
    card_provenance = [
        {
            "card_id": card.get("card_id"),
            "card_index": card.get("card_index"),
            "title": card.get("title"),
            "semantic_anchor": card.get("semantic_anchor"),
            "semantic_motif": card.get("semantic_motif"),
            "archetype": card.get("archetype"),
            "qualitative_reading": card.get("qualitative_reading"),
            "provenance_level": card.get("provenance_level"),
            "provenance": card.get("hidden_provenance") or {},
            "selection_state": "selected" if card.get("card_id") in selection_pattern["selected_card_ids"] else "not_selected",
        }
        for card in deck_cards
    ]
    selection_pattern.update({
        "total_cards_presented": len(deck_cards),
        "cards_inspected": None,
        "selection_status": "participant_reported" if selected_cards else "no_selection_recorded",
        "group_distribution": {
            group: selection_pattern["reading_groups"].count(group)
            for group in dict.fromkeys(selection_pattern["reading_groups"])
        },
    })
    navarasa_sufficient = bool(detected_seq)
    def _traj(source: dict[str, Any], key: str) -> dict[str, Any]:
        value = source.get(key) if isinstance(source, dict) else None
        return value if isinstance(value, dict) else {}

    latency = _traj(temporal, "response_latency_trajectory")
    gap = _traj(temporal, "inter_turn_gap_trajectory")
    variation = _traj(_traj(temporal, "volatility"), "message_length")
    interaction_profile = {
        "input_modality": offering.get("modality"),
        "turn_count": turn_count,
        "question_count": question_count,
        "character_count": total_chars,
        "question_density": _traj(linguistic, "question_rate").get("value"),
        "self_reference_mean": _traj(linguistic, "self_reference_trajectory").get("mean"),
        "repetition_count": _traj(temporal, "repetition").get("repetition_count"),
        "message_length_variation": variation.get("normalized_variation"),
        "response_latency_mean_seconds": latency.get("mean") if latency.get("status") == "ok" else None,
        "inter_turn_gap_mean_seconds": gap.get("mean") if gap.get("status") == "ok" else None,
        "interaction_state": _traj(engagement, "engagement_state").get("state"),
        "navarasa_status": "ok" if navarasa_sufficient else "insufficient_evidence",
        "evidence_count": evidence_count,
        "eligible_inference_count": len(eligible),
        "readings_constructed": len(deck_cards),
        "card_selection_count": len(selected_cards) if isinstance(selected, list) else int(bool(selected)),
        "resonance": "participant-reported" if selected_cards else "none recorded",
        "card_selection_pattern": "participant-reported selection pattern; not psychological validation",
    }
    session_archetype = _session_archetype(interaction_profile, selection_pattern, trajectory)

    return {
        "session_id": sid,
        "what_you_gave": offering_text,
        "what_you_gave_channel": offering.get("modality"),
        "machine_transformation": {
            "raw_text": {"character_count": total_chars, "turn_count": turn_count},
            "turn_sequence": [int(e.payload.get("turn_index", i)) for i, e in enumerate(dialogue_events)],
            "evidence_ids": [item["evidence_id"] for item in evidence_items],
            "inference_ids": [item.get("inference_id") for item in eligible],
        },
        "observed_signals": observed_signals,
        "analytical_artifacts": {
            "linguistic": linguistic,
            "temporal": temporal,
            "engagement": engagement,
            "navarasa": trajectory,
            "evidence_bundle": bundle,
            "inference_evaluation": evaluation,
            "deep_reader_packet": deep_reader_packet,
        },
        "inference_records": inference_records,
        "card_provenance": card_provenance,
        "navarasa_trajectory": trajectory,
        "interaction_profile": interaction_profile,
        "session_archetype": session_archetype,
        "turn_texts": turn_texts,
        "what_was_recorded": what_recorded_body,
        "what_the_system_observed": what_recorded_body,
        "what_was_recorded_sub": what_recorded_sub,
        "what_was_interpreted": what_interpreted_body,
        "what_the_system_interpreted": what_interpreted_body,
        "what_was_interpreted_sub": what_interpreted_sub,
        "what_was_constructed": what_constructed_body,
        "what_the_system_inferred": what_constructed_body,
        "what_was_constructed_sub": what_constructed_sub,
        "what_you_chose": what_chose,
        "selection_pattern": selection_pattern,
        "what_we_cannot_know": list(dict.fromkeys(limitations)),
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
    # Normalize legacy and current selection shapes before rendering the receipt.
    # Older sessions can contain nested lists or an empty/non-dict selection.
    selected_cards = selected if isinstance(selected, list) else ([selected] if selected else [])
    selected_cards = [card for card in selected_cards if isinstance(card, dict)]
    selected_card = selected_cards[0] if selected_cards else None

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
        f"CARD: {selected_card.get('title', 'None Selected') if isinstance(selected_card, dict) else 'None Selected'}",
        f"READING: {selected_card.get('qualitative_reading', '') if isinstance(selected_card, dict) else ''}",
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
        purge_expired_sessions()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            self._send_json({"ok": True, "service": "ftp_backend", "status": "online"})
            return

        if path == "/api/session-reveal":
            sid = query.get("session_id", [""])[0]
            coord = get_session(sid)
            if not coord:
                self._send_json({"error": "Session not found or expired"}, 404)
                return
            deck = SESSION_DECKS.get(sid)
            selected = SESSION_SELECTED.get(sid)
            reveal = SESSION_REVEALS.get(sid) or build_participant_reveal(coord, deck, selected)
            SESSION_REVEALS[sid] = reveal
            persist_artifact(coord, sid, "reveals", reveal)
            self._send_json({"ok": True, "session_id": sid, "reveal": reveal})
            return

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        try:
            self._handle_post()
        except KeyError:
            self._send_json({"error": "Session not found or expired"}, 404)
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
            coord = create_session()
            sid = coord.session_id
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
            persist_artifact(coord, sid, "multimodal_context", multi_ctx)
            SESSION_OFFERINGS[sid] = {"channel": "write", "text": text, "modality": "TEXT"}
            persist_artifact(coord, sid, "offerings", SESSION_OFFERINGS[sid])
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
            transcript = str(body.get("transcript") or "").strip()
            face_detected = body.get("face_detected")
            expression_cues = body.get("expression_cues")

            coord = get_or_create_coordinator(sid)
            coord.record_raw_input({"modality": modality})
            coord.mark_raw_offering_ready()

            if modality in ("AUDIO", "VOICE", "SPEAK"):
                multi_ctx = analyze_voice_offering(transcript=transcript or "Voice offering received.", duration_sec=duration_sec or 3.5)
                channel = "speak"
            elif modality in ("VIDEO",):
                multi_ctx = analyze_video_offering(
                    duration_sec=duration_sec or 15.0,
                    face_detected=face_detected,
                    expression_cues=expression_cues if isinstance(expression_cues, list) else None,
                )
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
                self._send_json({
                    "ok": True,
                    "session_id": sid,
                    "lifecycle_state": coord.machine.state.value,
                })
                return

            elif action == "card_selection":
                raw_cards = body.get("cards") or [{"card_index": body.get("card_index", 1), "card_id": body.get("card_id", "card_01")}]
                if not isinstance(raw_cards, list) or not raw_cards:
                    raise ValueError("At least one resonant card is required")
                deck = SESSION_DECKS.get(sid) or {}
                selected_cards = []
                
                # Validate every resonant card against this session's generated deck.
                for order, item in enumerate(raw_cards, start=1):
                    card_index = int(item.get("card_index", 1))
                    card_id = str(item.get("card_id", f"card_{card_index:02d}"))
                    if deck.get("cards"):
                        try:
                            validated_card = validate_card_resonance(deck, card_id=card_id, card_index=card_index)
                        except Exception as exc:
                            logger.warning(f"Card resonance validation fallback: {exc}")
                            # Never pass an unvalidated generated card to the participant
                            # path: a malformed card may contain analytical provenance.
                            validated_card = {
                                "card_id": card_id,
                                "card_index": card_index,
                                "title": "The Resonant Card",
                                "qualitative_reading": "A moment of reflection, held without conclusion.",
                                "meaning": "participant_reported_resonance_not_truth",
                            }
                    else:
                        validated_card = {"card_id": card_id, "card_index": card_index, "title": "The Resonant Card", "qualitative_reading": "A card chosen by reflection."}
                    selected_cards.append({**validated_card, "selection_order": order})

                # One participant-level confirmation represents the complete set.
                # Card identity/order remain in the payload; resonance is not emitted per card.
                coord.record(
                    event_type=EventType.CARD_RESONANCE_MARKED,
                    provenance_level=ProvenanceLevel.VALIDATED,
                    payload={
                        "selected_cards": [
                            {"card_id": card.get("card_id"), "card_index": card.get("card_index"), "selection_order": card.get("selection_order")}
                            for card in selected_cards
                        ],
                        "selected_count": len(selected_cards),
                        "meaning": "participant_reported_resonance_not_truth",
                    },
                )
                SESSION_SELECTED[sid] = selected_cards
                persist_artifact(coord, sid, "selected", selected_cards)
                if coord.machine.state == SessionState.CARD_SELECTION:
                    coord.advance(SessionState.PROFILE_REVEAL)
                self._send_json({
                    "ok": True,
                    "session_id": sid,
                    "lifecycle_state": coord.machine.state.value,
                })
                return

            elif action == "reveal":
                if coord.machine.state == SessionState.PROFILE_REVEAL:
                    coord.advance(SessionState.DATA_WALL_CONSENT)
                deck = SESSION_DECKS.get(sid)
                selected = SESSION_SELECTED.get(sid)
                reveal = build_participant_reveal(coord, deck, selected)
                SESSION_REVEALS[sid] = reveal
                persist_artifact(coord, sid, "reveals", reveal)
                self._send_json({
                    "ok": True,
                    "session_id": sid,
                    "lifecycle_state": coord.machine.state.value,
                    "reveal": reveal,
                })
                return

            elif action == "consent":
                requested = str(body.get("consent_type", "KEEP_PRIVATE")).strip().upper()
                if requested in {"SHARE", "WALL", "MEMORY_CHEST"}:
                    consent_type = "SHARE"
                elif requested in {"PRIVATE", "KEEP_PRIVATE"}:
                    consent_type = "KEEP_PRIVATE"
                else:
                    self._send_json({"error": "Unsupported consent choice"}, 400)
                    return

                if coord._persistence is not None:
                    persistence = coord._persistence
                else:
                    try:
                        persistence = build_neon_persistence()
                    except RuntimeError:
                        # A fresh memory-only session can still be kept private
                        # even if optional durable storage is misconfigured.
                        persistence = None
                if consent_type == "SHARE" and persistence is None:
                    self._send_json({
                        "error": "Memory Chest storage is not configured; no data was archived.",
                        "code": "MEMORY_CHEST_UNAVAILABLE",
                    }, 503)
                    return

                existing_consent = any(
                    event.event_type == EventType.CONSENT_RECORDED
                    and str(event.payload.get("consent_type", "")).upper() == consent_type
                    for event in coord.store.all_events()
                )

                if consent_type == "KEEP_PRIVATE":
                    # Remove any legacy durable record before recording the
                    # private choice; do not persist the private consent event.
                    if coord._persistence is not None:
                        coord._persistence.delete_session(sid)
                        coord.deactivate_persistence()
                    elif persistence is not None:
                        # Also erase a durable row if this session was written by
                        # an older version of the backend before this consent.
                        persistence.delete_session(sid)
                    if not existing_consent:
                        coord.record(
                            event_type=EventType.CONSENT_RECORDED,
                            provenance_level=ProvenanceLevel.OBSERVED,
                            payload={"consent_type": consent_type},
                        )
                else:
                    if coord._persistence is not None:
                        # Compatibility for a session hydrated from an older
                        # durable archive: record the final choice idempotently.
                        recorded = coord._persistence.record_consent(
                            sid, "SHARE", finalization=True
                        )
                        if recorded and not existing_consent:
                            coord.record(
                                event_type=EventType.CONSENT_RECORDED,
                                provenance_level=ProvenanceLevel.OBSERVED,
                                payload={"consent_type": "SHARE"},
                            )
                    else:
                        # Stage the consent event in memory first so the new
                        # archive transaction includes the decision authorizing it.
                        if not existing_consent:
                            coord.record(
                                event_type=EventType.CONSENT_RECORDED,
                                provenance_level=ProvenanceLevel.OBSERVED,
                                payload={"consent_type": "SHARE"},
                            )
                        expires_at = time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ",
                            time.gmtime(SESSION_CREATED_AT.get(sid, time.time()) + SESSION_TTL_SECONDS),
                        )
                        artifacts = {
                            # The reveal is the participant-facing Data Showdown
                            # snapshot. Do not archive raw offerings or multimodal inputs.
                            "offerings": None,
                            "multimodal_context": None,
                            "decks": SESSION_DECKS.get(sid),
                            "selected": SESSION_SELECTED.get(sid),
                            "reveals": SESSION_REVEALS.get(sid),
                            "state": {"lifecycle_state": coord.machine.state.value},
                        }
                        persistence.persist_approved_archive(
                            sid,
                            expires_at,
                            list(coord.store.all_events()),
                            artifacts,
                            consent_type="SHARE",
                        )
                        coord.activate_persistence(persistence)

                if coord.machine.state == SessionState.DATA_WALL_CONSENT:
                    coord.advance(SessionState.OUTPUT_GENERATION)

                self._send_json({
                    "ok": True,
                    "session_id": sid,
                    "lifecycle_state": coord.machine.state.value,
                    "archived": consent_type == "SHARE" and persistence is not None,
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
            coord.record_turn_analysis(turn_index=turn_idx, analysis=nav)
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
                analysis_snapshot=nav,
                decision_metadata={
                    "selection_mode": instruction.get("selection_mode", ""),
                    "behaviour_intensity": instruction.get("behaviour_intensity", ""),
                    "directive": instruction.get("directive"),
                },
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
            persist_artifact(coord, sid, "decks", deck)

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
                    "semantic_anchor": c.get("semantic_anchor"),
                    "semantic_motif": c.get("semantic_motif"),
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
            for store in (SESSIONS, SESSION_OFFERINGS, SESSION_MULTIMODAL_CONTEXT,
                          SESSION_DECKS, SESSION_SELECTED, SESSION_REVEALS, SESSION_CREATED_AT):
                store.pop(sid, None)
            self._send_json({
                "ok": True,
                "lifecycle_state": "IDLE_STANDBY",
            })
            return

        self._send_json({"error": "Unknown POST route"}, 404)


def run_server(port: int | None = None) -> None:
    socketserver.TCPServer.allow_reuse_address = True
    # Render and other managed services route traffic to the process over the
    # container network, so the production default must not be loopback-only.
    bind_host = os.environ.get("FTP_BIND_HOST", "0.0.0.0")
    bind_port = port if port is not None else int(os.environ.get("PORT", "5000"))
    with socketserver.ThreadingTCPServer((bind_host, bind_port), FtpApiHandler) as httpd:
        logger.info("FTP 2.0 backend running on http://%s:%s", bind_host, bind_port)
        httpd.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_server(port)
