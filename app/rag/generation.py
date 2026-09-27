"""Local LLM generation with Qwen2.5 (3B primary, 1.5B fallback).

All generation happens locally. Models are loaded from the D: drive model
directory (or downloaded there once during setup). GPU is used automatically
when available; CPU is fully supported. A 4-bit load is used on CUDA when
bitsandbytes is available; otherwise float32/16 is used.
"""

from __future__ import annotations

import os
import threading
from typing import Callable, Iterator

import torch

from app.config import (
    LLM_MODEL_LOCAL,
    LLM_MODEL_PRIMARY,
    LLM_MODEL_FALLBACK,
    GENERATION_MAX_NEW_TOKENS,
    GENERATION_TEMPERATURE,
    GENERATION_TOP_P,
    GENERATION_REPETITION_PENALTY,
    SYSTEM_PROMPT,
    EMBEDDING_DTYPE,
)
from app.log_utils import get_logger

logger = get_logger("petcare.generation")


class GenerationError(Exception):
    """Raised when the local model cannot be loaded or run."""


class Generation:
    def __init__(self, model_path: str | None = None, fallback_path: str | None = None):
        self.model_path = model_path or LLM_MODEL_LOCAL
        self.fallback_id = fallback_path or LLM_MODEL_FALLBACK
        self.device = self._resolve_device()
        self.tokenizer = None
        self.model = None
        self._ready = False

    @staticmethod
    def _resolve_device() -> str:
        if torch.cuda.is_available():
            return "cuda"
        try:
            if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        return "cpu"

    # ------------------------------------------------------------------
    def load(self) -> None:
        if self._ready:
            return
        from transformers import AutoModelForCausalLM, AutoTokenizer

        source = self._resolve_source()
        logger.info("Loading generation model from %s on %s", source, self.device)

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(source, local_files_only=True)
            self.model = self._build_model(source, AutoModelForCausalLM)
        except Exception as primary_err:  # pragma: no cover - environment dependent
            logger.warning("Primary model load failed: %s", primary_err)
            if source != self.fallback_id:
                logger.info("Falling back to %s", self.fallback_id)
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(
                        self.fallback_id, local_files_only=True
                    )
                    self.model = self._build_model(self.fallback_id, AutoModelForCausalLM)
                except Exception:
                    raise GenerationError(
                        "Local generation model is not available. Run setup to download it."
                    ) from primary_err
            else:
                raise GenerationError(
                    "Local generation model is not available. Run setup to download it."
                ) from primary_err

        self.model.eval()
        self._ready = True

    def _resolve_source(self) -> str:
        local = self.model_path
        if os.path.isdir(local) and os.path.exists(os.path.join(local, "config.json")):
            return local
        # Runtime must not attempt a network download; fail fast and let the UI
        # report the missing-model state gracefully.
        raise GenerationError(
            f"Local generation model not found at {local}. "
            "Run setup_windows.ps1 to download it into the D: drive."
        )

    def _build_model(self, source: str, cls):
        torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
        use_4bit = self.device == "cuda"
        try:
            if use_4bit:
                from transformers import BitsAndBytesConfig

                quant = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_low_bit_quantization=True,
                )
                return cls.from_pretrained(
                    source,
                    quantization_config=quant,
                    dtype=torch.float16,
                    device_map="auto",
                )
        except Exception as err:  # bitsandbytes may be unavailable
            logger.warning("4-bit load unavailable (%s); using float weights", err)
        return cls.from_pretrained(source, dtype=torch_dtype).to(self.device)

    # ------------------------------------------------------------------
    def _build_messages(self, system_prompt: str, user_prompt: str, history=None):
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for turn in history[-6:]:
                messages.append({"role": "user", "content": turn.get("user", "")})
                messages.append({"role": "assistant", "content": turn.get("assistant", "")})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def generate(
        self,
        context: str,
        query: str,
        safety_instruction: str = "",
        pet_context: str = "",
        history=None,
        callback: Callable[[str], None] | None = None,
        max_new_tokens: int = GENERATION_MAX_NEW_TOKENS,
    ) -> str:
        if not self._ready:
            self.load()

        system = SYSTEM_PROMPT
        if safety_instruction:
            system += "\n\n" + safety_instruction

        pet_line = ""
        if pet_context:
            pet_line = (
                f"Pet the question is about: {pet_context}. "
                "Honour this species/breed/age context when answering; do not give "
                "guidance for other species.\n\n"
            )

        user = (
            pet_line +
            "Use the retrieved knowledge below to answer the user's question. "
            "Cite factual claims with [n] matching the source numbering. "
            "If the knowledge is insufficient, say so and suggest a veterinarian. "
            "Do not invent sources.\n\n"
            f"RETRIEVED KNOWLEDGE:\n{context}\n\n"
            f"USER QUESTION:\n{query}\n\n"
            "ANSWER:"
        )

        messages = self._build_messages(system, user, history)
        encoded = self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        )
        # transformers >=5 returns a BatchFeature rather than a raw tensor.
        if hasattr(encoded, "input_ids"):
            input_ids = encoded.input_ids.to(self.device)
            attn = getattr(encoded, "attention_mask", None)
            attention_mask = attn.to(self.device) if attn is not None else None
        else:
            input_ids = encoded.to(self.device)
            attention_mask = None

        if callback is not None:
            return self._stream(input_ids, attention_mask, max_new_tokens, callback)
        return self._static(input_ids, attention_mask, max_new_tokens)

    def _static(self, input_ids, attention_mask, max_new_tokens: int) -> str:
        gen_kwargs = self._gen_kwargs(input_ids, attention_mask, max_new_tokens)
        gen_kwargs["do_sample"] = False  # greedy: faster and more concise on CPU
        gen_kwargs.pop("temperature", None)
        gen_kwargs.pop("top_p", None)
        with torch.no_grad():
            out = self.model.generate(**gen_kwargs)
        gen = out[0][input_ids.shape[1]:]
        return self.tokenizer.decode(gen, skip_special_tokens=True).strip()

    def _gen_kwargs(self, input_ids, attention_mask, max_new_tokens: int) -> dict:
        kwargs = dict(
            input_ids=input_ids,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=GENERATION_TEMPERATURE,
            top_p=GENERATION_TOP_P,
            repetition_penalty=GENERATION_REPETITION_PENALTY,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        if attention_mask is not None:
            kwargs["attention_mask"] = attention_mask
        return kwargs

    def _stream(self, input_ids, attention_mask, max_new_tokens: int, callback: Callable[[str], None]) -> str:
        from transformers import TextIteratorStreamer

        streamer = TextIteratorStreamer(
            self.tokenizer, skip_prompt=True, skip_special_tokens=True
        )
        gen_kwargs = self._gen_kwargs(input_ids, attention_mask, max_new_tokens)
        gen_kwargs["do_sample"] = False  # greedy: consistent with _static, faster on CPU
        gen_kwargs.pop("temperature", None)
        gen_kwargs.pop("top_p", None)
        gen_kwargs["streamer"] = streamer

        buffer = []

        def _run():
            with torch.no_grad():
                self.model.generate(**gen_kwargs)

        thread = threading.Thread(target=_run)
        thread.start()
        for piece in streamer:
            if piece:
                buffer.append(piece)
                callback(piece)
        thread.join()
        return "".join(buffer).strip()
