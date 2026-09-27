"""Dense embedding model wrapper.

Uses BAAI/bge-small-en-v1.5 loaded from the local D: drive model directory.
Embeddings are L2-normalised so that inner-product search in FAISS equals
cosine similarity.
"""

from __future__ import annotations

import os
from functools import lru_cache

import numpy as np

from app.config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL_ID,
    EMBEDDING_MODEL_LOCAL,
    EMBEDDING_DTYPE,
    configure_caches,
    ensure_directories,
)
from app.log_utils import get_logger

logger = get_logger("petcare.embeddings")

# BGE models expect this instruction prefix on *queries* for best retrieval.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class EmbeddingModel:
    def __init__(self, model_path: str | None = None, device: str = "auto"):
        configure_caches()
        ensure_directories()
        self.model_path = model_path or EMBEDDING_MODEL_LOCAL
        self.device = self._resolve_device(device)
        self._model = None
        self._tokenizer = None
        self._ready = False

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device != "auto":
            return device
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        return "cpu"

    def load(self) -> None:
        if self._ready:
            return
        from transformers import AutoModel, AutoTokenizer

        # Honour a locally cached copy first; otherwise download into D:.
        local = self.model_path
        use_local = os.path.isdir(local) and any(
            os.path.exists(os.path.join(local, f))
            for f in ("config.json", "pytorch_model.bin", "model.safetensors", "tokenizer.json")
        )
        source = local if use_local else EMBEDDING_MODEL_ID
        logger.info("Loading embedding model from %s on %s", source, self.device)
        self._tokenizer = AutoTokenizer.from_pretrained(source)
        self._model = AutoModel.from_pretrained(source)
        self._model.to(self.device)
        self._model.eval()
        self._ready = True

    def _mean_pool(self, hidden, mask):
        import torch

        mask = mask.unsqueeze(-1).float()
        summed = torch.sum(hidden * mask, dim=1)
        counts = torch.clamp(torch.sum(mask, dim=1), min=1e-9)
        return summed / counts

    def encode(self, texts, batch_size: int = 32, is_query: bool = False):
        if not self._ready:
            self.load()
        import torch

        single = isinstance(texts, str)
        if single:
            texts = [texts]

        if is_query:
            texts = [QUERY_INSTRUCTION + t for t in texts]

        all_vecs = []
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                enc = self._tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                )
                enc = {k: v.to(self.device) for k, v in enc.items()}
                out = self._model(**enc)
                hidden = out.last_hidden_state
                pooled = self._mean_pool(hidden, enc["attention_mask"])
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
                all_vecs.append(pooled.cpu().numpy().astype(np.float32))
        vecs = np.vstack(all_vecs).astype(np.float32)
        if single:
            return vecs[0]
        return vecs

    @property
    def dim(self) -> int:
        return EMBEDDING_DIM

    @property
    def dtype(self) -> str:
        return EMBEDDING_DTYPE
