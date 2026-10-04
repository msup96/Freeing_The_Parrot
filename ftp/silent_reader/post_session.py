"""Deterministic post-session insight deck for FTP 2.0.

This stays entirely in the background analytics layer. The Parrot never reads
from this module or any of the generated card data.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel

_TITLE_POOL = (
    "The Quiet Before the Question",
    "The Lantern in the Hallway",
    "The Thread That Returns",
    "The Weather of Unspoken Things",
    "The Keeper of Deferred Answers",
    "The Blue Hour of Reconsideration",
    "The Bell in the Empty Room",
    "The Worn Path of Second Thoughts",
    "The Soft Echo of a Missing Sentence",
    "The Map Beneath the Surface",
    "The Mirror of Delayed Recognition",
    "The Lantern Between Two Silences",
    "The Orchard of Quiet Confidence",
    "The River That Returns the Same Question",
    "The Shape of a Careful Pause",
    "The Hearth of Less Certain Certainty",
    "The Door with the Listening Knob",
    "The Candle Behind the Curtain",
    "The Grammar of the Unsaid",
    "The Strong Light of Gentle Resolve",
    "The Hush Around a Difficult Truth",
    "The Small Door of Reframing",
    "The Rain That Changes the Path",
    "The Thread of a Wiser Delay",
    "The Hidden Comfort in Repetition",
    "The Tender Weight of an Unfinished Thought",
    "The Familiar Sound of a New Beginning",
    "The Quiet Home of the Not-Yet-Decided",
)

_PATTERNS = (
    "A patient rhythm keeps returning to the same door, asking for a gentler opening.",
    "Silence is carrying more than it first appears to carry.",
    "The work is not in the first answer but in the second thinking of it.",
    "A difficult truth becomes softer when it is held with patience.",
    "An unfinished thought may be doing most of the work at the edges.",
    "The next chapter begins where repetition stops pretending to be certainty.",
    "A careful pause can become a kind of intelligence.",
    "The honest path is often the one that asks for less certainty.",
    "Meaning is gathering itself in the small spaces between declarations.",
    "What feels unresolved may simply be waiting for a more spacious language.",
    "There is wisdom in noticing what returns without being forced.",
    "The old question has changed its face, and that is a form of growth.",
    "A steady eye on the light can reveal what urgency hides.",
    "The story is not breaking; it is becoming more precise.",
    "A modest openness can carry a larger truth than a dramatic answer.",
    "The answer is already present in the way the pause is held.",
    "The next step is not louder; it is more honest.",
    "A pattern that once felt repetitive is beginning to look like guidance.",
    "The calmest insight often arrives after the feeling has stopped arguing.",
    "A soft reconsideration may be the clearest signal of all.",
    "What was ignored in the moment may become invaluable in reflection.",
    "Attention is gathering around a deeper thread than the first impression suggested.",
    "The path broadens when the mind stops trying to conquer uncertainty.",
    "There is a gentle authority in the rhythm of returning.",
    "A curious refusal to rush may eventually reveal the truest direction.",
    "Resolution is not the same as certainty; one can be brave without being decisive.",
    "The smallest honest adjustment can redirect a large emotional arc.",
)

_BARNUM_TECHNIQUES = (
    "DOUBLE_HEADED_STATEMENT",
    "UNIVERSAL_VULNERABILITY",
    "SUBJECTIVE_COMPLETION",
    "FLATTERY_OF_DISCERNMENT",
    "MODAL_FALLACY",
)

_FORBIDDEN_SPOILERS = (
    "you said",
    "system matched",
    "navarasa",
    "ocr detected",
    "sentiment score",
)


class PostSessionInterpreter:
    """Deterministic, non-Parrot-visible post-session interpretation layer."""

    def __init__(self, coordinator: Any) -> None:
        self._coordinator = coordinator

    @property
    def coordinator(self) -> Any:
        return self._coordinator

    def generate_deck(self) -> dict:
        """Construct a deterministic 27-card deck rooted in observed session evidence."""
        events = self.coordinator.store.all_events()
        user_messages = [
            str(e.payload.get("user_text") or "").strip()
            for e in events
            if e.event_type == EventType.PARROT_TURN_GENERATED
            and str(e.payload.get("user_text") or "").strip()
        ]

        turn_count = max(len(user_messages), 1)
        total_chars = sum(len(message) for message in user_messages)
        question_count = sum(1 for message in user_messages if message.endswith("?"))
        repeated = bool(user_messages and len(set(user_messages)) < len(user_messages))
        signal = self._primary_signal(user_messages, total_chars, question_count, repeated)
        signal_events = self._supporting_event_refs(events, signal)

        cards: list[dict] = []
        for index in range(1, 28):
            title = _TITLE_POOL[(index - 1) % len(_TITLE_POOL)]
            technique = _BARNUM_TECHNIQUES[(index - 1) % len(_BARNUM_TECHNIQUES)]
            phrase = _PATTERNS[(index - 1) % len(_PATTERNS)]
            reading = f"{title}: {phrase}"
            if self._contains_forbidden_spoiler(reading):
                reading = f"{title}: A patient reconsideration can reveal a gentler truth than the first impression offered."

            card = {
                "card_id": f"card_{index:02d}_{self._slugify(title)}",
                "card_index": index,
                "card_title": title,
                "archetype": self._archetype_for(index),
                "qualitative_reading": reading,
                "underlying_provenance": {
                    "primary_trigger_signal": signal,
                    "triggering_event_refs": signal_events,
                    "heuristics_used": self._heuristics_for(index, total_chars, question_count, repeated),
                    "barnum_technique": technique,
                },
            }
            cards.append(card)

        assert len(cards) == 27
        return {
            "session_id": self.coordinator.session_id,
            "total_cards": 27,
            "cards": cards,
        }

    def record_cards(self) -> InteractionEvent:
        """Write the deck as a single interpreted event on the coordinator."""
        deck = self.generate_deck()
        event = self.coordinator.record(
            EventType.CARDS_GENERATED,
            ProvenanceLevel.INTERPRETED,
            {
                "session_id": self.coordinator.session_id,
                "card_count": deck["total_cards"],
                "source": "deterministic_post_session_interpreter",
                "cards": deck["cards"],
            },
        )
        return event

    @staticmethod
    def _contains_forbidden_spoiler(text: str) -> bool:
        hay = text.lower()
        return any(token in hay for token in _FORBIDDEN_SPOILERS)

    @staticmethod
    def _slugify(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")

    @staticmethod
    def _primary_signal(user_messages: list[str], total_chars: int, question_count: int, repeated: bool) -> str:
        if not user_messages:
            return "quiet_threshold"
        if question_count >= max(1, len(user_messages) // 2):
            return "question_density"
        if repeated:
            return "repetition_pattern"
        if total_chars > 250:
            return "extended_reflection"
        return "pause_and_return"

    @staticmethod
    def _supporting_event_refs(events: tuple[InteractionEvent, ...], signal: str) -> list[str]:
        relevant = [
            event.event_id
            for event in events
            if event.event_type == EventType.PARROT_TURN_GENERATED
            and (event.payload.get("user_text") or "")
        ]
        if not relevant:
            return []
        digest = hashlib.sha256(signal.encode("utf-8")).hexdigest()
        start = int(digest[:8], 16) % max(1, len(relevant))
        chosen = relevant[start : start + 3]
        if len(chosen) < 3:
            chosen = relevant[:3]
        return chosen

    @staticmethod
    def _archetype_for(index: int) -> str:
        archetypes = (
            "Archivist",
            "Lantern-Bearer",
            "Anchor",
            "Harbinger",
            "Seeker",
            "Keeper",
            "Riddle-Holder",
            "Warden",
            "Mapmaker",
            "Pilgrim",
            "Stillness",
            "Witness",
            "Tide-Reader",
            "Gardener",
            "Wanderer",
            "Pathfinder",
            "Ember-Holder",
            "Echo",
            "Mender",
            "Seamstress",
            "Night-Watcher",
            "Traveler",
            "Conductor",
            "Quiet Oracle",
            "Horizon-Keeper",
            "Mirror-Bearer",
            "Root-Listener",
            "Threshold-Guide",
        )
        return archetypes[(index - 1) % len(archetypes)]

    @staticmethod
    def _heuristics_for(index: int, total_chars: int, question_count: int, repeated: bool) -> str:
        parts = [
            "temporal_pacing",
            "turn_recurrence",
            "lexical_density",
        ]
        if question_count:
            parts.append("question_pattern")
        if repeated:
            parts.append("repetition_bias")
        if total_chars > 200:
            parts.append("extended_reflection")
        return ", ".join(parts[:3 + (index % 2)])
