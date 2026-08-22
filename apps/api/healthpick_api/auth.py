"""Account authentication and one-time anonymous-session ownership migration."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, TypeVar
from uuid import UUID, uuid4

from psycopg import DatabaseError, OperationalError, connect
from psycopg.rows import dict_row

from healthpick_api.chat import ConversationStore, ConversationStoreError
from healthpick_api.errors import AppError

T = TypeVar("T")
TOKEN_TTL = timedelta(days=30)
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


@dataclass(frozen=True, slots=True)
class UserRecord:
    user_id: str
    email: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: UserRecord
    access_token: str
    session_id: str
    expires_at: datetime


class AuthStore(Protocol):
    async def register(
        self, *, email: str, password: str, anonymous_session_id: str
    ) -> AuthResult: ...

    async def login(self, *, email: str, password: str) -> AuthResult: ...

    async def authenticate(self, access_token: str) -> UserRecord: ...

    async def logout(self, access_token: str) -> None: ...

    async def authorize_session(self, session_id: str, user_id: str | None) -> None: ...

    async def export_account(self, user_id: str) -> dict[str, Any]: ...

    async def delete_account(self, user_id: str, password: str) -> None: ...


class EphemeralAuthStore:
    """Process-local auth implementation used only by explicit test/development mode."""

    def __init__(self, conversations: ConversationStore) -> None:
        self.conversations = conversations
        self._users_by_email: dict[str, tuple[UserRecord, str]] = {}
        self._claims: dict[str, str] = {}
        self._tokens: dict[str, tuple[str, datetime]] = {}
        self._lock = asyncio.Lock()

    async def register(self, *, email: str, password: str, anonymous_session_id: str) -> AuthResult:
        await self._require_session(anonymous_session_id)
        normalized = _normalize_email(email)
        password_hash = _hash_password(password)
        async with self._lock:
            if normalized in self._users_by_email:
                raise _conflict("email_already_registered", "该邮箱已注册。")
            if anonymous_session_id in self._claims:
                raise _conflict("anonymous_session_claimed", "该匿名会话已绑定账号。")
            now = datetime.now(UTC)
            user = UserRecord(user_id=str(uuid4()), email=normalized, created_at=now)
            self._users_by_email[normalized] = (user, password_hash)
            self._claims[anonymous_session_id] = user.user_id
            return self._issue(user, anonymous_session_id)

    async def login(self, *, email: str, password: str) -> AuthResult:
        normalized = _normalize_email(email)
        async with self._lock:
            stored = self._users_by_email.get(normalized)
            if stored is None or not _verify_password(password, stored[1]):
                raise _invalid_credentials()
            user = stored[0]
            session_id = next(
                (key for key, owner in self._claims.items() if owner == user.user_id), None
            )
        if session_id is None:
            session = await self.conversations.create_session()
            session_id = session.session_id
            async with self._lock:
                self._claims[session_id] = user.user_id
                return self._issue(user, session_id)
        async with self._lock:
            return self._issue(user, session_id)

    async def authenticate(self, access_token: str) -> UserRecord:
        token_hash = _token_hash(access_token)
        async with self._lock:
            stored = self._tokens.get(token_hash)
            if stored is None or stored[1] <= datetime.now(UTC):
                raise _invalid_token()
            user_id = stored[0]
            for user, _ in self._users_by_email.values():
                if user.user_id == user_id:
                    return user
        raise _invalid_token()

    async def logout(self, access_token: str) -> None:
        token_hash = _token_hash(access_token)
        async with self._lock:
            if self._tokens.pop(token_hash, None) is None:
                raise _invalid_token()

    async def authorize_session(self, session_id: str, user_id: str | None) -> None:
        await self._require_session(session_id)
        async with self._lock:
            owner = self._claims.get(session_id)
        _check_owner(owner, user_id)

    async def export_account(self, user_id: str) -> dict[str, Any]:
        async with self._lock:
            stored = next(
                (entry for entry in self._users_by_email.values() if entry[0].user_id == user_id),
                None,
            )
            if stored is None:
                raise _invalid_token()
            user = stored[0]
            session_ids = sorted(
                session_id for session_id, owner in self._claims.items() if owner == user_id
            )
            active_tokens = sorted(
                (expires_at for owner, expires_at in self._tokens.values() if owner == user_id),
                key=lambda value: value.isoformat(),
            )

        sessions: list[dict[str, Any]] = []
        conversations: list[dict[str, Any]] = []
        turn_count = 0
        for session_id in session_ids:
            records = await self.conversations.list_conversations(session_id, limit=1000)
            sessions.append(
                {
                    "session_id": session_id,
                    "created_at": user.created_at,
                    "updated_at": user.created_at,
                    "last_seen_at": user.created_at,
                    "claimed_at": user.created_at,
                }
            )
            for record in reversed(records):
                _, turns = await self.conversations.get_conversation(
                    record.conversation_id, session_id=session_id
                )
                exported_turns = [
                    {
                        "turn_id": turn.turn_id,
                        "request_id": turn.request_id,
                        "user_message": turn.user_message,
                        "assistant_message": turn.assistant_message,
                        "route": turn.route,
                        "context_eligible": turn.context_eligible,
                        "response_payload": dict(turn.response_payload or {}),
                        "created_at": turn.created_at,
                    }
                    for turn in turns
                ]
                turn_count += len(exported_turns)
                conversations.append(
                    {
                        "conversation_id": record.conversation_id,
                        "session_id": record.session_id,
                        "title": record.title,
                        "created_at": record.created_at,
                        "updated_at": record.updated_at,
                        "turns": exported_turns,
                    }
                )

        inventory = _inventory(
            auth_sessions=len(active_tokens),
            anonymous_sessions=len(sessions),
            conversations=len(conversations),
            conversation_turns=turn_count,
        )
        return {
            "export_version": "1.0",
            "exported_at": datetime.now(UTC),
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "created_at": user.created_at,
                "updated_at": user.created_at,
            },
            "inventory": inventory,
            "auth_sessions": [
                {
                    "auth_session_id": f"ephemeral-session-{index}",
                    "created_at": user.created_at,
                    "expires_at": expires_at,
                    "revoked_at": None,
                }
                for index, expires_at in enumerate(active_tokens, start=1)
            ],
            "sessions": sessions,
            "conversations": conversations,
            "excluded_static_data": _excluded_static_data(),
        }

    async def delete_account(self, user_id: str, password: str) -> None:
        async with self._lock:
            entry = next(
                (
                    (email, stored)
                    for email, stored in self._users_by_email.items()
                    if stored[0].user_id == user_id
                ),
                None,
            )
            if entry is None or not _verify_password(password, entry[1][1]):
                raise _invalid_credentials()
            email = entry[0]
            session_ids = [
                session_id for session_id, owner in self._claims.items() if owner == user_id
            ]

        for session_id in session_ids:
            await self.conversations.delete_session(session_id)

        async with self._lock:
            self._users_by_email.pop(email, None)
            for session_id in session_ids:
                self._claims.pop(session_id, None)
            self._tokens = {
                token_hash: token
                for token_hash, token in self._tokens.items()
                if token[0] != user_id
            }

    async def _require_session(self, session_id: str) -> None:
        try:
            await self.conversations.list_conversations(session_id, limit=1)
        except ConversationStoreError as exc:
            if exc.status_code == 404:
                raise AppError(
                    status_code=404,
                    code="anonymous_session_not_found",
                    message="匿名会话不存在或已迁移。",
                ) from exc
            raise

    def _issue(self, user: UserRecord, session_id: str) -> AuthResult:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + TOKEN_TTL
        self._tokens[_token_hash(token)] = (user.user_id, expires_at)
        return AuthResult(
            user=user,
            access_token=token,
            session_id=session_id,
            expires_at=expires_at,
        )


class PostgresAuthStore:
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

    async def register(self, *, email: str, password: str, anonymous_session_id: str) -> AuthResult:
        normalized = _normalize_email(email)
        password_hash = _hash_password(password)
        session_uuid = _uuid(anonymous_session_id)
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + TOKEN_TTL

        def operation() -> AuthResult:
            with self._connect() as connection:
                session = connection.execute(
                    "SELECT user_id FROM anonymous_sessions WHERE id = %s FOR UPDATE",
                    (session_uuid,),
                ).fetchone()
                if session is None:
                    raise AppError(
                        status_code=404,
                        code="anonymous_session_not_found",
                        message="匿名会话不存在或已迁移。",
                    )
                if session["user_id"] is not None:
                    raise _conflict("anonymous_session_claimed", "该匿名会话已绑定账号。")
                row = connection.execute(
                    """
                    INSERT INTO users (email, password_hash)
                    VALUES (%s, %s)
                    ON CONFLICT (email) DO NOTHING
                    RETURNING id, email, created_at
                    """,
                    (normalized, password_hash),
                ).fetchone()
                if row is None:
                    raise _conflict("email_already_registered", "该邮箱已注册。")
                connection.execute(
                    "UPDATE anonymous_sessions SET user_id = %s, claimed_at = now() WHERE id = %s",
                    (row["id"], session_uuid),
                )
                connection.execute(
                    """
                    INSERT INTO auth_sessions (user_id, token_hash, expires_at)
                    VALUES (%s, %s, %s)
                    """,
                    (row["id"], _token_hash(token), expires_at),
                )
                return AuthResult(
                    user=_user_record(row),
                    access_token=token,
                    session_id=str(session_uuid),
                    expires_at=expires_at,
                )

        return await self._run(operation)

    async def login(self, *, email: str, password: str) -> AuthResult:
        normalized = _normalize_email(email)
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + TOKEN_TTL

        def operation() -> AuthResult:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT id, email, password_hash, created_at FROM users WHERE email = %s",
                    (normalized,),
                ).fetchone()
                if row is None or not _verify_password(password, row["password_hash"]):
                    raise _invalid_credentials()
                session = connection.execute(
                    """
                    SELECT id FROM anonymous_sessions
                    WHERE user_id = %s
                    ORDER BY claimed_at NULLS LAST, created_at, id
                    LIMIT 1
                    """,
                    (row["id"],),
                ).fetchone()
                if session is None:
                    session = connection.execute(
                        """
                        INSERT INTO anonymous_sessions (user_id, claimed_at)
                        VALUES (%s, now()) RETURNING id
                        """,
                        (row["id"],),
                    ).fetchone()
                assert session is not None
                connection.execute(
                    """
                    INSERT INTO auth_sessions (user_id, token_hash, expires_at)
                    VALUES (%s, %s, %s)
                    """,
                    (row["id"], _token_hash(token), expires_at),
                )
                return AuthResult(
                    user=_user_record(row),
                    access_token=token,
                    session_id=str(session["id"]),
                    expires_at=expires_at,
                )

        return await self._run(operation)

    async def authenticate(self, access_token: str) -> UserRecord:
        token_hash = _token_hash(access_token)

        def operation() -> UserRecord:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT u.id, u.email, u.created_at
                    FROM auth_sessions a
                    JOIN users u ON u.id = a.user_id
                    WHERE a.token_hash = %s AND a.revoked_at IS NULL AND a.expires_at > now()
                    """,
                    (token_hash,),
                ).fetchone()
                if row is None:
                    raise _invalid_token()
                return _user_record(row)

        return await self._run(operation)

    async def logout(self, access_token: str) -> None:
        token_hash = _token_hash(access_token)

        def operation() -> None:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    UPDATE auth_sessions SET revoked_at = now()
                    WHERE token_hash = %s AND revoked_at IS NULL RETURNING id
                    """,
                    (token_hash,),
                ).fetchone()
                if row is None:
                    raise _invalid_token()

        await self._run(operation)

    async def authorize_session(self, session_id: str, user_id: str | None) -> None:
        session_uuid = _uuid(session_id)

        def operation() -> None:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT user_id FROM anonymous_sessions WHERE id = %s", (session_uuid,)
                ).fetchone()
                if row is None:
                    raise AppError(
                        status_code=404,
                        code="anonymous_session_not_found",
                        message="匿名会话不存在。",
                    )
                _check_owner(str(row["user_id"]) if row["user_id"] else None, user_id)

        await self._run(operation)

    async def export_account(self, user_id: str) -> dict[str, Any]:
        user_uuid = _uuid(user_id)

        def operation() -> dict[str, Any]:
            with self._connect() as connection:
                user = connection.execute(
                    "SELECT id, email, created_at, updated_at FROM users WHERE id = %s",
                    (user_uuid,),
                ).fetchone()
                if user is None:
                    raise _invalid_token()
                auth_sessions = connection.execute(
                    """
                    SELECT id, created_at, expires_at, revoked_at
                    FROM auth_sessions WHERE user_id = %s ORDER BY created_at, id
                    """,
                    (user_uuid,),
                ).fetchall()
                sessions = connection.execute(
                    """
                    SELECT id, created_at, updated_at, last_seen_at, claimed_at
                    FROM anonymous_sessions WHERE user_id = %s ORDER BY created_at, id
                    """,
                    (user_uuid,),
                ).fetchall()
                conversation_rows = connection.execute(
                    """
                    SELECT c.id, c.session_id, c.title, c.created_at, c.updated_at
                    FROM conversations c
                    JOIN anonymous_sessions s ON s.id = c.session_id
                    WHERE s.user_id = %s ORDER BY c.created_at, c.id
                    """,
                    (user_uuid,),
                ).fetchall()
                turn_rows = connection.execute(
                    """
                    SELECT t.id, t.conversation_id, t.request_id, t.user_message,
                           t.assistant_message, t.route, t.context_eligible,
                           t.response_payload, t.created_at
                    FROM conversation_turns t
                    JOIN conversations c ON c.id = t.conversation_id
                    JOIN anonymous_sessions s ON s.id = c.session_id
                    WHERE s.user_id = %s ORDER BY t.created_at, t.id
                    """,
                    (user_uuid,),
                ).fetchall()

                turns_by_conversation: dict[str, list[dict[str, Any]]] = {}
                for turn in turn_rows:
                    turns_by_conversation.setdefault(str(turn["conversation_id"]), []).append(
                        {
                            "turn_id": str(turn["id"]),
                            "request_id": str(turn["request_id"]),
                            "user_message": turn["user_message"],
                            "assistant_message": turn["assistant_message"],
                            "route": turn["route"],
                            "context_eligible": turn["context_eligible"],
                            "response_payload": dict(turn["response_payload"] or {}),
                            "created_at": turn["created_at"],
                        }
                    )
                conversations = [
                    {
                        "conversation_id": str(row["id"]),
                        "session_id": str(row["session_id"]),
                        "title": row["title"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "turns": turns_by_conversation.get(str(row["id"]), []),
                    }
                    for row in conversation_rows
                ]
                return {
                    "export_version": "1.0",
                    "exported_at": datetime.now(UTC),
                    "user": {
                        "user_id": str(user["id"]),
                        "email": user["email"],
                        "created_at": user["created_at"],
                        "updated_at": user["updated_at"],
                    },
                    "inventory": _inventory(
                        auth_sessions=len(auth_sessions),
                        anonymous_sessions=len(sessions),
                        conversations=len(conversations),
                        conversation_turns=len(turn_rows),
                    ),
                    "auth_sessions": [
                        {
                            "auth_session_id": str(row["id"]),
                            "created_at": row["created_at"],
                            "expires_at": row["expires_at"],
                            "revoked_at": row["revoked_at"],
                        }
                        for row in auth_sessions
                    ],
                    "sessions": [
                        {
                            "session_id": str(row["id"]),
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                            "last_seen_at": row["last_seen_at"],
                            "claimed_at": row["claimed_at"],
                        }
                        for row in sessions
                    ],
                    "conversations": conversations,
                    "excluded_static_data": _excluded_static_data(),
                }

        return await self._run(operation)

    async def delete_account(self, user_id: str, password: str) -> None:
        user_uuid = _uuid(user_id)

        def operation() -> None:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT password_hash FROM users WHERE id = %s FOR UPDATE",
                    (user_uuid,),
                ).fetchone()
                if row is None or not _verify_password(password, row["password_hash"]):
                    raise _invalid_credentials()
                deleted = connection.execute(
                    "DELETE FROM users WHERE id = %s RETURNING id", (user_uuid,)
                ).fetchone()
                if deleted is None:
                    raise _invalid_token()

        await self._run(operation)

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
        except AppError:
            raise
        except OperationalError as exc:
            raise AppError(
                status_code=503,
                code="auth_store_unavailable",
                message="账号服务暂时不可用。",
                retryable=True,
            ) from exc
        except DatabaseError as exc:
            raise AppError(
                status_code=500,
                code="auth_store_failed",
                message="账号服务未能完成操作。",
            ) from exc


def build_auth_store(
    *,
    mode: str,
    database_url: str | None,
    conversations: ConversationStore,
    connect_timeout_seconds: int = 5,
    statement_timeout_ms: int = 5000,
) -> AuthStore:
    if mode == "ephemeral":
        return EphemeralAuthStore(conversations)
    if not database_url:
        raise AppError(
            status_code=503,
            code="auth_store_not_configured",
            message="账号存储尚未配置。",
        )
    return PostgresAuthStore(
        database_url,
        connect_timeout_seconds=connect_timeout_seconds,
        statement_timeout_ms=statement_timeout_ms,
    )


def bearer_token(authorization: str | None, *, required: bool) -> str | None:
    if authorization is None:
        if required:
            raise _invalid_token()
        return None
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise _invalid_token()
    return token.strip()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${derived.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, expected_hex = encoded.split("$", 5)
        if scheme != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(expected_hex)),
        )
        return hmac.compare_digest(actual, bytes.fromhex(expected_hex))
    except (TypeError, ValueError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError) as exc:
        raise AppError(
            status_code=422,
            code="invalid_resource_id",
            message="资源标识格式无效。",
        ) from exc


def _user_record(row: dict[str, object]) -> UserRecord:
    return UserRecord(
        user_id=str(row["id"]),
        email=str(row["email"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
    )


def _check_owner(owner: str | None, user_id: str | None) -> None:
    if owner is None:
        if user_id is not None:
            raise AppError(
                status_code=403,
                code="session_access_denied",
                message="该匿名会话尚未绑定当前账号。",
            )
        return
    if user_id is None:
        raise AppError(
            status_code=401,
            code="authentication_required",
            message="该会话已绑定账号，请先登录。",
        )
    if owner != user_id:
        raise AppError(
            status_code=403,
            code="session_access_denied",
            message="无权访问该会话。",
        )


def _invalid_credentials() -> AppError:
    return AppError(
        status_code=401,
        code="invalid_credentials",
        message="邮箱或密码不正确。",
    )


def _invalid_token() -> AppError:
    return AppError(
        status_code=401,
        code="invalid_access_token",
        message="登录状态无效或已过期。",
    )


def _conflict(code: str, message: str) -> AppError:
    return AppError(status_code=409, code=code, message=message)


def _inventory(
    *,
    auth_sessions: int,
    anonymous_sessions: int,
    conversations: int,
    conversation_turns: int,
) -> dict[str, int]:
    counts = {
        "users": 1,
        "auth_sessions": auth_sessions,
        "anonymous_sessions": anonymous_sessions,
        "conversations": conversations,
        "conversation_turns": conversation_turns,
    }
    return {**counts, "total_records": sum(counts.values())}


def _excluded_static_data() -> list[str]:
    return [
        "knowledge_documents",
        "knowledge_pages",
        "knowledge_chunks",
        "food_facts",
        "plan_rules",
        "platform_facts",
        "knowledge_ingestion_runs",
    ]
