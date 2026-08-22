"""Run auditable routing/retrieval probes against the real normalized chunks."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from healthpick_api.retrieval import KeywordRetriever, KnowledgeIndex  # noqa: E402
from healthpick_api.routing import QueryRouter  # noqa: E402

OUTPUT = ROOT / "docs" / "evidence" / "phase-03-retrieval-runtime.json"

QUERIES = {
    "nutrition": "膳食纤维有什么营养作用？",
    "recommendation": "帮我搭配一份增肌早餐食谱",
    "platform": "平台会员和企业服务有哪些？",
    "mixed": "平台会员能否获得低钠饮食建议？",
    "out_of_scope": "如何修复汽车发动机？",
}


def main() -> None:
    index = KnowledgeIndex.load_default(ROOT)
    router = QueryRouter()
    retriever = KeywordRetriever(index)
    probes: list[dict[str, object]] = []

    for name, query in QUERIES.items():
        decision = router.route(query)
        result = retriever.search(query, decision, limit=6)
        sources = {hit.chunk.source_code for hit in result.hits}
        if decision.route in {"nutrition", "recommendation", "contraindication"}:
            assert sources <= {"A", "B"}
        elif decision.route == "platform":
            assert sources == {"C"}
        elif decision.route == "mixed":
            assert sources & {"A", "B"} and "C" in sources
        else:
            assert not result.hits

        probes.append(
            {
                "name": name,
                "query": query,
                "route": decision.route,
                "components": list(decision.components),
                "allowed_sources": list(decision.allowed_sources),
                "reason_codes": list(decision.reason_codes),
                "trace": {
                    "mode": result.trace.mode,
                    "examined_chunks": result.trace.examined_chunks,
                    "eligible_chunks": result.trace.eligible_chunks,
                    "rejected_by_source_boundary": result.trace.rejected_by_source_boundary,
                    "returned_chunks": result.trace.returned_chunks,
                },
                "hits": [
                    {
                        "chunk_id": hit.chunk.chunk_id,
                        "source": hit.chunk.source_code,
                        "page": hit.chunk.page,
                        "section": hit.chunk.section,
                        "score": hit.score,
                        "matched_terms": list(hit.matched_terms),
                    }
                    for hit in result.hits
                ],
            }
        )

    evidence = {
        "schema_version": 1,
        "task_id": "P03-03",
        "checked_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "retrieval_mode": "keyword",
        "embedding_claimed": False,
        "chunk_counts": {source: len(chunks) for source, chunks in index.by_source.items()},
        "probes": probes,
        "result": "pass",
    }
    OUTPUT.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
