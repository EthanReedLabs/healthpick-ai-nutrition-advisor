"""Shared canonical session/conversation setup for runtime smoke scripts."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx2


@dataclass(slots=True)
class RuntimeConversationScope:
    client: httpx2.AsyncClient
    api_origin: str
    session_id: str
    conversation_ids: list[str] = field(default_factory=list)

    @classmethod
    async def create(cls, client: httpx2.AsyncClient, api_origin: str) -> RuntimeConversationScope:
        response = await client.post(f"{api_origin}/v1/sessions/anonymous")
        response.raise_for_status()
        return cls(
            client=client,
            api_origin=api_origin,
            session_id=response.json()["session_id"],
        )

    async def new_conversation(self, title: str) -> str:
        response = await self.client.post(
            f"{self.api_origin}/v1/conversations",
            json={"session_id": self.session_id, "title": title[:80]},
        )
        response.raise_for_status()
        conversation_id = response.json()["conversation_id"]
        self.conversation_ids.append(conversation_id)
        return conversation_id

    async def cleanup(self) -> None:
        for conversation_id in reversed(self.conversation_ids):
            response = await self.client.delete(
                f"{self.api_origin}/v1/conversations/{conversation_id}",
                params={"session_id": self.session_id},
            )
            response.raise_for_status()
