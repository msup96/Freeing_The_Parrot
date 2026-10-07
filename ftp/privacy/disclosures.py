"""Purpose limitation for voluntary sensitive disclosures."""
from __future__ import annotations

import re
from dataclasses import dataclass

_DISCLOSURE_PATTERNS = (
    re.compile(r"\b(i am|i'm|i identify as|my gender is|my sexuality is)\s+(?:a\s+)?[a-z][\w -]{1,40}", re.I),
    re.compile(r"\b(i am|i'm)\s+(?:gay|lesbian|bisexual|bi|pansexual|asexual|trans|non[- ]?binary|queer|straight)\b", re.I),
)

@dataclass(frozen=True)
class DisclosureAssessment:
    disclosed: bool
    marker: str = "sensitive personal disclosure omitted"


def assess_disclosure(text: str) -> DisclosureAssessment:
    return DisclosureAssessment(any(pattern.search(text or "") for pattern in _DISCLOSURE_PATTERNS))


def participant_safe_text(text: str) -> tuple[str, bool]:
    assessment = assess_disclosure(text)
    return (assessment.marker if assessment.disclosed else text, assessment.disclosed)
