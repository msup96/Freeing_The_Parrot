"""Deterministic 27-card composer."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from ftp.events.model import ProvenanceLevel
from ftp.silent_reader.inference import evaluate_bundle
from ftp.silent_reader.reading.cards import (
    ARCHETYPES,
    BARNUM_TECHNIQUES,
    CARD_COUNT,
    COMPOSITION_STRATEGIES,
    READING_FRAGMENTS,
    TITLE_FRAGMENTS,
)
from ftp.silent_reader.reading.profile import build_reading_profile
from ftp.silent_reader.reading.validate import validate_deck


class DeterministicFallbackAdapter:
    """Force Phase 4B fallback without calling Gemini."""

    def complete(self, reader_input: dict[str, Any]) -> str:
        from ftp.silent_reader.deep_reader.adapter import GeminiUnavailable

        raise GeminiUnavailable("deterministic card composition path")


def compose_reading_deck(coordinator: Any, adapter: Any | None = None) -> dict[str, Any]:
    """Run lock-only reading pipeline and return a validated deck."""
    if not coordinator.machine.is_locked():
        raise ValueError("Reading deck composition requires a locked session.")

    from ftp.silent_reader.deep_reader.adapter import GeminiReaderAdapter
    from ftp.silent_reader.deep_reader.read import read_session_interpretations

    bundle = coordinator.build_evidence_bundle()
    evaluation = evaluate_bundle(bundle)
    if adapter is None:
        adapter = DeterministicFallbackAdapter()
    reader_result = read_session_interpretations(bundle, evaluation, adapter)
    profile = build_reading_profile(
        bundle=bundle,
        evaluation=evaluation,
        reader_result=reader_result,
    )
    deck = compose_deck(profile)
    validate_deck(deck, profile)
    deck["reading_profile_status"] = profile["reader_status"]
    deck["source"] = "phase_4c_reading_composer"
    return deck


def compose_deck(profile: dict[str, Any]) -> dict[str, Any]:
    anchors = profile["anchors"]
    cards: list[dict[str, Any]] = []
    used_readings: set[str] = set()
    # Stable session material changes the deterministic composition without adding
    # randomness. The profile remains the source of meaning; this only prevents
    # every session from receiving the same title/archetype ordering.
    session_seed = _session_seed(profile)

    for index in range(1, CARD_COUNT + 1):
        anchor = anchors[(index * 5 + index // 3 + session_seed) % len(anchors)]
        strategy = COMPOSITION_STRATEGIES[(index - 1 + session_seed) % len(COMPOSITION_STRATEGIES)]
        technique = BARNUM_TECHNIQUES[(index - 1 + session_seed) % len(BARNUM_TECHNIQUES)]
        title = _unique_title(index, used_readings, session_seed)
        archetype = ARCHETYPES[(index - 1 + session_seed) % len(ARCHETYPES)]
        fragment = READING_FRAGMENTS[(index * 3 + len(anchor["reading_seed"]) + session_seed) % len(READING_FRAGMENTS)]
        qualitative = _compose_reading(
            title=title,
            archetype=archetype,
            seed=anchor["reading_seed"],
            fragment=fragment,
            strategy=strategy,
        )
        qualitative = _ensure_unique_reading(qualitative, index, used_readings)
        evidence_ids = _resolve_evidence_ids(anchor, profile)
        cards.append({
            "card_id": f"card_{index:02d}_{_slugify(title)}",
            "card_index": index,
            "title": title,
            "archetype": archetype,
            "qualitative_reading": qualitative,
            "provenance_level": ProvenanceLevel.INFERRED.value,
            "hidden_provenance": {
                "inference_ids": [anchor["inference_id"]],
                "evidence_ids": evidence_ids,
                "barnum_technique": technique,
                "composition_strategy": strategy,
                "provenance_level": ProvenanceLevel.INFERRED.value,
            },
        })

    return {
        "session_id": profile["session_id"],
        "total_cards": CARD_COUNT,
        "cards": cards,
    }


def _compose_reading(
    *,
    title: str,
    archetype: str,
    seed: str,
    fragment: str,
    strategy: str,
) -> str:
    seed_clause = seed.rstrip(".")
    if strategy == "REFRACTION":
        body = f"As {archetype}, you may notice how {seed_clause.lower()}."
    elif strategy == "MIRRORING":
        body = f"{fragment} It mirrors the sense that {seed_clause.lower()}."
    elif strategy == "ACCUMULATION":
        body = f"{fragment} Something similar to {seed_clause.lower()} keeps returning."
    elif strategy == "THRESHOLD":
        body = f"At a threshold moment, {seed_clause.lower()}."
    elif strategy == "RETURNING motif":
        body = f"{fragment} The motif of returning touches {seed_clause.lower()}."
    elif strategy == "CONTRAST":
        body = f"{fragment} Yet another layer suggests {seed_clause.lower()}."
    else:
        body = f"Perhaps {seed_clause.lower()}, though the reading stays open."
    return f"{title}: {body}"


def _resolve_evidence_ids(anchor: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    refs = list(anchor.get("evidence_refs") or [])
    if refs:
        return refs
    catalog = profile.get("evidence_catalog") or {}
    if catalog:
        first = sorted(catalog.keys())[0]
        return [first]
    return ["reading_anchor_session_threshold"]


def _session_seed(profile: dict[str, Any]) -> int:
    """Derive composition variation only from analytical material.

    Session identity is deliberately excluded: identical evidence/inference
    material must produce the same deck even when replayed under another ID.
    """
    analytical_material = []
    for anchor in profile.get("anchors", []):
        analytical_material.append({
            "category": anchor.get("category"),
            "evidence_refs": sorted(str(ref) for ref in (anchor.get("evidence_refs") or [])),
            "inference_id": anchor.get("inference_id"),
            "reading_seed": anchor.get("reading_seed"),
        })
    material = repr({
        "anchors": analytical_material,
        "evidence_catalog": profile.get("evidence_catalog") or {},
        "limitations": profile.get("limitations") or [],
        "reader_status": profile.get("reader_status"),
        "evaluation_status": profile.get("evaluation_status"),
    })
    return int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:8], 16)


def _unique_title(index: int, used: set[str], session_seed: int) -> str:
    title = TITLE_FRAGMENTS[(index - 1 + session_seed) % len(TITLE_FRAGMENTS)]
    if title not in used:
        used.add(title)
        return title
    suffix = hashlib.sha256(str(index).encode()).hexdigest()[:4]
    variant = f"{title} ({suffix})"
    used.add(variant)
    return variant


def _ensure_unique_reading(text: str, index: int, used: set[str]) -> str:
    candidate = text
    bump = 0
    while candidate in used:
        bump += 1
        candidate = f"{text} ({bump})"
    used.add(candidate)
    return candidate


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
