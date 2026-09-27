"""AI safety layer for PetCare+.

Flags potentially urgent situations (poisoning, breathing difficulty, collapse,
seizures, suspected rabies exposure, etc.) and produces a clear, calm safety
assessment. For urgent signals the UI shows an amber/red banner and the
generator is instructed to prioritise veterinary care. The assistant never
provides dangerous home treatment for emergencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

# Tier 1: strong emergency signals -> red/urgent banner.
URGENT_PATTERNS = {
    "breathing difficulty": r"difficult(?:y| to) breath|can'?t breathe|not breathing|stop(?:s|ped)? breathing|gasping|choking",
    "collapse": r"collaps|fainted|unconscious|passed out|not responsive|unresponsive",
    "seizure": r"seizur|convuls|fitting",
    "severe bleeding": r"severe bleed|heavy bleed|bleeding badly|bleeding heavily|won'?t stop bleeding",
    "severe trauma": r"hit by|ran over|fell from|severe injury|major trauma|broken bone",
    "heatstroke": r"heatstroke|heat stroke|overheat|body very hot|panting heavily and hot",
    "poisoning": r"ate (?:rat|mouse) poison|ingest.*poison|antifreeze|snail bait|severe poison",
    "known toxin ingestion": r"ate (?:a |an )?(?:grape|raisin|chocolate|onion|garlic|xylitol|macadamia)|ingested .*(?:grape|raisin|chocolate|onion|xylitol|macadamia)",
    "inability to urinate": r"can'?t urinate|unable to pee|straining to urinate|blocked bladder",
    "severe abdominal swelling": r"belly (?:suddenly )?swollen|abdomen swollen|bloated and",
    "severe allergic reaction": r"face swell|throat swell|anaphylax|hives and swell",
    "rabies exposure": r"rabid|foaming at the mouth|bitten by (?:a |unknown )(?:dog|animal|bat)|possible rabies",
}

# Tier 2: caution signals -> amber banner, still vet-appropriate.
CAUTION_PATTERNS = {
    "toxic ingestion": r"ate (?:a |an )?(?:grape|raisin|chocolate|onion|garlic|xylitol|macadamia)|ingested .*(?:grape|chocolate|onion|xylitol|macadamia)",
    "not eating": r"not eating|refus(?:e|ing) food|won'?t eat|stopped eating",
    "vomiting/diarrhea": r"vomit|throw(?:ing)? up|diarrh|bloody stool|blood in stool",
    "lethargy/weakness": r"lethargic|very weak|extremely tired|no energy|collapse",
    "wound": r"deep wound|bleeding|bite wound|cut",
    "rabies risk": r"dog bite|animal bite|scratch from|bitten|bat in",
    "distress": r"severe pain|crying in pain|whimpering|unusual aggression",
}

# Illegal / harmful-intent signals -> the assistant must refuse and alert.
# Deliberately specific to acts of cruelty, animal fighting and illegal wildlife
# acquisition; it does NOT flag legitimate "is it illegal to..." questions.
ILLEGAL_PATTERNS = {
    "animal cruelty": r"(?:how|ways?)\s+(?:to|do i|can i)\s+(?:hurt|harm|abuse|torture|kill|injure|punish|beat|starve)\b.*(?:pet|dog|cat|animal|puppy|kitten)|(?:hurt|harm|abuse|torture|beat|starve|kill)\s+(?:my|the|their|your)\s+(?:pet|dog|cat|puppy|kitten|animal|bird)",
    "animal fighting": r"dog\s?fight|cock\s?fight|make\s+(?:my|their|the|these|those|our)?\s*(?:dogs?|cats?|animals?|pets?)\s+(?:fight|fight each other|attack each other|bait)",
    "illegal wildlife": r"(?:buy|get|obtain|purchase|acquire|own)\s+(?:a |an |some )?(?:tiger|lion|leopard|pangolin|exotic|protected|wild)\s*(?:animal|pet|species|bird)?|wildlife traffick|smuggle\s+(?:a |an )?(?:tiger|wild|exotic|animal)",
    "poisoning animal": r"(?:how|ways?)\s+(?:to|do i)\s+poison|poison\s+(?:my|the|their)\s+(?:dog|cat|pet|animal)|put\s+(?:rat poison|poison|something)\s+in",
}


class SafetyLevel(str, Enum):
    NONE = "none"
    CAUTION = "caution"
    URGENT = "urgent"


@dataclass
class SafetyResult:
    level: SafetyLevel
    reasons: list[str] = field(default_factory=list)
    banner_title: str = ""
    banner_detail: str = ""
    is_emergency: bool = False
    illegal: bool = False
    illegal_note: str = ""

    def as_dict(self) -> dict:
        return {
            "level": self.level.value,
            "reasons": self.reasons,
            "banner_title": self.banner_title,
            "banner_detail": self.banner_detail,
            "is_emergency": self.is_emergency,
            "illegal": self.illegal,
            "illegal_note": self.illegal_note,
        }


ILLEGAL_REFUSAL = (
    "PetCare+ cannot provide guidance on causing harm to animals, organised animal "
    "fighting, or acquiring protected or illegal wildlife. These acts may violate the "
    "Prevention of Cruelty to Animals Act (1960) and the Wildlife Protection Act (1972) "
    "in India, and similar animal-protection laws elsewhere. If you are worried about an "
    "animal's welfare, please contact a veterinarian or a local animal-welfare "
    "organisation such as the Blue Cross of India. If you or someone else is in danger, "
    "reach out to the appropriate authorities."
)


def assess(query: str) -> SafetyResult:
    q = query.lower()

    illegal_hits = [name for name, pat in ILLEGAL_PATTERNS.items() if re.search(pat, q)]
    if illegal_hits:
        return SafetyResult(
            level=SafetyLevel.URGENT,
            reasons=illegal_hits,
            banner_title="Not allowed",
            banner_detail=ILLEGAL_REFUSAL,
            is_emergency=False,
            illegal=True,
            illegal_note=ILLEGAL_REFUSAL,
        )

    urgent_hits = [name for name, pat in URGENT_PATTERNS.items() if re.search(pat, q)]
    caution_hits = [name for name, pat in CAUTION_PATTERNS.items() if re.search(pat, q)]

    if urgent_hits:
        return SafetyResult(
            level=SafetyLevel.URGENT,
            reasons=urgent_hits,
            banner_title="URGENT",
            banner_detail=(
                "Some signs described here can require immediate veterinary attention. "
                "Contact a veterinarian or an emergency veterinary service as soon as possible."
            ),
            is_emergency=True,
        )
    if caution_hits:
        return SafetyResult(
            level=SafetyLevel.CAUTION,
            reasons=caution_hits,
            banner_title="Veterinary attention may be needed",
            banner_detail=(
                "Based on what you described, it is wise to contact a veterinarian for "
                "advice. The guidance below is informational and not a diagnosis."
            ),
            is_emergency=False,
        )
    return SafetyResult(level=SafetyLevel.NONE)


def rabies_guidance_note(query: str) -> str | None:
    """Return authoritative first-aid framing for possible rabies exposure."""
    q = query.lower()
    if re.search(r"rab(?:ies|y)|bitten by|dog bite|animal bite|bat", q) and re.search(r"bite|bitten|scratch|exposure|saliva", q):
        return (
            "If there has been a potential rabies exposure (bite, scratch or saliva contact "
            "with broken skin or mucous membranes from a mammal, especially an unknown or "
            "stray animal), this is a public-health matter. Wash the wound thoroughly with "
            "soap and running water for at least 15 minutes, apply an antiseptic, and seek "
            "prompt medical/veterinary assessment. Do not assume the animal is safe based on "
            "appearance or behaviour; professional evaluation is required."
        )
    return None


# Guidance inserted into the generation prompt when urgency is detected.
EMERGENCY_INSTRUCTION = (
    "The user's question may describe an urgent situation. Prioritise clear advice to "
    "contact a veterinarian or emergency veterinary service. Do NOT suggest risky home "
    "treatment for emergencies. State when immediate professional care is needed."
)
