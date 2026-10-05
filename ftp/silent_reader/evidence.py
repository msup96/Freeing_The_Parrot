"""Curated post-lock evidence bundle for Phase 4A.

Consumes Phase 3 trajectory objects. Does not remeasure them and does not
write events. The Parrot never receives this object.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ftp.events.model import ProvenanceLevel

if TYPE_CHECKING:
    from ftp.session.coordinator import SessionCoordinator


class EvidenceBundleBuilder:
    """Aggregate existing synthesizer outputs into evidence items."""

    def __init__(self, coordinator: SessionCoordinator) -> None:
        self._coordinator = coordinator

    def build(self) -> dict[str, Any]:
        from ftp.silent_reader.engagement import EngagementSynthesizer
        from ftp.silent_reader.linguistic import LinguisticTrajectorySynthesizer
        from ftp.silent_reader.navarasa_trajectory import NavarasaTrajectorySynthesizer
        from ftp.silent_reader.trajectories import TemporalTrajectorySynthesizer

        temporal = TemporalTrajectorySynthesizer(self._coordinator).synthesize()
        linguistic = LinguisticTrajectorySynthesizer(self._coordinator).synthesize()
        navarasa = NavarasaTrajectorySynthesizer(self._coordinator).synthesize()
        engagement = EngagementSynthesizer(self._coordinator).synthesize()

        items: list[dict[str, Any]] = []
        limitations: list[str] = []
        turn_count = len(temporal["turn_sequence"])
        if turn_count < 2:
            limitations.append("fewer_than_two_turns")

        length = temporal["message_length_trajectory"]
        if length["status"] == "ok" and length["change"]["status"] == "ok":
            items.append(_item(
                "message_length",
                "Message length changed between the first and last turn.",
                {
                    "first": length["first"],
                    "final": length["final"],
                    "direction": length["change"]["direction"],
                    "absolute": length["change"]["absolute"],
                },
                length["source_event_ids"],
                ProvenanceLevel.OBSERVED.value,
                [],
            ))
        else:
            limitations.append("message_length_change_unavailable")

        question = linguistic["question_rate"]
        if question["status"] == "ok":
            items.append(_item(
                "question_rate",
                "Share of turns that end with a question mark.",
                {
                    "value": question["value"],
                    "question_turns": question["question_turns"],
                    "turn_count": question["turn_count"],
                },
                question["source_event_ids"],
                ProvenanceLevel.OBSERVED.value,
                [],
            ))
        else:
            limitations.append("question_rate_unavailable")

        repetition = temporal["repetition"]
        items.append(_item(
            "repetition",
            "Count of turns whose text repeated an earlier turn.",
            {"repetition_count": repetition["repetition_count"]},
            repetition["source_event_ids"],
            ProvenanceLevel.OBSERVED.value,
            [] if turn_count else ["no_turns"],
        ))

        self_ref = linguistic["self_reference_trajectory"]
        if self_ref["status"] == "ok":
            items.append(_item(
                "self_reference",
                "Self-reference token counts across turns.",
                {
                    "first": self_ref["first"],
                    "final": self_ref["final"],
                    "mean": self_ref["mean"],
                },
                self_ref["source_event_ids"],
                ProvenanceLevel.OBSERVED.value,
                [],
            ))
        else:
            limitations.append("self_reference_unavailable")

        detected = list(navarasa["detected_sequence"])
        if detected:
            items.append(_item(
                "detected_rasa",
                "Detected Rasa labels only. Defaulted Shanta is excluded.",
                {
                    "detected_sequence": detected,
                    "beginning": navarasa["beginning_rasa"]["label"],
                    "ending": navarasa["ending_rasa"]["label"],
                    "changed": navarasa["beginning_end_changed"]["value"],
                },
                [
                    row["event_id"]
                    for row in navarasa["turn_sequence"]
                    if not row["defaulted_primary"]
                ],
                ProvenanceLevel.INTERPRETED.value,
                [],
            ))
        else:
            limitations.append("detected_rasa_unavailable")
            if navarasa["defaulted_shanta_turns"]:
                limitations.append("defaulted_shanta_not_detected_evidence")

        state = engagement["engagement_state"]
        if state["state"] != "insufficient":
            items.append(_item(
                "engagement_state",
                "Bounded interaction-state label for this session.",
                {
                    "state": state["state"],
                    "basis": list(state["basis"]),
                },
                engagement["evidence"]["source_event_ids"],
                ProvenanceLevel.INTERPRETED.value,
                ["interaction_state_not_a_person_claim"],
            ))
        else:
            limitations.append("engagement_state_insufficient")

        latency = temporal["response_latency_trajectory"]
        if latency["status"] != "ok":
            limitations.append("response_latency_unavailable")

        return {
            "session_id": self._coordinator.session_id,
            "observation_kind": "evidence_bundle",
            "provenance_level": ProvenanceLevel.INTERPRETED.value,
            "status": "insufficient" if turn_count < 2 else "ok",
            "evidence_items": items,
            "sources": {
                "temporal": {
                    "observation_kind": temporal["observation_kind"],
                    "turn_count": turn_count,
                },
                "linguistic": {
                    "observation_kind": linguistic["observation_kind"],
                    "turn_count": len(linguistic["turn_sequence"]),
                },
                "navarasa": {
                    "observation_kind": navarasa["observation_kind"],
                    "detected_count": len(detected),
                    "defaulted_shanta_turns": navarasa["defaulted_shanta_turns"],
                },
                "engagement": {
                    "observation_kind": engagement["observation_kind"],
                    "state": state["state"],
                },
            },
            "limitations": limitations,
        }


def _item(
    signal_type: str,
    observation: str,
    value: Any,
    source_event_ids: list[str],
    provenance_level: str,
    limitations: list[str],
) -> dict[str, Any]:
    unique_ids: list[str] = []
    for event_id in source_event_ids:
        if event_id not in unique_ids:
            unique_ids.append(event_id)
    return {
        "evidence_id": f"ev_{signal_type}",
        "signal_type": signal_type,
        "observation": observation,
        "value": value,
        "source_event_ids": unique_ids,
        "provenance_level": provenance_level,
        "scope": "session",
        "limitations": list(limitations),
    }
