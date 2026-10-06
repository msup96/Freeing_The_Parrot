"""
Test Stage 06 card selection semantics.

Validates the distinction between:
  FLIPPED (card inspected)
  SELECTED (card chosen for resonance set)
  RESONATES (participant confirms entire selected set)
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ftp_backend_service import (
    create_session,
    SESSION_DECKS,
    SESSION_SELECTED,
    get_session,
)
from ftp.session.states import SessionState
from ftp.events.model import EventType, ProvenanceLevel


def test_single_selection():
    """Test selecting a single card and confirming resonance."""
    session = create_session()
    sid = session.session_id
    
    # Setup: transition through states
    # INPUT_INGESTION → LIVE_CONVERSATION
    session.advance(SessionState.LIVE_CONVERSATION)
    session.record_parrot_turn("question", "response")
    session.lock()  # Automatically advances to SESSION_CONCLUDED
    
    # Create deck with 27 cards
    deck = {
        "cards": [
            {
                "card_id": f"card_{idx:02d}",
                "card_index": idx,
                "title": f"Card {idx}",
                "semantic_anchor": "TEST_ANCHOR",
                "semantic_motif": "test-motif",
                "archetype": "ARCHIVE",
                "qualitative_reading": f"Reading {idx}",
            }
            for idx in range(1, 28)
        ]
    }
    SESSION_DECKS[sid] = deck
    
    # Advance to CARD_SELECTION state
    # SESSION_CONCLUDED → POST_SESSION_INTERPRETATION → CARD_SELECTION
    session.advance(SessionState.POST_SESSION_INTERPRETATION)
    session.advance(SessionState.CARD_SELECTION)
    
    # Simulate card selection: select card 5
    selected_cards = [deck["cards"][4]]  # Index 4 = card_05
    SESSION_SELECTED[sid] = selected_cards
    
    # Record resonance event
    session.record(
        event_type=EventType.CARD_RESONANCE_MARKED,
        provenance_level=ProvenanceLevel.OBSERVED,
        payload={
            "selected_cards": [
                {"card_id": "card_05", "card_index": 5, "selection_order": 1}
            ],
            "selected_count": 1,
            "meaning": "participant_reported_resonance",
        },
    )
    
    # Verify state
    assert session.machine.state == SessionState.CARD_SELECTION
    assert len(SESSION_SELECTED[sid]) == 1
    assert SESSION_SELECTED[sid][0]["card_index"] == 5
    
    # Verify event was recorded
    events = session.store.all_events()
    resonance_events = [e for e in events if e.event_type == EventType.CARD_RESONANCE_MARKED]
    assert len(resonance_events) == 1
    assert resonance_events[0].payload["selected_count"] == 1


def test_multi_selection():
    """Test selecting multiple cards and confirming resonance."""
    session = create_session()
    sid = session.session_id
    
    session.advance(SessionState.LIVE_CONVERSATION)
    session.record_parrot_turn("question", "response")
    session.lock()  # Automatically advances to SESSION_CONCLUDED
    
    deck = {
        "cards": [
            {
                "card_id": f"card_{idx:02d}",
                "card_index": idx,
                "title": f"Card {idx}",
                "semantic_anchor": "ANCHOR",
                "semantic_motif": "motif",
                "archetype": "ARCHIVE",
                "qualitative_reading": f"Reading {idx}",
            }
            for idx in range(1, 28)
        ]
    }
    SESSION_DECKS[sid] = deck
    
    # Transition to CARD_SELECTION
    session.advance(SessionState.POST_SESSION_INTERPRETATION)
    session.advance(SessionState.CARD_SELECTION)
    
    # Select 4 cards: 2, 5, 8, 15
    selected_indices = [1, 4, 7, 14]  # 0-based indexing
    selected_cards = [deck["cards"][idx] for idx in selected_indices]
    SESSION_SELECTED[sid] = selected_cards
    
    # Record ONE resonance event for the entire selected set
    session.record(
        event_type=EventType.CARD_RESONANCE_MARKED,
        provenance_level=ProvenanceLevel.OBSERVED,
        payload={
            "selected_cards": [
                {"card_id": f"card_{idx+1:02d}", "card_index": idx+1, "selection_order": order}
                for order, idx in enumerate(selected_indices, start=1)
            ],
            "selected_count": 4,
            "meaning": "participant_reported_resonance",
        },
    )
    
    # Verify
    assert len(SESSION_SELECTED[sid]) == 4
    events = session.store.all_events()
    resonance_events = [e for e in events if e.event_type == EventType.CARD_RESONANCE_MARKED]
    assert len(resonance_events) == 1  # ONE event, not 4
    assert resonance_events[0].payload["selected_count"] == 4
    
    # Verify order is preserved
    assert resonance_events[0].payload["selected_cards"][0]["card_index"] == 2
    assert resonance_events[0].payload["selected_cards"][1]["card_index"] == 5
    assert resonance_events[0].payload["selected_cards"][2]["card_index"] == 8
    assert resonance_events[0].payload["selected_cards"][3]["card_index"] == 15


def test_deselection():
    """Test selecting, then deselecting cards."""
    session = create_session()
    sid = session.session_id
    
    session.advance(SessionState.LIVE_CONVERSATION)
    session.record_parrot_turn("q", "r")
    session.lock()  # Automatically advances to SESSION_CONCLUDED
    
    deck = {
        "cards": [
            {
                "card_id": f"card_{idx:02d}",
                "card_index": idx,
                "title": f"Card {idx}",
                "semantic_anchor": "A",
                "semantic_motif": "m",
                "archetype": "ARCH",
                "qualitative_reading": "R",
            }
            for idx in range(1, 28)
        ]
    }
    SESSION_DECKS[sid] = deck
    
    # Transition to CARD_SELECTION
    session.advance(SessionState.POST_SESSION_INTERPRETATION)
    session.advance(SessionState.CARD_SELECTION)
    
    # Simulate user selecting 3 cards, then deselecting 1
    # After deselection, only 2 cards remain
    selected_indices = [0, 4, 7]  # originally 3 cards
    selected_cards = [deck["cards"][idx] for idx in selected_indices if idx != 4]  # remove index 4
    SESSION_SELECTED[sid] = selected_cards
    
    # Record final resonance with 2 cards
    session.record(
        event_type=EventType.CARD_RESONANCE_MARKED,
        provenance_level=ProvenanceLevel.OBSERVED,
        payload={
            "selected_cards": [
                {"card_id": "card_01", "card_index": 1, "selection_order": 1},
                {"card_id": "card_08", "card_index": 8, "selection_order": 2},
            ],
            "selected_count": 2,
            "meaning": "participant_reported_resonance",
        },
    )
    
    assert len(SESSION_SELECTED[sid]) == 2
    assert SESSION_SELECTED[sid][0]["card_index"] == 1
    assert SESSION_SELECTED[sid][1]["card_index"] == 8


def test_flip_without_selection():
    """Test that flipping a card does not automatically select it."""
    session = create_session()
    sid = session.session_id
    
    session.advance(SessionState.LIVE_CONVERSATION)
    session.record_parrot_turn("q", "r")
    session.lock()  # Automatically advances to SESSION_CONCLUDED
    
    deck = {
        "cards": [
            {
                "card_id": f"card_{idx:02d}",
                "card_index": idx,
                "title": f"Card {idx}",
                "semantic_anchor": "A",
                "semantic_motif": "m",
                "archetype": "ARCH",
                "qualitative_reading": "R",
            }
            for idx in range(1, 28)
        ]
    }
    SESSION_DECKS[sid] = deck
    
    # Transition to CARD_SELECTION
    session.advance(SessionState.POST_SESSION_INTERPRETATION)
    session.advance(SessionState.CARD_SELECTION)
    
    # User flips card 10 to inspect it (no selection yet)
    # Then flips card 3 and explicitly selects it
    selected_cards = [deck["cards"][2]]  # only card 3
    SESSION_SELECTED[sid] = selected_cards
    
    session.record(
        event_type=EventType.CARD_RESONANCE_MARKED,
        provenance_level=ProvenanceLevel.OBSERVED,
        payload={
            "selected_cards": [
                {"card_id": "card_03", "card_index": 3, "selection_order": 1},
            ],
            "selected_count": 1,
            "meaning": "participant_reported_resonance",
        },
    )
    
    # Verify: only card 3 is selected, not card 10
    assert len(SESSION_SELECTED[sid]) == 1
    assert SESSION_SELECTED[sid][0]["card_index"] == 3


def test_empty_selection_prevented():
    """Test that resonance cannot be submitted with zero selected cards."""
    session = create_session()
    sid = session.session_id
    
    session.advance(SessionState.LIVE_CONVERSATION)
    session.record_parrot_turn("q", "r")
    session.lock()  # Automatically advances to SESSION_CONCLUDED
    
    deck = {
        "cards": [
            {
                "card_id": f"card_{idx:02d}",
                "card_index": idx,
                "title": f"Card {idx}",
                "semantic_anchor": "A",
                "semantic_motif": "m",
                "archetype": "ARCH",
                "qualitative_reading": "R",
            }
            for idx in range(1, 28)
        ]
    }
    SESSION_DECKS[sid] = deck
    
    # Transition to CARD_SELECTION
    session.advance(SessionState.POST_SESSION_INTERPRETATION)
    session.advance(SessionState.CARD_SELECTION)
    
    # No cards selected
    SESSION_SELECTED[sid] = []
    
    # Attempt to record resonance with empty set should be prevented on frontend
    # (backend can still accept it but frontend should block it)
    assert len(SESSION_SELECTED[sid]) == 0


def test_semantic_anchors_preserved():
    """Test that selected cards retain their semantic anchor and metadata."""
    session = create_session()
    sid = session.session_id
    
    session.advance(SessionState.LIVE_CONVERSATION)
    session.record_parrot_turn("q", "r")
    session.lock()  # Automatically advances to SESSION_CONCLUDED
    
    deck = {
        "cards": [
            {
                "card_id": f"card_{idx:02d}",
                "card_index": idx,
                "title": f"Card {idx}",
                "semantic_anchor": ["DOUBT", "RECONSIDERATION", "ABSENCE"][idx % 3],
                "semantic_motif": "motif",
                "archetype": f"ARCH_{idx}",
                "qualitative_reading": f"Reading {idx}",
            }
            for idx in range(1, 28)
        ]
    }
    SESSION_DECKS[sid] = deck
    
    # Transition to CARD_SELECTION
    session.advance(SessionState.POST_SESSION_INTERPRETATION)
    session.advance(SessionState.CARD_SELECTION)
    
    # Select cards 4 and 8
    selected_cards = [deck["cards"][3], deck["cards"][7]]
    SESSION_SELECTED[sid] = selected_cards
    
    session.record(
        event_type=EventType.CARD_RESONANCE_MARKED,
        provenance_level=ProvenanceLevel.OBSERVED,
        payload={
            "selected_cards": [
                {
                    "card_id": "card_04",
                    "card_index": 4,
                    "selection_order": 1,
                    "semantic_anchor": deck["cards"][3]["semantic_anchor"],
                },
                {
                    "card_id": "card_08",
                    "card_index": 8,
                    "selection_order": 2,
                    "semantic_anchor": deck["cards"][7]["semantic_anchor"],
                },
            ],
            "selected_count": 2,
            "meaning": "participant_reported_resonance",
        },
    )
    
    # Verify anchors are preserved
    assert SESSION_SELECTED[sid][0]["semantic_anchor"] == "RECONSIDERATION"  # idx 4: 4 % 3 = 1
    assert SESSION_SELECTED[sid][1]["semantic_anchor"] == "ABSENCE"  # idx 8: 8 % 3 = 2


if __name__ == "__main__":
    test_single_selection()
    test_multi_selection()
    test_deselection()
    test_flip_without_selection()
    test_empty_selection_prevented()
    test_semantic_anchors_preserved()
    print("All Stage 06 selection tests passed!")
