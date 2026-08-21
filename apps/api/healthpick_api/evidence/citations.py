"""Build stable citations and prompt context directly from retrieval hits."""

from __future__ import annotations

from dataclasses import dataclass

from healthpick_api.models import Citation
from healthpick_api.retrieval import RetrievalResult


@dataclass(frozen=True, slots=True)
class CitationBundle:
    citations: tuple[Citation, ...]
    context_blocks: tuple[str, ...]


class CitationBuilder:
    def __init__(self, *, excerpt_chars: int = 220, context_chars: int = 900) -> None:
        if excerpt_chars < 40:
            raise ValueError("excerpt_chars must be at least 40")
        if context_chars < excerpt_chars:
            raise ValueError("context_chars cannot be shorter than excerpt_chars")
        self.excerpt_chars = excerpt_chars
        self.context_chars = context_chars

    def build(self, result: RetrievalResult) -> CitationBundle:
        citations: list[Citation] = []
        context_blocks: list[str] = []
        for hit in result.hits:
            chunk = hit.chunk
            excerpt = _extract_excerpt(
                chunk.content,
                hit.matched_terms,
                max_chars=self.excerpt_chars,
            )
            citations.append(
                Citation(
                    chunk_id=chunk.chunk_id,
                    source=chunk.source_code,  # type: ignore[arg-type]
                    title=chunk.source_title,
                    page=chunk.page,
                    section=chunk.section,
                    excerpt=excerpt,
                )
            )
            context = chunk.content[: self.context_chars]
            context_blocks.append(
                "\n".join(
                    (
                        f"[EVIDENCE {chunk.chunk_id}]",
                        f"source={chunk.source_code}; page={chunk.page}; section={chunk.section}",
                        context,
                        f"[END EVIDENCE {chunk.chunk_id}]",
                    )
                )
            )
        return CitationBundle(citations=tuple(citations), context_blocks=tuple(context_blocks))


def _extract_excerpt(
    content: str,
    matched_terms: tuple[str, ...],
    *,
    max_chars: int,
) -> str:
    if len(content) <= max_chars:
        return content
    positions = [content.lower().find(term.lower()) for term in matched_terms]
    positions = [position for position in positions if position >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - max_chars // 4)
    end = min(len(content), start + max_chars)
    start = max(0, end - max_chars)
    return content[start:end]
