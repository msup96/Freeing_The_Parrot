"""Deck and resonance validation for Phase 4C."""

from __future__ import annotations

import re
from typing import Any

from ftp.silent_reader.reading.cards import CARD_COUNT, FORBIDDEN_SPOILERS


class DeckValidationError(ValueError):
    """Raised when a composed deck fails integrity checks."""


class CardResonanceError(ValueError):
    """Raised when resonance marking references an unknown card."""


def validate_deck(deck: dict[str, Any], profile: dict[str, Any]) -> None:
    cards = deck.get("cards") or []
    if len(cards) != CARD_COUNT:
        raise DeckValidationError("deck must contain exactly 27 cards")

    card_ids = [card["card_id"] for card in cards]
    if len(set(card_ids)) != CARD_COUNT:
        raise DeckValidationError("card_id values must be unique")

    indices = {card["card_index"] for card in cards}
    if indices != set(range(1, CARD_COUNT + 1)):
        raise DeckValidationError("card_index must cover 1..27 exactly")

    readings = [card["qualitative_reading"] for card in cards]
    if len(set(readings)) != CARD_COUNT:
        raise DeckValidationError("qualitative_reading values must be unique")

    catalog = profile.get("evidence_catalog") or {}
    anchor_inference_ids = {anchor["inference_id"] for anchor in profile.get("anchors", [])}

    for card in cards:
        _validate_card(card, catalog, anchor_inference_ids)


def _validate_card(
    card: dict[str, Any],
    evidence_catalog: dict[str, Any],
    anchor_inference_ids: set[str],
) -> None:
    required = {"card_id", "card_index", "title", "archetype", "qualitative_reading", "provenance_level", "hidden_provenance"}
    if not required.issubset(card.keys()):
        raise DeckValidationError("card is missing required fields")

    hidden = card["hidden_provenance"]
    inference_ids = hidden.get("inference_ids") or []
    evidence_ids = hidden.get("evidence_ids") or []
    if not inference_ids:
        raise DeckValidationError("each card must trace to at least one inference")
    if not evidence_ids:
        raise DeckValidationError("each card must trace to at least one evidence item")
    if not hidden.get("barnum_technique"):
        raise DeckValidationError("barnum_technique is required")
    if not hidden.get("composition_strategy"):
        raise DeckValidationError("composition_strategy is required")

    for inference_id in inference_ids:
        if inference_id not in anchor_inference_ids and not inference_id.startswith("reading_anchor_"):
            raise DeckValidationError(f"unknown inference reference {inference_id!r}")

    for evidence_id in evidence_ids:
        if evidence_id.startswith("reading_anchor_"):
            continue
        if evidence_id not in evidence_catalog:
            raise DeckValidationError(f"unknown evidence reference {evidence_id!r}")

    participant_text = f"{card['title']} {card['qualitative_reading']}".lower()
    if contains_spoiler(participant_text):
        raise DeckValidationError("participant-facing card text contains analytical spoilers")

    if re.search(r"\b(?:ev|inf)_[a-z0-9_]+\b", participant_text):
        raise DeckValidationError("participant-facing card text exposes internal identifiers")


def contains_spoiler(text: str) -> bool:
    hay = text.lower()
    for token in FORBIDDEN_SPOILERS:
        if token in {"shanta", "raudra", "hasya", "karuna", "bibhatsa", "adbhuta", "bhayanaka", "veera"}:
            if re.search(rf"\b{re.escape(token)}\b", hay):
                return True
        elif token in hay:
            return True
    return False


def validate_card_resonance(
    deck: dict[str, Any],
    *,
    card_id: str,
    card_index: int,
) -> dict[str, Any]:
    """Validate a participant RESONATES selection against a generated deck."""
    cards = deck.get("cards") or []
    by_id = {card["card_id"]: card for card in cards}
    by_index = {card["card_index"]: card for card in cards}

    if card_id not in by_id:
        raise CardResonanceError(f"Unknown card_id {card_id!r}.")
    if card_index not in by_index:
        raise CardResonanceError(f"Unknown card_index {card_index!r}.")
    if by_id[card_id]["card_index"] != card_index:
        raise CardResonanceError("card_id and card_index do not refer to the same card.")
    if by_index[card_index]["card_id"] != card_id:
        raise CardResonanceError("duplicate card identity mismatch.")

    card = by_id[card_id]
    return {
        "card_id": card_id,
        "card_index": card_index,
        "title": card["title"],
        "meaning": "participant_reported_resonance_not_truth",
    }
