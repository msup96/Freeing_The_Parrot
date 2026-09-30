"""Silent Reader — derive OBSERVED features from the event timeline."""

from __future__ import annotations

import datetime
import hashlib
import re
from typing import TYPE_CHECKING

from ftp.events.model import EventType, InteractionEvent
from ftp.silent_reader.features import build_derived_feature_payload

if TYPE_CHECKING:
    from ftp.session.coordinator import SessionCoordinator

_SELF_REF_PATTERN = re.compile(r"\b(I|me|my|myself|mine)\b", re.IGNORECASE)


def _parse_ts(iso: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(iso)


def _seconds_between(earlier: str, later: str) -> float:
    delta = _parse_ts(later) - _parse_ts(earlier)
    return max(0.0, delta.total_seconds())


class TimelineAnalyzer:
    """Read-only pass over EventStore; writes OBSERVED features via coordinator."""

    def __init__(self, coordinator: SessionCoordinator) -> None:
        self._coordinator = coordinator
        self._processed_through_sequence: int = 0

    def analyze_pending(self) -> list[InteractionEvent]:
        """Process new timeline events once; return recorded feature events."""
        store = self._coordinator.store
        all_events = store.all_events()
        new_events = [
            e for e in all_events
            if e.sequence_num > self._processed_through_sequence
        ]
        if not new_events:
            return []

        recorded: list[InteractionEvent] = []
        parrot_turns = [
            e for e in all_events
            if e.event_type == EventType.PARROT_TURN_GENERATED
        ]

        for event in new_events:
            if event.event_type == EventType.PARROT_TURN_GENERATED:
                recorded.extend(
                    self._derive_from_parrot_turn(event, all_events, parrot_turns)
                )
            elif event.event_type == EventType.INPUT_RAW_INGESTED:
                if event.payload.get("modality") != "TEXT":
                    recorded.extend(self._derive_from_raw_ingest(event))

        if new_events:
            self._processed_through_sequence = max(
                e.sequence_num for e in new_events
            )
        return recorded

    def _already_derived_for(self, source_event_id: str, feature: str) -> bool:
        for event in self._coordinator.store.events_of_type(
            EventType.TELEMETRY_RECORDED
        ):
            payload = event.payload
            if payload.get("observation_type") != "derived":
                continue
            if payload.get("feature") != feature:
                continue
            if source_event_id in payload.get("source_event_ids", []):
                return True
        return False

    def _record_feature(
        self,
        feature: str,
        value,
        unit: str,
        source_event_ids: list[str],
        turn_index: int | None,
    ) -> InteractionEvent | None:
        if source_event_ids and self._already_derived_for(
            source_event_ids[0], feature
        ):
            return None
        payload = build_derived_feature_payload(
            feature,
            value,
            unit,
            source_event_ids,
            turn_index=turn_index,
        )
        return self._coordinator.record_silent_reader_observation(payload)

    def _derive_from_parrot_turn(
        self,
        parrot_event: InteractionEvent,
        all_events: tuple[InteractionEvent, ...],
        parrot_turns: list[InteractionEvent],
    ) -> list[InteractionEvent]:
        recorded: list[InteractionEvent] = []
        user_text = str(parrot_event.payload.get("user_text") or "")
        turn_index = int(parrot_event.payload.get("turn_index", 0))
        source_ids = [parrot_event.event_id]

        preceding_raw = self._find_preceding_text_raw(
            parrot_event, all_events
        )
        if preceding_raw is not None:
            source_ids = [preceding_raw.event_id, parrot_event.event_id]
            latency = _seconds_between(
                preceding_raw.timestamp,
                parrot_event.timestamp,
            )
            ev = self._record_feature(
                "response_latency",
                round(latency, 3),
                "seconds",
                source_ids,
                turn_index,
            )
            if ev:
                recorded.append(ev)

        length = len(user_text)
        ev = self._record_feature(
            "message_length",
            length,
            "characters",
            [parrot_event.event_id],
            turn_index,
        )
        if ev:
            recorded.append(ev)

        is_question = user_text.strip().endswith("?")
        ev = self._record_feature(
            "utterance_is_question",
            is_question,
            "boolean",
            [parrot_event.event_id],
            turn_index,
        )
        if ev:
            recorded.append(ev)

        self_refs = len(_SELF_REF_PATTERN.findall(user_text))
        ev = self._record_feature(
            "self_reference_count",
            self_refs,
            "count",
            [parrot_event.event_id],
            turn_index,
        )
        if ev:
            recorded.append(ev)

        text_hash = hashlib.sha256(user_text.encode("utf-8")).hexdigest()
        prior_hashes = [
            hashlib.sha256(
                str(p.payload.get("user_text") or "").encode("utf-8")
            ).hexdigest()
            for p in parrot_turns
            if p.sequence_num < parrot_event.sequence_num
        ]
        ev = self._record_feature(
            "repeated_message",
            text_hash in prior_hashes,
            "boolean",
            [parrot_event.event_id],
            turn_index,
        )
        if ev:
            recorded.append(ev)

        prior_parrot = [
            p for p in parrot_turns if p.sequence_num < parrot_event.sequence_num
        ]
        if prior_parrot:
            gap = _seconds_between(
                prior_parrot[-1].timestamp,
                parrot_event.timestamp,
            )
            ev = self._record_feature(
                "inter_turn_gap",
                round(gap, 3),
                "seconds",
                [prior_parrot[-1].event_id, parrot_event.event_id],
                turn_index,
            )
            if ev:
                recorded.append(ev)

        return recorded

    def _derive_from_raw_ingest(
        self, raw_event: InteractionEvent
    ) -> list[InteractionEvent]:
        modality = str(raw_event.payload.get("modality") or "")
        ev = self._record_feature(
            "multimodal_ingest",
            modality,
            "modality",
            [raw_event.event_id],
            None,
        )
        return [ev] if ev else []

    @staticmethod
    def _find_preceding_text_raw(
        parrot_event: InteractionEvent,
        all_events: tuple[InteractionEvent, ...],
    ) -> InteractionEvent | None:
        for event in reversed(all_events):
            if event.sequence_num >= parrot_event.sequence_num:
                continue
            if event.event_type != EventType.INPUT_RAW_INGESTED:
                continue
            if event.payload.get("modality") == "TEXT":
                return event
        return None
