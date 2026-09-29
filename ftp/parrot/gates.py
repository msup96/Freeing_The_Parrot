"""FTP 2.0 Parrot Gate Detection.

Phase 1B:
Extracted gate detection from interface_server.py without
changing the existing detection vocabulary or gate precedence.
"""

import re


def pattern_score(text, patterns):
    text = text.lower()
    return [p for p in patterns if re.search(p, text)]


def detect_gate_state(
    text,
    analysis,
    validation_patterns,
    health_patterns,
    fast_relief_patterns,
    anxiety_patterns,
    expletive_patterns,
    detect_social_intent_fn,
):
    health = pattern_score(text, health_patterns)
    validation = pattern_score(text, validation_patterns)
    relief = pattern_score(text, fast_relief_patterns)
    anxiety = pattern_score(text, anxiety_patterns)
    expletives = pattern_score(text, expletive_patterns)
    social_intent = detect_social_intent_fn(text)

    sentiment = analysis.get("sentiment", {})
    compound = float(sentiment.get("compound", 0.0))

    rasa_scores = analysis.get("rasa_scores", {})
    anxiety_rasa = "Bhayanaka" in rasa_scores

    if health:
        gate = "health_abort"
    elif social_intent:
        gate = "social_intercept"
    elif validation:
        gate = "validation_intercept"
    elif relief:
        gate = "fast_relief_intercept"
    else:
        gate = "reflection"

    return {
        "gate": gate,
        "social_intent": social_intent,
        "validation_detected": bool(validation),
        "fast_relief_detected": bool(relief),
        "anxiety_detected": bool(anxiety) or anxiety_rasa,
        "expletive_detected": bool(expletives),
        "validation_matches": len(validation),
        "fast_relief_matches": len(relief),
        "anxiety_matches": len(anxiety),
        "expletive_matches": len(expletives),
        "sentiment_compound": compound,
        "health_detected": bool(health),
        "health_matches": len(health),
    }
