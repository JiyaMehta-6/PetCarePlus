"""Query understanding.

Lightweight, fully local extraction of structured signals from a user query so
retrieval can apply metadata-aware filtering without over-filtering. We never
discard species-level knowledge when breed-specific knowledge is absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.rag.species_registry import detect_species, detect_breed, detect_life_stage

# Topic keyword map. Order matters only for preference, not correctness.
TOPIC_KEYWORDS = {
    "nutrition": ["feed", "food", "diet", "nutrition", "eat", "eating", "meal", "kibble", "treat", "treats", "hungry", "weight", "obese", "obesity", "underweight"],
    "toxic": ["toxic", "poison", "poisoning", "chocolate", "grape", "onion", "garlic", "xylitol", "unsafe food", "harmful", "dangerous food"],
    "environment": ["habitat", "cage", "enclosure", "tank", "aquarium", "temperature", "humidity", "bedding", "housing", "light", "uvb", "substrate", "ventilation", "apartment"],
    "grooming": ["groom", "bath", "bathing", "brush", "brushing", "nail", "claw", "dental", "teeth", "ear", "coat", "shedding", "clean"],
    "behaviour": ["behav", "aggress", "anxi", "stress", "bark", "bite", "separation", "social", "scratch", "destruct", "fear", "distress", "litter", "noise"],
    "exercise": ["exercise", "walk", "play", "activity", "enrichment", "run", "training"],
    "preventive": ["vaccin", "vaccine", "vaccination", "parasite", "deworm", "steriliz", "neuter", "spay", "microchip", "checkup", "prevent"],
    "health": ["sick", "symptom", "disease", "illness", "condition", "infection", "wound", "pain", "limp", "vomit", "diarrhea", "cough", "sneez", "fever", "seizure", "swelling", "bleeding", "not eating", "lethargic"],
    "india": ["india", "indian", "monsoon", "heat", "summer", "rabies", "street", "desi"],
}


@dataclass
class QueryContext:
    raw: str
    species: list[str] = field(default_factory=list)
    breeds: list[str] = field(default_factory=list)
    life_stage: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    urgency_terms: list[str] = field(default_factory=list)

    def describe(self) -> str:
        parts = []
        if self.species:
            parts.append("species=" + ",".join(self.species))
        if self.breeds:
            parts.append("breed=" + ",".join(self.breeds))
        if self.life_stage:
            parts.append("stage=" + ",".join(self.life_stage))
        if self.topics:
            parts.append("topic=" + ",".join(self.topics))
        return "; ".join(parts) or "general"


def understand(query: str) -> QueryContext:
    species = detect_species(query)
    breeds = detect_breed(query)
    life_stage = detect_life_stage(query)

    q = query.lower()
    topics = [t for t, kws in TOPIC_KEYWORDS.items() if any(k in q for k in kws)]
    if not topics:
        topics = ["health", "nutrition"]

    return QueryContext(
        raw=query,
        species=species,
        breeds=breeds,
        life_stage=life_stage,
        topics=topics,
    )
