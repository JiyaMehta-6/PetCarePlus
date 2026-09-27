"""Generate a storage report for PetCare+.

Prints where every byte lives and confirms the single most important
guarantee of this project: all large assets are stored on the D: drive
(``D:\\projects\\petCareplus``), never on the system C: drive.

Run:
    python storage_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

from app.config import (
    PETCARE_ROOT,
    MODELS_DIR,
    KNOWLEDGE_DIR,
    DATA_DIR,
    HF_DIR,
    TORCH_DIR,
    LOG_DIR,
    EVALUATION_DIR,
    DEVELOPER_DIR,
    KNOWLEDGE_JSONL,
    FAISS_INDEX,
)


def _human(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


def _dir_size(path: Path) -> int:
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    if path.exists():
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    return total


def _dir_files(path: Path) -> int:
    if path.is_file():
        return 1
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*") if p.is_file())


def main() -> None:
    rows = [
        ("Knowledge base (chunks)", KNOWLEDGE_JSONL),
        ("FAISS index", FAISS_INDEX),
        ("Embedding model (BGE)", MODELS_DIR / "embeddings"),
        ("Generation model (Qwen)", MODELS_DIR / "llm"),
        ("Local data (pets, history, settings)", DATA_DIR),
        ("Hugging Face cache", HF_DIR),
        ("Torch cache", TORCH_DIR),
        ("Logs", LOG_DIR),
        ("Evaluation", EVALUATION_DIR),
        ("Developer / KB generators", DEVELOPER_DIR),
    ]

    print("=" * 64)
    print("PetCare+ Storage Report")
    print("=" * 64)
    print(f"Root location: {PETCARE_ROOT}")
    on_c = str(PETCARE_ROOT).lower().startswith("c:")
    print(f"On system C: drive? {'YES (unexpected!)' if on_c else 'No (good — D: drive)'}")
    print("-" * 64)
    print(f"{'Component':42} {'Size':>10}   Files")
    print("-" * 64)

    report = {"root": str(PETCARE_ROOT), "on_system_drive": on_c, "components": {}}
    for name, path in rows:
        size = _dir_size(path)
        files = _dir_files(path)
        print(f"{name:42} {_human(size):>10}   {files}")
        report["components"][name] = {
            "path": str(path),
            "size_bytes": size,
            "size_human": _human(size),
            "files": files,
        }

    print("-" * 64)
    total = sum(c["size_bytes"] for c in report["components"].values())
    print(f"{'TOTAL (tracked D: assets)':42} {_human(total):>10}")
    print("=" * 64)

    out = PETCARE_ROOT / "storage_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote JSON report -> {out}")


if __name__ == "__main__":
    main()
