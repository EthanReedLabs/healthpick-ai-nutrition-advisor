from __future__ import annotations

import pytest

from scripts.smoke_local_stack import parse_sse


def test_parse_sse_preserves_event_order_and_multiline_data() -> None:
    events = parse_sse(
        'event: meta\ndata: {"route":"nutrition"}\n\n'
        'event: final\ndata: {"answer":"ok",\n'
        'data: "citations":[]}\n'
    )
    assert [name for name, _ in events] == ["meta", "final"]
    assert events[-1][1] == {"answer": "ok", "citations": []}


@pytest.mark.parametrize("body", ["", "event: final", 'data: {"answer":"ok"}'])
def test_parse_sse_rejects_incomplete_blocks(body: str) -> None:
    with pytest.raises(RuntimeError, match="missing event or data"):
        parse_sse(body)
