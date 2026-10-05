from ftp.events.model import EventType, ProvenanceLevel
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState
from ftp.silent_reader.post_session import PostSessionInterpreter


class TestPostSessionInterpreter:
    def test_generates_exactly_27_unique_cards(self):
        coordinator = SessionCoordinator()
        coordinator.start()
        coordinator.advance(SessionState.LIVE_CONVERSATION)
        coordinator.record_parrot_turn("I feel uncertain and want clarity.", "You are not alone.")
        coordinator.record_parrot_turn("I keep returning to the same question.", "That pattern matters.")
        coordinator.lock()
        coordinator.advance(SessionState.POST_SESSION_INTERPRETATION)

        deck = PostSessionInterpreter(coordinator).generate_deck()

        assert deck["session_id"] == coordinator.session_id
        assert deck["total_cards"] == 27
        assert len(deck["cards"]) == 27
        assert {card["card_index"] for card in deck["cards"]} == set(range(1, 28))
        assert len({card["card_id"] for card in deck["cards"]}) == 27
        assert len({card["qualitative_reading"] for card in deck["cards"]}) == 27

    def test_cards_do_not_leak_analytical_spoilers(self):
        coordinator = SessionCoordinator()
        coordinator.start()
        coordinator.advance(SessionState.LIVE_CONVERSATION)
        coordinator.record_parrot_turn("I hesitate before speaking.", "Take your time.")
        coordinator.lock()
        coordinator.advance(SessionState.POST_SESSION_INTERPRETATION)

        deck = PostSessionInterpreter(coordinator).generate_deck()
        forbidden = ["you said", "system matched", "Navarasa", "OCR detected", "sentiment score"]
        for card in deck["cards"]:
            text = (card["qualitative_reading"] + " " + card["title"]).lower()
            for token in forbidden:
                assert token not in text

    def test_records_cards_generated_event(self):
        coordinator = SessionCoordinator()
        coordinator.start()
        coordinator.advance(SessionState.LIVE_CONVERSATION)
        coordinator.record_parrot_turn("The silence feels heavy.", "It can.")
        coordinator.lock()
        coordinator.advance(SessionState.POST_SESSION_INTERPRETATION)

        interpreter = PostSessionInterpreter(coordinator)
        interpreter.record_cards()

        events = coordinator.store.events_of_type(EventType.CARDS_GENERATED)
        assert len(events) == 1
        assert events[0].provenance_level == ProvenanceLevel.INFERRED
        assert events[0].payload["card_count"] == 27
