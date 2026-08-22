"""Prove that real citations pass and tampered citations fail closed."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from healthpick_api.evidence import CitationBuilder, EvidenceValidator  # noqa: E402
from healthpick_api.retrieval import KeywordRetriever, KnowledgeIndex  # noqa: E402
from healthpick_api.routing import QueryRouter  # noqa: E402

OUTPUT = ROOT / "docs" / "evidence" / "phase-03-citation-runtime.json"


def main() -> None:
    index = KnowledgeIndex.load_default(ROOT)
    query = "膳食纤维有什么营养作用？"
    decision = QueryRouter().route(query)
    retrieval = KeywordRetriever(index).search(query, decision, limit=4)
    bundle = CitationBuilder(excerpt_chars=160).build(retrieval)
    citation = bundle.citations[0]
    answer = f"该结论来自指定资料中的膳食纤维章节【{citation.chunk_id}】。"

    validator = EvidenceValidator(index)
    valid = validator.validate(
        answer=answer,
        citations=(citation,),
        decision=decision,
    )
    tampered = citation.model_copy(update={"page": citation.page + 100})
    invalid = validator.validate(
        answer=answer,
        citations=(tampered,),
        decision=decision,
    )
    assert valid.valid is True
    assert invalid.valid is False
    assert "citation_metadata_mismatch" in invalid.error_codes

    evidence = {
        "schema_version": 1,
        "task_id": "P03-04",
        "checked_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "query": query,
        "route": decision.route,
        "citation": {
            "chunk_id": citation.chunk_id,
            "source": citation.source,
            "title": citation.title,
            "page": citation.page,
            "section": citation.section,
            "excerpt_chars": len(citation.excerpt),
            "excerpt_is_exact_substring": True,
        },
        "context_delimiters": {
            "start": f"[EVIDENCE {citation.chunk_id}]",
            "end": f"[END EVIDENCE {citation.chunk_id}]",
        },
        "valid_case": {
            "valid": valid.valid,
            "referenced_chunk_ids": list(valid.referenced_chunk_ids),
            "error_codes": list(valid.error_codes),
        },
        "tampered_page_case": {
            "valid": invalid.valid,
            "error_codes": list(invalid.error_codes),
        },
        "result": "pass",
    }
    OUTPUT.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
