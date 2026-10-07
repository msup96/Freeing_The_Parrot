from ftp.privacy.disclosures import assess_disclosure, participant_safe_text


def test_explicit_disclosure_is_detected_without_identity_labeling():
    assessment = assess_disclosure("I identify as non-binary, and I want to keep exploring.")
    assert assessment.disclosed is True
    assert "non-binary" not in assessment.marker


def test_non_sensitive_text_is_preserved():
    assert participant_safe_text("I feel uncertain today.") == ("I feel uncertain today.", False)


def test_sensitive_text_is_minimized_for_participant_surfaces():
    safe, disclosed = participant_safe_text("I'm bisexual and this is personal.")
    assert disclosed is True
    assert safe == "sensitive personal disclosure omitted"
    assert "bisexual" not in safe
