"""Bounded process-local session context; persistence is intentionally deferred to P05."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    user_message: str
    assistant_message: str
    request_id: str
    route: str


class EphemeralConversationStore:
    mode = "ephemeral"

    def __init__(self, *, max_conversations: int = 1000, max_turns: int = 12) -> None:
        if max_conversations < 1 or max_turns < 1:
            raise ValueError("conversation limits must be positive")
        self.max_conversations = max_conversations
        self.max_turns = max_turns
        self._conversations: OrderedDict[str, tuple[ConversationTurn, ...]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def history(self, conversation_id: str) -> tuple[ConversationTurn, ...]:
        async with self._lock:
            turns = self._conversations.get(conversation_id, ())
            if turns:
                self._conversations.move_to_end(conversation_id)
            return turns

    async def append(self, conversation_id: str, turn: ConversationTurn) -> None:
        async with self._lock:
            current = self._conversations.get(conversation_id, ())
            self._conversations[conversation_id] = (*current, turn)[-self.max_turns :]
            self._conversations.move_to_end(conversation_id)
            while len(self._conversations) > self.max_conversations:
                self._conversations.popitem(last=False)
