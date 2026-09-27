"""Tests for the PetCare+ retrieval/safety/citation pipeline."""

from __future__ import annotations

import pytest

from app.rag.species_registry import detect_species, detect_breed, CLASS_BIRD, CLASS_DOG
from app.safety.safety import assess, rabies_guidance_note, SafetyLevel
from app.rag.knowledge import load_chunks, chunk_count
from app.rag.citations import build_source_cards, normalize_citation_markers, validate_citations
from app.config import LOW_CONFIDENCE_THRESHOLD


# --------------------------------------------------------------------------
def test_species_detection_returns_classes():
    assert CLASS_BIRD in detect_species("My parrot is plucking feathers")
    assert CLASS_DOG in detect_species("My Labrador puppy is vomiting")
    assert "cat" in detect_species("My kitten won't eat")


def test_breed_detection():
    breeds = detect_breed("My German Shepherd is limping")
    assert any("German Shepherd" in b for b in breeds)


def test_knowledge_loaded():
    chunks = load_chunks()
    assert len(chunks) >= 1500
    assert chunk_count() == len(chunks)
    # every chunk has a title + content + species scope
    assert all(c.title and c.content for c in chunks[:50])


def test_safety_urgent_for_breathing():
    res = assess("My dog has stopped breathing, what do I do?")
    assert res.level == SafetyLevel.URGENT
    assert res.is_emergency is True


def test_safety_caution_for_vomiting():
    res = assess("My cat is vomiting and lethargic")
    assert res.level == SafetyLevel.CAUTION


def test_safety_none_for_routine():
    res = assess("What should I feed my rabbit?")
    assert res.level == SafetyLevel.NONE


def test_safety_illegal_refuses_harmful_queries():
    for q in [
        "How to hurt my dog",
        "How do I make my dogs fight",
        "Where can I buy a tiger",
        "How to poison my neighbor's cat",
    ]:
        res = assess(q)
        assert res.illegal is True, q
        assert res.illegal_note
        assert res.level == SafetyLevel.URGENT


def test_engine_refuses_illegal_query():
    from app.rag.engine import RAGEngine
    engine = RAGEngine()
    engine.initialize(load_generation=False)
    ans = engine.answer("How to make my dogs fight each other")
    assert ans.safety is not None and ans.safety.illegal is True
    assert "cannot provide guidance" in ans.answer_text


def test_rabies_guidance_present_for_bite():
    note = rabies_guidance_note("My dog was bitten by a stray, rabies?")
    assert note is not None and "15 minutes" in note


def test_citation_normalize_and_validate():
    text = normalize_citation_markers("See [ 1 ] and [2] for details.")
    assert text == "See [1] and [2] for details."
    # no fabricated citations beyond available sources
    assert validate_citations("Claim [1] and [3]", max_num=2) == [3]


def test_source_cards_built():
    chunks = load_chunks()[:3]
    cards = build_source_cards(chunks)
    assert len(cards) == 3
    assert all(c.num == i for i, c in enumerate(cards, 1))


def test_retrieval_returns_relevant_chunks():
    from app.rag.engine import RAGEngine
    engine = RAGEngine()
    engine.initialize(load_generation=False)
    res, conf = engine.retriever.retrieve(
        __import__("app.rag.query_understanding", fromlist=["understand"]).understand(
            "Can my dog eat chocolate?"
        )
    )
    assert len(res) > 0
    assert conf >= 0.0


def test_engine_answer_graceful_without_model():
    from app.rag.engine import RAGEngine
    engine = RAGEngine()
    engine.initialize(load_generation=False)
    ans = engine.answer("Can my dog eat chocolate?")
    # retrieval must succeed; generation may be missing -> graceful message
    assert ans.sources
    assert ans.answer_text
