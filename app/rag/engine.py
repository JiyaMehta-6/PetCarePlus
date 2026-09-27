"""PetCare+ RAG engine.

Orchestrates the full local pipeline:

    query -> understand -> safety -> dense+BM25 -> RRF -> context -> local LLM
          -> citations -> answer

Designed to be driven from a background worker so the UI never blocks. All work
is local; no network calls occur during inference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.config import LOW_CONFIDENCE_THRESHOLD
from app.log_utils import get_logger
from app.rag.context import ContextBuilder
from app.rag.citations import build_source_cards, normalize_citation_markers
from app.rag.embeddings import EmbeddingModel
from app.rag.generation import Generation, GenerationError
from app.rag.knowledge import Chunk
from app.rag.query_understanding import QueryContext, understand
from app.rag.retrieval import Retriever
from app.rag.species_registry import SPECIES_BY_KEY, detect_species
from app.safety.safety import (
    SafetyResult,
    SafetyLevel,
    assess,
    rabies_guidance_note,
    EMERGENCY_INSTRUCTION,
)

logger = get_logger("petcare.engine")

LOW_CONFIDENCE_MESSAGE = (
    "I don't have enough reliable information in my current knowledge base to "
    "answer that confidently. A veterinarian or an authoritative source would be "
    "the best next step. If this is urgent, please contact a veterinarian directly."
)


@dataclass
class Answer:
    query: str
    answer_text: str = ""
    sources: list = field(default_factory=list)  # list[SourceCard]
    safety: SafetyResult | None = None
    confidence: float = 0.0
    low_confidence: bool = False
    retrieval_report: str = ""
    cited_chunks: list[Chunk] = field(default_factory=list)
    generation_error: str = ""

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "answer_text": self.answer_text,
            "sources": [s.to_dict() for s in self.sources],
            "safety": self.safety.as_dict() if self.safety else None,
            "confidence": self.confidence,
            "low_confidence": self.low_confidence,
            "retrieval_report": self.retrieval_report,
        }


class RAGEngine:
    def __init__(self):
        self.embedder: EmbeddingModel | None = None
        self.retriever: Retriever | None = None
        self.generation: Generation | None = None
        self.context_builder = ContextBuilder()
        self._initialized = False

    # ------------------------------------------------------------------
    def initialize(self, load_generation: bool = True) -> None:
        """Load heavy resources. Safe to call multiple times."""
        if self._initialized:
            return
        logger.info("Initializing PetCare+ RAG engine")
        self.embedder = EmbeddingModel()
        self.retriever = Retriever(embedder=self.embedder)
        # FAISS + embedder are loaded lazily on first query for a fast startup.
        if load_generation:
            self.generation = Generation()
            try:
                self.generation.load()
            except Exception as err:  # pragma: no cover - model may be missing
                logger.warning("Generation model not loaded at init: %s", err)
                self.generation = None
        self._initialized = True

    def ensure_generation(self) -> Generation:
        if self.generation is None:
            self.generation = Generation()
        if not self.generation._ready:
            self.generation.load()
        return self.generation

    # ------------------------------------------------------------------
    def _build_profile_context(self, base: QueryContext, pet_profile: dict | None) -> QueryContext:
        if not pet_profile:
            return base
        # Accept either an engine-shaped profile ("species" = class) or the
        # UI-shaped pet dict ("species_key" / "species_display").
        species = pet_profile.get("species") or pet_profile.get("type")
        if not species:
            key = pet_profile.get("species_key")
            disp = pet_profile.get("species_display") or ""
            sp = SPECIES_BY_KEY.get(key) if key else None
            if sp:
                species = sp.klass
            elif disp:
                detected = detect_species(disp)
                species = detected[0] if detected else None
        breed = pet_profile.get("breed")
        age = pet_profile.get("age_years")
        if species and species not in base.species:
            base.species.append(species)
        if breed and breed not in base.breeds:
            base.breeds.append(breed)
        if age is not None:
            try:
                age = float(age)
                if age >= 7:
                    stages = ["senior"]
                elif age >= 1:
                    stages = ["adult"]
                else:
                    # KB tags young animals as "puppy" or "kitten"; match both so
                    # the age-based boost fires regardless of the pet's species.
                    stages = ["puppy", "kitten"]
                for st in stages:
                    if st not in base.life_stage:
                        base.life_stage.append(st)
            except (TypeError, ValueError):
                pass
        return base

    def _describe_pet(self, pet_profile: dict, ctx: QueryContext) -> str:
        bits = []
        name = pet_profile.get("name")
        if name:
            bits.append(f"pet name: {name}")
        if ctx.species:
            bits.append("species: " + ", ".join(ctx.species))
        if ctx.breeds:
            bits.append("breed: " + ", ".join(ctx.breeds))
        if ctx.life_stage:
            bits.append("life stage: " + ", ".join(ctx.life_stage))
        return "; ".join(bits)

    # ------------------------------------------------------------------
    def answer(
        self,
        query: str,
        pet_profile: dict | None = None,
        history=None,
        on_token: Callable[[str], None] | None = None,
        on_stage: Callable[[str], None] | None = None,
    ) -> Answer:
        if on_stage:
            on_stage("Understanding your question...")
        ctx = self._build_profile_context(understand(query), pet_profile)

        safety = assess(query)
        rabies_note = rabies_guidance_note(query)

        # Refuse illegal / harmful-intent queries before any retrieval or generation.
        if safety.illegal:
            answer = Answer(
                query=query,
                safety=safety,
                confidence=1.0,
                retrieval_report="Query flagged as illegal or harmful — refused.",
                answer_text=safety.illegal_note,
            )
            logger.info("Refused illegal/harmful query: %s", query[:60])
            return answer

        if on_stage:
            on_stage("Finding relevant care guidance...")

        results, confidence = self.retriever.retrieve(ctx)
        n_found = len(results)
        report = f"{n_found} relevant source{'s' if n_found != 1 else ''} found"
        logger.info("Retrieval for '%s': %s | confidence=%.2f", query[:60], report, confidence)

        answer = Answer(
            query=query,
            safety=safety,
            confidence=confidence,
            retrieval_report=report,
        )

        if on_stage:
            on_stage("Preparing your answer...")

        low_conf = confidence < LOW_CONFIDENCE_THRESHOLD and not safety.is_emergency
        if low_conf:
            answer.low_confidence = True
            answer.answer_text = LOW_CONFIDENCE_MESSAGE
            # Still surface whatever was retrieved for transparency.
            ctx_result = self.context_builder.build(results)
            answer.cited_chunks = ctx_result.cited_chunks
            answer.sources = build_source_cards(answer.cited_chunks)
            return answer

        try:
            gen = self.ensure_generation()
        except GenerationError as err:
            answer.generation_error = str(err)
            answer.answer_text = (
                "PetCare+ couldn't load its local AI model. The knowledge retrieval "
                "worked, but answer generation requires the local model. Please run "
                "setup_windows.ps1 to download the model into the D: drive."
            )
            ctx_result = self.context_builder.build(results)
            answer.cited_chunks = ctx_result.cited_chunks
            answer.sources = build_source_cards(answer.cited_chunks)
            return answer

        ctx_result = self.context_builder.build(results)
        answer.cited_chunks = ctx_result.cited_chunks
        answer.sources = build_source_cards(answer.cited_chunks)

        safety_instruction = EMERGENCY_INSTRUCTION if safety.is_emergency else ""
        if rabies_note:
            safety_instruction = (safety_instruction + "\n\n" + rabies_note).strip()

        pet_context = self._describe_pet(pet_profile, ctx) if pet_profile else ""
        try:
            text = gen.generate(
                context=ctx_result.context_text,
                query=query,
                safety_instruction=safety_instruction,
                pet_context=pet_context,
                history=history,
                callback=on_token,
            )
        except Exception as err:  # pragma: no cover - generation edge cases
            logger.exception("Generation failed")
            answer.generation_error = str(err)
            text = (
                "I found relevant guidance but encountered a problem while generating "
                "the answer. The retrieved sources below may still help."
            )

        answer.answer_text = normalize_citation_markers(text.strip())
        return answer
