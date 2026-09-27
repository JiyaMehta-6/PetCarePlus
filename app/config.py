"""Central configuration and path management for PetCare+.

All large runtime assets (models, embeddings, FAISS indexes, Hugging Face
caches, Torch caches, knowledge base, user data and temporary AI files) are
derived from a single canonical root directory on the D: drive.

This module is intentionally dependency-light so that it can be imported very
early (before any heavy ML libraries) to configure cache environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical root
# ---------------------------------------------------------------------------
# The default storage root MUST remain on the D: drive. End users should never
# be surprised by multi-gigabyte AI assets silently appearing on C:.
PETCARE_ROOT = Path(os.environ.get("PETCARE_ROOT", r"D:\projects\petCareplus")).resolve()

# Allow an explicit override directory to be created if needed by the developer
# (e.g. for testing), but the default is always the path above.
ALLOW_ROOT_OVERRIDE = True

# ---------------------------------------------------------------------------
# Derived directories
# ---------------------------------------------------------------------------
APP_DIR = PETCARE_ROOT / "app"
MODELS_DIR = PETCARE_ROOT / "models"
EMBEDDINGS_DIR = MODELS_DIR / "embeddings" / "bge-small-en-v1.5"
LLM_DIR = MODELS_DIR / "llm" / "qwen"

HF_DIR = PETCARE_ROOT / "huggingface"
HF_HUB_CACHE = HF_DIR / "hub"
TRANSFORMERS_CACHE = HF_DIR / "transformers"

TORCH_DIR = PETCARE_ROOT / "torch"
CACHE_DIR = PETCARE_ROOT / "cache"
TEMP_DIR = PETCARE_ROOT / "temp"

KNOWLEDGE_DIR = PETCARE_ROOT / "knowledge"
KNOWLEDGE_JSONL = KNOWLEDGE_DIR / "knowledge.jsonl"
FAISS_INDEX = KNOWLEDGE_DIR / "index.faiss"

DATA_DIR = PETCARE_ROOT / "data"
PETS_DIR = DATA_DIR / "pets"
CONVERSATIONS_DIR = DATA_DIR / "conversations"

LOG_DIR = PETCARE_ROOT / "logs"
LOG_FILE = LOG_DIR / "petcare.log"

ASSETS_DIR = PETCARE_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
ILLUSTRATIONS_DIR = ASSETS_DIR / "illustrations"

DEVELOPER_DIR = PETCARE_ROOT / "developer"
SOURCE_DIR = DEVELOPER_DIR / "source"

EVALUATION_DIR = PETCARE_ROOT / "evaluation"

# ---------------------------------------------------------------------------
# Model identifiers
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_ID = "BAAI/bge-small-en-v1.5"
EMBEDDING_MODEL_LOCAL = str(EMBEDDINGS_DIR)

# Primary local generation model and low-resource fallback.
LLM_MODEL_PRIMARY = "Qwen/Qwen2.5-3B-Instruct"
LLM_MODEL_FALLBACK = "Qwen/Qwen2.5-1.5B-Instruct"
LLM_MODEL_LOCAL = str(LLM_DIR)

# When set, prefer models already present under LLM_DIR / EMBEDDINGS_DIR.
PREFER_LOCAL_MODELS = True

# ---------------------------------------------------------------------------
# RAG tuning
# ---------------------------------------------------------------------------
EMBEDDING_DIM = 384
EMBEDDING_DTYPE = "float32"
FAISS_INDEX_TYPE = "IndexFlatIP"  # inner product over normalized vectors == cosine

DENSE_TOP_K = 10
BM25_TOP_K = 10
RRF_K = 60
FINAL_TOP_K = 8            # how many fused chunks to keep after RRF
MIN_CONTEXT_CHUNKS = 5

MAX_CONTEXT_TOKENS = 3500
LOW_CONFIDENCE_THRESHOLD = 0.32  # retrieval confidence below this -> low confidence

# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
GENERATION_MAX_NEW_TOKENS = 320
GENERATION_TEMPERATURE = 0.3
GENERATION_TOP_P = 0.9
GENERATION_REPETITION_PENALTY = 1.1
STREAM_TOKENS = True

SYSTEM_PROMPT = (
    "You are PetCare+, an evidence-grounded pet-care information assistant.\n\n"
    "Answer using the supplied knowledge context.\n\n"
    "Rules:\n"
    "1. Prefer supplied evidence over unsupported model knowledge.\n"
    "2. Never invent facts, sources, studies, medications, or dosages.\n"
    "3. If evidence is insufficient, say so.\n"
    "4. Do not diagnose an animal.\n"
    "5. Do not claim certainty when evidence is uncertain.\n"
    "6. Do not prescribe prescription medication.\n"
    "7. Do not invent medication doses.\n"
    "8. Consider species, breed, age, and context.\n"
    "9. Clearly identify when veterinary evaluation is appropriate.\n"
    "10. For possible emergencies, prioritize veterinary care.\n"
    "11. Keep answers practical and understandable.\n"
    "12. Cite factual claims using supplied source information.\n"
    "13. Never fabricate citations.\n"
    "14. PetCare+ is an information assistant and does not replace a veterinarian."
)

# ---------------------------------------------------------------------------
# Cache environment configuration
# ---------------------------------------------------------------------------
def configure_caches() -> None:
    """Point every relevant Hugging Face / Torch cache to the D: drive.

    This must run BEFORE transformers / torch / huggingface_hub are imported
    so that downloaded artifacts never land on C:.
    """
    os.environ.setdefault("HF_HOME", str(HF_DIR))
    os.environ.setdefault("HF_HUB_CACHE", str(HF_HUB_CACHE))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(TRANSFORMERS_CACHE))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(HF_HUB_CACHE))
    # Current / legacy keys honoured by the installed HF stack.
    os.environ.setdefault("HF_DATASETS_CACHE", str(CACHE_DIR / "hf_datasets"))
    os.environ.setdefault("TORCH_HOME", str(TORCH_DIR))
    os.environ.setdefault("TORCH_CACHE", str(TORCH_DIR / "cache"))
    os.environ.setdefault("TRITON_CACHE", str(TEMP_DIR / "triton"))
    os.environ.setdefault("TMPDIR", str(TEMP_DIR))
    os.environ.setdefault("TEMP", str(TEMP_DIR))
    os.environ.setdefault("TMP", str(TEMP_DIR))
    # Prefer offline operation once artifacts are present.
    os.environ.setdefault("HF_HUB_OFFLINE", "0")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "0")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def ensure_root() -> None:
    """Verify the storage root exists and is writable.

    PetCare+ must NOT silently fall back to C: for large assets. If the D:
    drive root is unavailable we raise a clear, actionable error for the
    developer / operator.
    """
    try:
        PETCARE_ROOT.mkdir(parents=True, exist_ok=True)
        # Probe writability with a throwaway file.
        probe = PETCARE_ROOT / ".petcare_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "PetCare+ storage root is unavailable or not writable:\n"
            f"  {PETCARE_ROOT}\n\n"
            "All models, caches and the knowledge base require this location on "
            "the D: drive. PetCare+ will not silently fall back to C:.\n"
            "Please attach/repair the D: drive or set PETCARE_ROOT to another "
            "explicit path before launching."
        ) from exc


def ensure_directories() -> None:
    """Create the full runtime directory tree under the storage root."""
    for d in (
        APP_DIR, MODELS_DIR, EMBEDDINGS_DIR, LLM_DIR, HF_DIR, HF_HUB_CACHE,
        TRANSFORMERS_CACHE, TORCH_DIR, CACHE_DIR, TEMP_DIR, KNOWLEDGE_DIR,
        DATA_DIR, PETS_DIR, CONVERSATIONS_DIR, LOG_DIR, ASSETS_DIR, ICONS_DIR,
        ILLUSTRATIONS_DIR, DEVELOPER_DIR, SOURCE_DIR, EVALUATION_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
