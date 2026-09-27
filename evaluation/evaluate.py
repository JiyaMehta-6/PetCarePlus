"""PetCare+ retrieval + safety evaluation harness.

Runs the curated evaluation questions through the RAG engine and scores:
  * retrieval recall  - at least one source relevant to the expected species/topic
  * safety detection   - urgent/caution flagged when expected
  * citation presence  - answer contains [n] markers when sources exist

Generation is exercised only if a local model is present; otherwise the
graceful "model missing" path is scored as a pass for retrieval/safety.

Run:
    python evaluation/evaluate.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from app.config import EVALUATION_DIR
from app.log_utils import setup_logging, get_logger

logger = get_logger("petcare.eval")


def _topic_match(chunk_topic: str, expected: str) -> bool:
    if not expected:
        return True
    return expected.lower() in (chunk_topic or "").lower()


def evaluate(engine, questions: list[dict]) -> dict:
    results = []
    for item in questions:
        q = item["q"]
        expected_species = item.get("species", "")
        expected_topic = item.get("topic", "")
        expect_safety = bool(item.get("expect_safety", False))

        ans = engine.answer(q)
        sources = ans.sources
        safety_flagged = ans.safety is not None and ans.safety.level != "none"

        # Retrieval recall: any retrieved chunk whose species set includes the
        # expected species, or whose topic matches the expected topic.
        recalled = False
        for c in (ans.cited_chunks or []):
            species = [x.lower() for x in (c.species or [])]
            if expected_species and expected_species.lower() in species:
                recalled = True
                break
        if not recalled and (ans.cited_chunks or []):
            recalled = any(_topic_match(c.topic, expected_topic) for c in ans.cited_chunks)

        citations_ok = True
        if sources and not ans.generation_error:
            # Only enforce citations when the local model actually generated text.
            citations_ok = bool(re.search(r"\[\d{1,2}\]", ans.answer_text))

        safety_ok = (safety_flagged == expect_safety)
        ok = recalled and safety_ok and citations_ok

        results.append({
            "q": q,
            "recalled": recalled,
            "safety_flagged": safety_flagged,
            "safety_ok": safety_ok,
            "citations_ok": citations_ok,
            "confidence": round(ans.confidence, 3),
            "n_sources": len(sources),
            "ok": ok,
        })

    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    recall = sum(1 for r in results if r["recalled"]) / total if total else 0
    safety_acc = sum(1 for r in results if r["safety_ok"]) / total if total else 0
    citation_acc = sum(1 for r in results if r["citations_ok"]) / total if total else 0

    return {
        "total": total,
        "passed": passed,
        "recall": round(recall, 3),
        "safety_accuracy": round(safety_acc, 3),
        "citation_accuracy": round(citation_acc, 3),
        "results": results,
    }


def main() -> int:
    setup_logging()
    qfile = EVALUATION_DIR / "questions.json"
    if not qfile.exists():
        logger.error("Missing evaluation questions: %s", qfile)
        return 1
    questions = json.loads(qfile.read_text(encoding="utf-8"))["questions"]

    from app.rag.engine import RAGEngine
    engine = RAGEngine()
    engine.initialize(load_generation=False)

    report = evaluate(engine, questions)
    out = EVALUATION_DIR / "eval_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=" * 60)
    print("PetCare+ Evaluation")
    print("=" * 60)
    print(f"Questions           : {report['total']}")
    print(f"Fully passing       : {report['passed']}/{report['total']}")
    print(f"Retrieval recall    : {report['recall']:.0%}")
    print(f"Safety accuracy     : {report['safety_accuracy']:.0%}")
    print(f"Citation accuracy   : {report['citation_accuracy']:.0%}")
    print("-" * 60)
    for r in report["results"]:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"[{mark}] {r['q']}  (rec={r['recalled']}, saf={r['safety_ok']}, "
              f"cit={r['citations_ok']}, conf={r['confidence']})")
    print("=" * 60)
    print(f"Wrote {out}")
    return 0 if report["passed"] == report["total"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
