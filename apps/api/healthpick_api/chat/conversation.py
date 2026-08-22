"""Conversation repositories with canonical server IDs and PostgreSQL persistence."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar
from uuid import UUID, uuid4

from psycopg import DatabaseError, OperationalError, connect
from psycopg.errors import QueryCanceled
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

T = TypeVar("T")


class ConversationStoreError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class AnonymousSessionRecord:
    session_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationRecord:
    conversation_id: str
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    turn_count: int = 0


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    user_message: str
    assistant_message: str
    request_id: str
    route: str
    context_eligible: bool = True
    response_payload: dict[str, Any] | None = None
    turn_id: str | None = None
    created_at: datetime | None = None


class ConversationStore(Protocol):
    mode: str

    async def create_session(self) -> AnonymousSessionRecord: ...

    async def delete_session(self, session_id: str) -> None: ...

    async def create_conversation(
        self, session_id: str, *, title: str = "新对话"
    ) -> ConversationRecord: ...

    async def list_conversations(
        self, session_id: str, *, limit: int = 50
    ) -> tuple[ConversationRecord, ...]: ...

    async def get_conversation(
        self, conversation_id: str, *, session_id: str
    ) -> tuple[ConversationRecord, tuple[ConversationTurn, ...]]: ...

    async def rename_conversation(
        self, conversation_id: str, *, session_id: str, title: str
    ) -> ConversationRecord: ...

    async def delete_conversation(self, conversation_id: str, *, session_id: str) -> None: ...

    async def history(
        self, conversation_id: str, *, session_id: str | None = None
    ) -> tuple[ConversationTurn, ...]: ...

    async def append(
        self,
        conversation_id: str,
        turn: ConversationTurn,
        *,
        session_id: str | None = None,
    ) -> ConversationTurn: ...

    async def clear(self, conversation_id: str, *, session_id: str | None = None) -> None: ...

    async def probe(self) -> bool: ...


class EphemeralConversationStore:
    """Bounded process-local store used only when explicitly configured or in tests."""

    mode = "ephemeral"

    def __init__(self, *, max_conversations: int = 1000, max_turns: int = 12) -> None:
        if max_conversations < 1 or max_turns < 1:
            raise ValueError("conversation limits must be positive")
        self.max_conversations = max_conversations
        self.max_turns = max_turns
        self._sessions: dict[str, AnonymousSessionRecord] = {}
        self._records: OrderedDict[str, ConversationRecord] = OrderedDict()
        self._conversations: OrderedDict[str, tuple[ConversationTurn, ...]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def create_session(self) -> AnonymousSessionRecord:
        async with self._lock:
            now = datetime.now(UTC)
            record = AnonymousSessionRecord(session_id=str(uuid4()), created_at=now)
            self._sessions[record.session_id] = record
            return record

    async def delete_session(self, session_id: str) -> None:
        async with self._lock:
            self._require_session(session_id)
            conversation_ids = [
                conversation_id
                for conversation_id, record in self._records.items()
                if record.session_id == session_id
            ]
            for conversation_id in conversation_ids:
                self._records.pop(conversation_id, None)
                self._conversations.pop(conversation_id, None)
            self._sessions.pop(session_id, None)

    async def create_conversation(
        self, session_id: str, *, title: str = "新对话"
    ) -> ConversationRecord:
        async with self._lock:
            self._require_session(session_id)
            now = datetime.now(UTC)
            record = ConversationRecord(
                conversation_id=str(uuid4()),
                session_id=session_id,
                title=_clean_title(title),
                created_at=now,
                updated_at=now,
            )
            self._records[record.conversation_id] = record
            self._conversations[record.conversation_id] = ()
            self._evict_if_needed()
            return record

    async def list_conversations(
        self, session_id: str, *, limit: int = 50
    ) -> tuple[ConversationRecord, ...]:
        async with self._lock:
            self._require_session(session_id)
            records = [
                record for record in self._records.values() if record.session_id == session_id
            ]
            records.sort(key=lambda item: (item.updated_at, item.conversation_id), reverse=True)
            return tuple(records[:limit])

    async def get_conversation(
        self, conversation_id: str, *, session_id: str
    ) -> tuple[ConversationRecord, tuple[ConversationTurn, ...]]:
        async with self._lock:
            record = self._require_conversation(conversation_id, session_id)
            return record, self._conversations.get(conversation_id, ())

    async def rename_conversation(
        self, conversation_id: str, *, session_id: str, title: str
    ) -> ConversationRecord:
        async with self._lock:
            record = self._require_conversation(conversation_id, session_id)
            updated = replace(record, title=_clean_title(title), updated_at=datetime.now(UTC))
            self._records[conversation_id] = updated
            return updated

    async def delete_conversation(self, conversation_id: str, *, session_id: str) -> None:
        async with self._lock:
            self._require_conversation(conversation_id, session_id)
            self._records.pop(conversation_id, None)
            self._conversations.pop(conversation_id, None)

    async def history(
        self, conversation_id: str, *, session_id: str | None = None
    ) -> tuple[ConversationTurn, ...]:
        async with self._lock:
            if session_id is not None:
                self._require_conversation(conversation_id, session_id)
            turns = tuple(
                turn
                for turn in self._conversations.get(conversation_id, ())
                if turn.context_eligible
            )
            if turns:
                self._conversations.move_to_end(conversation_id)
            return turns

    async def append(
        self,
        conversation_id: str,
        turn: ConversationTurn,
        *,
        session_id: str | None = None,
    ) -> ConversationTurn:
        async with self._lock:
            record = None
            if session_id is not None:
                record = self._require_conversation(conversation_id, session_id)
            current = self._conversations.get(conversation_id, ())
            for existing in current:
                if existing.request_id == turn.request_id:
                    return existing
            persisted = replace(
                turn,
                turn_id=turn.turn_id or str(uuid4()),
                created_at=turn.created_at or datetime.now(UTC),
            )
            self._conversations[conversation_id] = (*current, persisted)[-self.max_turns :]
            self._conversations.move_to_end(conversation_id)
            if record is not None:
                title = (
                    _first_message_title(turn.user_message)
                    if not current and record.title == "新对话"
                    else record.title
                )
                self._records[conversation_id] = replace(
                    record,
                    title=title,
                    updated_at=persisted.created_at or datetime.now(UTC),
                    turn_count=record.turn_count + 1,
                )
            self._evict_if_needed()
            return persisted

    async def clear(self, conversation_id: str, *, session_id: str | None = None) -> None:
        """Remove committed context after a safety terminal event without deleting its shell."""
        async with self._lock:
            if session_id is not None:
                record = self._require_conversation(conversation_id, session_id)
                self._records[conversation_id] = replace(
                    record, updated_at=datetime.now(UTC), turn_count=0
                )
            current = self._conversations.get(conversation_id, ())
            self._conversations[conversation_id] = tuple(
                replace(turn, context_eligible=False) for turn in current
            )

    async def probe(self) -> bool:
        return True

    def _require_session(self, session_id: str) -> AnonymousSessionRecord:
        record = self._sessions.get(session_id)
        if record is None:
            raise _not_found()
        return record

    def _require_conversation(self, conversation_id: str, session_id: str) -> ConversationRecord:
        record = self._records.get(conversation_id)
        if record is None or record.session_id != session_id:
            raise _not_found()
        return record

    def _evict_if_needed(self) -> None:
        while len(self._conversations) > self.max_conversations:
            conversation_id, _ = self._conversations.popitem(last=False)
            self._records.pop(conversation_id, None)


class PostgresConversationStore:
    """PostgreSQL repository using one short, transactional sync connection per operation."""

    mode = "postgres"

    def __init__(
        self,
        database_url: str,
        *,
        connect_timeout_seconds: int = 5,
        statement_timeout_ms: int = 5000,
    ) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self.connect_timeout_seconds = connect_timeout_seconds
        self.statement_timeout_ms = statement_timeout_ms

    async def create_session(self) -> AnonymousSessionRecord:
        def operation() -> AnonymousSessionRecord:
            with self._connect() as connection:
                row = connection.execute(
                    "INSERT INTO anonymous_sessions DEFAULT VALUES RETURNING id, created_at"
                ).fetchone()
                assert row is not None
                return AnonymousSessionRecord(
                    session_id=str(row["id"]), created_at=row["created_at"]
                )

        return await self._run(operation)

    async def delete_session(self, session_id: str) -> None:
        session_uuid = _uuid(session_id)

        def operation() -> None:
            with self._connect() as connection:
                row = connection.execute(
                    "DELETE FROM anonymous_sessions WHERE id = %s RETURNING id",
                    (session_uuid,),
                ).fetchone()
                if row is None:
                    raise _not_found()

        await self._run(operation)

    async def create_conversation(
        self, session_id: str, *, title: str = "新对话"
    ) -> ConversationRecord:
        session_uuid = _uuid(session_id)
        clean_title = _clean_title(title)

        def operation() -> ConversationRecord:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    INSERT INTO conversations (session_id, title)
                    SELECT id, %s FROM anonymous_sessions WHERE id = %s
                    RETURNING id, session_id, title, created_at, updated_at
                    """,
                    (clean_title, session_uuid),
                ).fetchone()
                if row is None:
                    raise _not_found()
                return _conversation_record(row)

        return await self._run(operation)

    async def list_conversations(
        self, session_id: str, *, limit: int = 50
    ) -> tuple[ConversationRecord, ...]:
        session_uuid = _uuid(session_id)

        def operation() -> tuple[ConversationRecord, ...]:
            with self._connect() as connection:
                session = connection.execute(
                    "SELECT 1 FROM anonymous_sessions WHERE id = %s", (session_uuid,)
                ).fetchone()
                if session is None:
                    raise _not_found()
                rows = connection.execute(
                    """
                    SELECT c.id, c.session_id, c.title, c.created_at, c.updated_at,
                           count(t.id)::integer AS turn_count
                    FROM conversations c
                    LEFT JOIN conversation_turns t ON t.conversation_id = c.id
                    WHERE c.session_id = %s
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC, c.id DESC
                    LIMIT %s
                    """,
                    (session_uuid, limit),
                ).fetchall()
                return tuple(_conversation_record(row) for row in rows)

        return await self._run(operation)

    async def get_conversation(
        self, conversation_id: str, *, session_id: str
    ) -> tuple[ConversationRecord, tuple[ConversationTurn, ...]]:
        conversation_uuid = _uuid(conversation_id)
        session_uuid = _uuid(session_id)

        def operation() -> tuple[ConversationRecord, tuple[ConversationTurn, ...]]:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT c.id, c.session_id, c.title, c.created_at, c.updated_at,
                           count(t.id)::integer AS turn_count
                    FROM conversations c
                    LEFT JOIN conversation_turns t ON t.conversation_id = c.id
                    WHERE c.id = %s AND c.session_id = %s
                    GROUP BY c.id
                    """,
                    (conversation_uuid, session_uuid),
                ).fetchone()
                if row is None:
                    raise _not_found()
                turns = connection.execute(
                    """
                    SELECT id, request_id, user_message, assistant_message, route,
                           context_eligible, response_payload, created_at
                    FROM conversation_turns
                    WHERE conversation_id = %s
                    ORDER BY created_at, id
                    """,
                    (conversation_uuid,),
                ).fetchall()
                return _conversation_record(row), tuple(_conversation_turn(item) for item in turns)

        return await self._run(operation)

    async def rename_conversation(
        self, conversation_id: str, *, session_id: str, title: str
    ) -> ConversationRecord:
        conversation_uuid = _uuid(conversation_id)
        session_uuid = _uuid(session_id)
        clean_title = _clean_title(title)

        def operation() -> ConversationRecord:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    UPDATE conversations
                    SET title = %s, updated_at = now()
                    WHERE id = %s AND session_id = %s
                    RETURNING id, session_id, title, created_at, updated_at,
                           (SELECT count(*)::integer
                            FROM conversation_turns
                            WHERE conversation_id = conversations.id) AS turn_count
                    """,
                    (clean_title, conversation_uuid, session_uuid),
                ).fetchone()
                if row is None:
                    raise _not_found()
                return _conversation_record(row)

        return await self._run(operation)

    async def delete_conversation(self, conversation_id: str, *, session_id: str) -> None:
        conversation_uuid = _uuid(conversation_id)
        session_uuid = _uuid(session_id)

        def operation() -> None:
            with self._connect() as connection:
                row = connection.execute(
                    "DELETE FROM conversations WHERE id = %s AND session_id = %s RETURNING id",
                    (conversation_uuid, session_uuid),
                ).fetchone()
                if row is None:
                    raise _not_found()

        await self._run(operation)

    async def history(
        self, conversation_id: str, *, session_id: str | None = None
    ) -> tuple[ConversationTurn, ...]:
        if session_id is None:
            raise _session_required()
        conversation_uuid = _uuid(conversation_id)
        session_uuid = _uuid(session_id)

        def operation() -> tuple[ConversationTurn, ...]:
            with self._connect() as connection:
                owner = connection.execute(
                    "SELECT 1 FROM conversations WHERE id = %s AND session_id = %s",
                    (conversation_uuid, session_uuid),
                ).fetchone()
                if owner is None:
                    raise _not_found()
                rows = connection.execute(
                    """
                    SELECT id, request_id, user_message, assistant_message, route,
                           context_eligible, response_payload, created_at
                    FROM conversation_turns
                    WHERE conversation_id = %s AND context_eligible = true
                    ORDER BY created_at, id
                    """,
                    (conversation_uuid,),
                ).fetchall()
                return tuple(_conversation_turn(row) for row in rows)

        return await self._run(operation)

    async def append(
        self,
        conversation_id: str,
        turn: ConversationTurn,
        *,
        session_id: str | None = None,
    ) -> ConversationTurn:
        if session_id is None:
            raise _session_required()
        conversation_uuid = _uuid(conversation_id)
        session_uuid = _uuid(session_id)
        request_uuid = _uuid(turn.request_id, code="invalid_request_id")

        def operation() -> ConversationTurn:
            with self._connect() as connection:
                conversation = connection.execute(
                    "SELECT title FROM conversations WHERE id = %s AND session_id = %s FOR UPDATE",
                    (conversation_uuid, session_uuid),
                ).fetchone()
                if conversation is None:
                    raise _not_found()
                existing = connection.execute(
                    """
                    SELECT id, request_id, user_message, assistant_message, route,
                           context_eligible, response_payload, created_at, conversation_id
                    FROM conversation_turns WHERE request_id = %s
                    """,
                    (request_uuid,),
                ).fetchone()
                if existing is not None:
                    if existing["conversation_id"] != conversation_uuid:
                        raise ConversationStoreError(
                            code="request_id_conflict",
                            message="请求标识已被另一会话使用。",
                            status_code=409,
                        )
                    return _conversation_turn(existing)
                row = connection.execute(
                    """
                    INSERT INTO conversation_turns
                        (conversation_id, request_id, user_message, assistant_message, route,
                         context_eligible, response_payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, request_id, user_message, assistant_message, route,
                              context_eligible, response_payload, created_at
                    """,
                    (
                        conversation_uuid,
                        request_uuid,
                        turn.user_message,
                        turn.assistant_message,
                        turn.route,
                        turn.context_eligible,
                        Jsonb(turn.response_payload or {}),
                    ),
                ).fetchone()
                assert row is not None
                connection.execute(
                    """
                    UPDATE conversations
                    SET title = CASE
                            WHEN title = '新对话' AND
                                 (SELECT count(*)
                                  FROM conversation_turns
                                  WHERE conversation_id = %s) = 1
                            THEN %s ELSE title END,
                        updated_at = now()
                    WHERE id = %s
                    """,
                    (
                        conversation_uuid,
                        _first_message_title(turn.user_message),
                        conversation_uuid,
                    ),
                )
                connection.execute(
                    """
                    UPDATE anonymous_sessions
                    SET updated_at = now(), last_seen_at = now()
                    WHERE id = %s
                    """,
                    (session_uuid,),
                )
                return _conversation_turn(row)

        return await self._run(operation)

    async def clear(self, conversation_id: str, *, session_id: str | None = None) -> None:
        if session_id is None:
            raise _session_required()
        conversation_uuid = _uuid(conversation_id)
        session_uuid = _uuid(session_id)

        def operation() -> None:
            with self._connect() as connection:
                owner = connection.execute(
                    "SELECT 1 FROM conversations WHERE id = %s AND session_id = %s FOR UPDATE",
                    (conversation_uuid, session_uuid),
                ).fetchone()
                if owner is None:
                    raise _not_found()
                connection.execute(
                    """
                    UPDATE conversation_turns
                    SET context_eligible = false
                    WHERE conversation_id = %s
                    """,
                    (conversation_uuid,),
                )
                connection.execute(
                    "UPDATE conversations SET updated_at = now() WHERE id = %s",
                    (conversation_uuid,),
                )

        await self._run(operation)

    async def probe(self) -> bool:
        def operation() -> bool:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT to_regclass('public.conversation_turns') IS NOT NULL AS ready"
                ).fetchone()
                return bool(row and row["ready"])

        return await self._run(operation)

    def _connect(self):  # type: ignore[no-untyped-def]
        return connect(
            self.database_url,
            connect_timeout=self.connect_timeout_seconds,
            options=f"-c statement_timeout={self.statement_timeout_ms}",
            row_factory=dict_row,
        )

    async def _run(self, operation: Callable[[], T]) -> T:
        try:
            return await asyncio.to_thread(operation)
        except ConversationStoreError:
            raise
        except QueryCanceled as exc:
            raise ConversationStoreError(
                code="conversation_store_timeout",
                message="会话存储操作超时，请稍后重试。",
                status_code=503,
                retryable=True,
            ) from exc
        except OperationalError as exc:
            raise ConversationStoreError(
                code="conversation_store_unavailable",
                message="会话存储暂时不可用。",
                status_code=503,
                retryable=True,
            ) from exc
        except DatabaseError as exc:
            raise ConversationStoreError(
                code="conversation_store_failed",
                message="会话存储未能完成操作。",
                status_code=500,
                retryable=False,
            ) from exc
        except Exception as exc:
            raise ConversationStoreError(
                code="conversation_store_internal_error",
                message="会话存储发生未分类错误。",
                status_code=500,
                retryable=False,
            ) from exc


def build_conversation_store(
    *,
    mode: str,
    database_url: str | None,
    connect_timeout_seconds: int = 5,
    statement_timeout_ms: int = 5000,
) -> ConversationStore:
    if mode == "ephemeral":
        return EphemeralConversationStore()
    if not database_url:
        raise ConversationStoreError(
            code="conversation_store_not_configured",
            message="PostgreSQL 会话存储尚未配置。",
            status_code=503,
        )
    return PostgresConversationStore(
        database_url,
        connect_timeout_seconds=connect_timeout_seconds,
        statement_timeout_ms=statement_timeout_ms,
    )


def _conversation_record(row: dict[str, Any]) -> ConversationRecord:
    return ConversationRecord(
        conversation_id=str(row["id"]),
        session_id=str(row["session_id"]),
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        turn_count=int(row.get("turn_count", 0)),
    )


def _conversation_turn(row: dict[str, Any]) -> ConversationTurn:
    return ConversationTurn(
        turn_id=str(row["id"]),
        request_id=str(row["request_id"]),
        user_message=row["user_message"],
        assistant_message=row["assistant_message"],
        route=row["route"],
        context_eligible=bool(row.get("context_eligible", True)),
        response_payload=row.get("response_payload") or None,
        created_at=row["created_at"],
    )


def _uuid(value: str, *, code: str = "invalid_resource_id") -> UUID:
    try:
        return UUID(value)
    except (ValueError, TypeError) as exc:
        raise ConversationStoreError(
            code=code,
            message="资源标识格式无效。",
            status_code=422,
        ) from exc


def _clean_title(title: str) -> str:
    cleaned = " ".join(title.split())
    if not cleaned or len(cleaned) > 80:
        raise ConversationStoreError(
            code="invalid_conversation_title",
            message="对话标题长度必须为 1 到 80 个字符。",
            status_code=422,
        )
    return cleaned


def _first_message_title(message: str) -> str:
    cleaned = " ".join(message.split())
    return cleaned[:60] or "新对话"


def _not_found() -> ConversationStoreError:
    return ConversationStoreError(
        code="conversation_not_found",
        message="会话不存在或不属于当前匿名用户。",
        status_code=404,
    )


def _session_required() -> ConversationStoreError:
    return ConversationStoreError(
        code="session_required",
        message="持久化会话请求必须提供匿名会话标识。",
        status_code=422,
    )
