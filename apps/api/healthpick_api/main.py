"""FastAPI application factory and Phase 03 contract surface."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from healthpick_api.auth import AuthResult, AuthStore, bearer_token, build_auth_store
from healthpick_api.chat import (
    ChatPipeline,
    ChatPipelineError,
    ConversationRecord,
    ConversationStore,
    ConversationStoreError,
    ConversationTurn,
    build_chat_pipeline,
    build_conversation_store,
    stream_chat_events,
)
from healthpick_api.config import Settings, get_settings
from healthpick_api.errors import AppError
from healthpick_api.evaluation.public_summary import load_public_evaluation_summary
from healthpick_api.models import (
    AccountDataExport,
    AccountDeleteRequest,
    AnonymousSession,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    AuthUser,
    ChatFinalEvent,
    ChatRequest,
    ComponentStatus,
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationRename,
    ConversationSummary,
    ConversationTurnView,
    EmbeddingTransparency,
    ErrorResponse,
    EvaluationSummaryResponse,
    HealthResponse,
    ModelFailoverInfo,
    ModelInfo,
    ProfileAssessment,
    ProfilePatch,
    RecommendationEvaluation,
    SourceBoundaryInfo,
    TransparencyResponse,
)
from healthpick_api.profile import assess_profile
from healthpick_api.providers import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRequestError,
)
from healthpick_api.recommendation.service import RecommendationService

LOGGER = logging.getLogger("healthpick.api")


def request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
    details: list[dict[str, object]] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        request_id=request_id_from(request),
        code=code,
        message=message,
        retryable=retryable,
        details=details,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def _conversation_summary(record: ConversationRecord) -> ConversationSummary:
    return ConversationSummary(
        conversation_id=UUID(record.conversation_id),
        session_id=UUID(record.session_id),
        title=record.title,
        created_at=record.created_at,
        updated_at=record.updated_at,
        turn_count=record.turn_count,
    )


def _auth_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        user_id=UUID(result.user.user_id),
        email=result.user.email,
        created_at=result.user.created_at,
        access_token=result.access_token,
        expires_at=result.expires_at,
        session_id=UUID(result.session_id),
    )


def _conversation_detail(
    record: ConversationRecord, turns: tuple[ConversationTurn, ...]
) -> ConversationDetail:
    return ConversationDetail(
        **_conversation_summary(record).model_dump(),
        turns=[
            ConversationTurnView(
                turn_id=UUID(turn.turn_id or "00000000-0000-0000-0000-000000000000"),
                request_id=turn.request_id,
                user_message=turn.user_message,
                assistant_message=turn.assistant_message,
                route=turn.route,  # type: ignore[arg-type]
                created_at=turn.created_at or record.updated_at,
                response=(
                    ChatFinalEvent.model_validate(turn.response_payload).model_copy(
                        update={"turn_id": UUID(turn.turn_id)}
                    )
                    if turn.response_payload and turn.turn_id
                    else None
                ),
            )
            for turn in turns
        ],
    )


def create_app(
    settings: Settings | None = None,
    *,
    chat_pipeline: ChatPipeline | None = None,
    recommendation_service: RecommendationService | None = None,
) -> FastAPI:
    runtime = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        yield
        active_tasks = tuple(application.state.active_chat_tasks.values())
        for task in active_tasks:
            task.cancel()
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)
        pipeline = application.state.chat_pipeline
        if pipeline is not None:
            await pipeline.aclose()

    app = FastAPI(
        title="HealthPick AI Nutrition Advisor API",
        summary="Traceable nutrition Q&A with hard source isolation.",
        version=runtime.app_version,
        docs_url="/docs" if runtime.app_env != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
        responses={
            422: {"model": ErrorResponse, "description": "Request validation failed"},
            500: {"model": ErrorResponse, "description": "Unexpected server error"},
        },
    )
    app.state.settings = runtime
    app.state.chat_pipeline = chat_pipeline
    app.state.conversation_store = chat_pipeline.conversations if chat_pipeline else None
    app.state.auth_store = None
    app.state.recommendation_service = recommendation_service
    app.state.active_chat_tasks = {}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[runtime.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        supplied = request.headers.get("X-Request-ID", "")
        try:
            request_id = str(UUID(supplied)) if supplied else str(uuid4())
        except ValueError:
            request_id = str(uuid4())
        request.state.request_id = request_id

        if request.method in {"POST", "PUT", "PATCH"}:
            raw_content_length = request.headers.get("Content-Length")
            if raw_content_length is not None:
                try:
                    content_length = int(raw_content_length)
                except ValueError:
                    response = error_response(
                        request,
                        status_code=400,
                        code="invalid_content_length",
                        message="请求体长度标头无效。",
                    )
                    response.headers["X-Request-ID"] = request_id
                    return response
                if content_length > runtime.max_request_body_bytes:
                    response = error_response(
                        request,
                        status_code=413,
                        code="request_body_too_large",
                        message="请求体超过允许大小。",
                    )
                    response.headers["X-Request-ID"] = request_id
                    return response

            body = await request.body()
            if len(body) > runtime.max_request_body_bytes:
                response = error_response(
                    request,
                    status_code=413,
                    code="request_body_too_large",
                    message="请求体超过允许大小。",
                )
                response.headers["X-Request-ID"] = request_id
                return response

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "location": ".".join(str(part) for part in error["loc"]),
                "type": error["type"],
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return error_response(
            request,
            status_code=422,
            code="validation_error",
            message="请求内容不符合接口要求。",
            details=details,
        )

    @app.exception_handler(ConversationStoreError)
    async def handle_conversation_store_error(
        request: Request, exc: ConversationStoreError
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return error_response(
                request,
                status_code=404,
                code="not_found",
                message="请求的资源不存在。",
            )
        return error_response(
            request,
            status_code=exc.status_code,
            code="http_error",
            message="请求未能完成。",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        LOGGER.exception("Unhandled API error request_id=%s", request_id_from(request))
        return error_response(
            request,
            status_code=500,
            code="internal_error",
            message="服务暂时不可用，请稍后重试。",
            retryable=True,
        )

    @app.get("/healthz", response_model=HealthResponse, tags=["system"])
    async def healthz(request: Request) -> HealthResponse:
        llm_status = (
            ComponentStatus(status="mock", detail="development/test only")
            if runtime.llm_mode == "mock"
            else ComponentStatus(status="configured" if runtime.llm_api_key else "not_configured")
        )
        embedding_status = (
            ComponentStatus(status="disabled")
            if runtime.embedding_mode == "disabled"
            else ComponentStatus(
                status="configured"
                if runtime.embedding_api_key and runtime.embedding_dimensions
                else "not_configured"
            )
        )
        database_status = ComponentStatus(status="disabled", detail="ephemeral conversation mode")
        if runtime.resolved_conversation_store_mode == "postgres":
            try:
                database_ready = await conversation_store().probe()
                database_status = ComponentStatus(
                    status="configured" if database_ready else "not_configured",
                    detail="conversation schema ready" if database_ready else "migration required",
                )
            except ConversationStoreError:
                database_status = ComponentStatus(
                    status="not_configured", detail="database unavailable"
                )
        return HealthResponse(
            version=runtime.app_version,
            environment=runtime.app_env,
            request_id=request_id_from(request),
            modes={
                "llm": runtime.llm_mode,
                "embedding": runtime.embedding_mode,
                "retrieval": runtime.retrieval_mode,
            },
            dependencies={
                "database": database_status,
                "llm": llm_status,
                "embedding": embedding_status,
            },
        )

    @app.get(
        "/v1/transparency",
        response_model=TransparencyResponse,
        tags=["transparency"],
        summary="Disclose non-secret model, retrieval, persistence and source boundaries",
    )
    async def transparency() -> TransparencyResponse:
        llm_provider = "healthpick_mock" if runtime.llm_mode == "mock" else "openai_compatible"
        llm_name = runtime.llm_model or (
            "mock-v1" if runtime.llm_mode == "mock" else "not_configured"
        )
        embedding_provider = (
            "disabled" if runtime.embedding_mode == "disabled" else "openai_compatible"
        )
        embedding_name = runtime.embedding_model or (
            "disabled" if runtime.embedding_mode == "disabled" else "not_configured"
        )
        return TransparencyResponse(
            version=runtime.app_version,
            model=ModelInfo(
                provider=runtime.llm_provider if runtime.llm_mode == "real" else llm_provider,
                name=llm_name,
                mode=runtime.llm_mode,
            ),
            failover=ModelFailoverInfo(
                enabled=runtime.llm_fallback_enabled,
                fallback=(
                    ModelInfo(
                        provider=runtime.llm_fallback_provider,
                        name=runtime.llm_fallback_model or "not_configured",
                        mode="real",
                    )
                    if runtime.llm_fallback_enabled
                    else None
                ),
            ),
            embedding=EmbeddingTransparency(
                provider=embedding_provider,
                name=embedding_name,
                mode=runtime.embedding_mode,
                dimensions=runtime.embedding_dimensions,
            ),
            retrieval_mode=runtime.retrieval_mode,
            conversation_store=runtime.resolved_conversation_store_mode,
            evidence_policy="仅返回通过来源边界、逐条引用和输出安全校验的完整回答。",
            sources=[
                SourceBoundaryInfo(
                    source="A",
                    title="2026秋季健康膳食指南",
                    allowed_use="营养事实、风险与禁忌依据",
                    forbidden_use="不得用于解释平台会员、价格或服务承诺",
                ),
                SourceBoundaryInfo(
                    source="B",
                    title="2026秋季个性化饮食方案",
                    allowed_use="食谱、搭配、目标与同类替换依据",
                    forbidden_use="不得用于解释平台会员、价格或服务承诺",
                ),
                SourceBoundaryInfo(
                    source="C",
                    title="HealthPick平台服务白皮书",
                    allowed_use="平台功能、会员、合作与服务规则",
                    forbidden_use="不得作为营养事实或医疗安全依据",
                ),
            ],
        )

    @app.get(
        "/v1/evaluation/summary",
        response_model=EvaluationSummaryResponse,
        tags=["evaluation"],
        summary="Return the packaged, sanitized release evaluation summary",
    )
    async def evaluation_summary() -> EvaluationSummaryResponse:
        return load_public_evaluation_summary()

    def conversation_store() -> ConversationStore:
        store = app.state.conversation_store
        if store is None:
            store = build_conversation_store(
                mode=runtime.resolved_conversation_store_mode,
                database_url=(
                    runtime.database_url.get_secret_value() if runtime.database_url else None
                ),
                connect_timeout_seconds=runtime.database_connect_timeout_seconds,
                statement_timeout_ms=runtime.database_statement_timeout_ms,
            )
            app.state.conversation_store = store
        return store

    def auth_store() -> AuthStore:
        store = app.state.auth_store
        if store is None:
            store = build_auth_store(
                mode=runtime.resolved_conversation_store_mode,
                database_url=(
                    runtime.database_url.get_secret_value() if runtime.database_url else None
                ),
                conversations=conversation_store(),
                connect_timeout_seconds=runtime.database_connect_timeout_seconds,
                statement_timeout_ms=runtime.database_statement_timeout_ms,
            )
            app.state.auth_store = store
        return store

    async def authenticated_user(request: Request, *, required: bool) -> AuthUser | None:
        token = bearer_token(request.headers.get("Authorization"), required=required)
        if token is None:
            return None
        user = await auth_store().authenticate(token)
        return AuthUser(user_id=UUID(user.user_id), email=user.email, created_at=user.created_at)

    async def authorize_session(request: Request, session_id: str) -> None:
        user = await authenticated_user(request, required=False)
        await auth_store().authorize_session(
            session_id, str(user.user_id) if user is not None else None
        )

    @app.post(
        "/v1/auth/register",
        response_model=AuthResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["auth"],
        summary="Register and atomically claim one anonymous session",
    )
    async def register_account(payload: AuthRegisterRequest) -> AuthResponse:
        result = await auth_store().register(
            email=payload.email,
            password=payload.password,
            anonymous_session_id=str(payload.anonymous_session_id),
        )
        return _auth_response(result)

    @app.post(
        "/v1/auth/login",
        response_model=AuthResponse,
        tags=["auth"],
        summary="Log in and return the canonical server session ID",
    )
    async def login_account(payload: AuthLoginRequest) -> AuthResponse:
        return _auth_response(
            await auth_store().login(email=payload.email, password=payload.password)
        )

    @app.get("/v1/auth/me", response_model=AuthUser, tags=["auth"])
    async def current_account(request: Request) -> AuthUser:
        user = await authenticated_user(request, required=True)
        assert user is not None
        return user

    @app.post("/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
    async def logout_account(request: Request) -> Response:
        token = bearer_token(request.headers.get("Authorization"), required=True)
        assert token is not None
        await auth_store().logout(token)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get(
        "/v1/account/export",
        response_model=AccountDataExport,
        tags=["account"],
        summary="Export the authenticated user's personal data",
    )
    async def export_account_data(request: Request) -> AccountDataExport:
        user = await authenticated_user(request, required=True)
        assert user is not None
        return AccountDataExport.model_validate(
            await auth_store().export_account(str(user.user_id))
        )

    @app.delete(
        "/v1/account",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["account"],
        summary="Permanently delete the authenticated account and personal data",
    )
    async def delete_account(payload: AccountDeleteRequest, request: Request) -> Response:
        user = await authenticated_user(request, required=True)
        assert user is not None
        await auth_store().delete_account(str(user.user_id), payload.password)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post(
        "/v1/sessions/anonymous",
        response_model=AnonymousSession,
        status_code=status.HTTP_201_CREATED,
        tags=["conversations"],
        summary="Create a server-owned anonymous session",
    )
    async def create_anonymous_session() -> AnonymousSession:
        record = await conversation_store().create_session()
        return AnonymousSession(session_id=UUID(record.session_id), created_at=record.created_at)

    @app.post(
        "/v1/conversations",
        response_model=ConversationSummary,
        status_code=status.HTTP_201_CREATED,
        tags=["conversations"],
        summary="Create a canonical conversation",
    )
    async def create_conversation(
        payload: ConversationCreate, request: Request
    ) -> ConversationSummary:
        await authorize_session(request, str(payload.session_id))
        record = await conversation_store().create_conversation(
            str(payload.session_id), title=payload.title
        )
        return _conversation_summary(record)

    @app.get(
        "/v1/conversations",
        response_model=ConversationList,
        tags=["conversations"],
        summary="List conversations owned by an anonymous session",
    )
    async def list_conversations(
        request: Request, session_id: UUID, limit: int = Query(default=50, ge=1, le=100)
    ) -> ConversationList:
        await authorize_session(request, str(session_id))
        records = await conversation_store().list_conversations(str(session_id), limit=limit)
        return ConversationList(items=[_conversation_summary(record) for record in records])

    @app.get(
        "/v1/conversations/{conversation_id}",
        response_model=ConversationDetail,
        tags=["conversations"],
        summary="Read one conversation and its persisted turns",
    )
    async def get_conversation(
        conversation_id: UUID, session_id: UUID, request: Request
    ) -> ConversationDetail:
        await authorize_session(request, str(session_id))
        record, turns = await conversation_store().get_conversation(
            str(conversation_id), session_id=str(session_id)
        )
        return _conversation_detail(record, turns)

    @app.patch(
        "/v1/conversations/{conversation_id}",
        response_model=ConversationSummary,
        tags=["conversations"],
        summary="Rename one owned conversation",
    )
    async def rename_conversation(
        conversation_id: UUID, payload: ConversationRename, request: Request
    ) -> ConversationSummary:
        await authorize_session(request, str(payload.session_id))
        record = await conversation_store().rename_conversation(
            str(conversation_id),
            session_id=str(payload.session_id),
            title=payload.title,
        )
        return _conversation_summary(record)

    @app.delete(
        "/v1/conversations/{conversation_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["conversations"],
        summary="Delete one owned conversation and all turns",
    )
    async def delete_conversation(
        conversation_id: UUID, session_id: UUID, request: Request
    ) -> Response:
        await authorize_session(request, str(session_id))
        await conversation_store().delete_conversation(
            str(conversation_id), session_id=str(session_id)
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post(
        "/v1/profile/assess",
        response_model=ProfileAssessment,
        tags=["profile"],
        summary="Validate and preview an ephemeral health profile",
        description=(
            "Normalizes a minimal structured profile and returns a BMI system estimate only "
            "when both height and weight are present. This endpoint does not persist data."
        ),
    )
    async def profile_assessment(profile: ProfilePatch) -> ProfileAssessment:
        return assess_profile(profile)

    @app.post(
        "/v1/recommendations/evaluate",
        response_model=RecommendationEvaluation,
        tags=["recommendations"],
        summary="Evaluate a deterministic recommendation candidate",
        description=(
            "Selects candidates from verified A/B plan rules only. Unreviewed or unknown-glyph "
            "facts return an explicit blocked result and never enter the candidate pool."
        ),
    )
    async def recommendation_evaluation(profile: ProfilePatch) -> RecommendationEvaluation:
        service = app.state.recommendation_service
        if service is None:
            service = RecommendationService.load_default()
            app.state.recommendation_service = service
        return service.evaluate(profile)

    @app.post(
        "/v1/chat/cancel/{request_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["chat"],
        summary="Idempotently cancel one active generation request",
    )
    async def cancel_chat_generation(request_id: UUID) -> Response:
        task = app.state.active_chat_tasks.get(str(request_id))
        if task is not None and not task.done():
            task.cancel()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post(
        "/v1/chat/stream",
        response_model=ChatFinalEvent,
        response_class=StreamingResponse,
        tags=["chat"],
        responses={
            200: {
                "description": "Ordered SSE stream ending with a ChatFinalEvent payload",
                "content": {
                    "text/event-stream": {
                        "schema": {
                            "type": "string",
                            "description": "meta, citation, token and final SSE events",
                        }
                    }
                },
            },
            502: {"model": ErrorResponse, "description": "Provider or evidence failure"},
            503: {"model": ErrorResponse, "description": "Provider not configured or unavailable"},
            504: {"model": ErrorResponse, "description": "Provider request timed out"},
        },
        summary="Stream one evidence-grounded chat response",
        description=(
            "SSE event order: meta, zero or more citation events, token events, then final. "
            "Failures detected before streaming use the stable JSON ErrorResponse contract."
        ),
    )
    async def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
        pipeline_task = None
        request_id = request_id_from(request)
        try:
            if payload.session_id is not None:
                await authorize_session(request, payload.session_id)
            pipeline = app.state.chat_pipeline
            if pipeline is None:
                pipeline = build_chat_pipeline(runtime, conversations=conversation_store())
                app.state.chat_pipeline = pipeline
            existing_task = app.state.active_chat_tasks.get(request_id)
            if existing_task is not None and not existing_task.done():
                raise AppError(
                    status_code=409,
                    code="request_already_running",
                    message="同一请求编号仍在处理中。",
                    retryable=False,
                )
            pipeline_task = asyncio.create_task(
                pipeline.run(payload, request_id=request_id),
                name=f"chat:{request_id}",
            )
            app.state.active_chat_tasks[request_id] = pipeline_task
            execution = await pipeline_task
        except asyncio.CancelledError as exc:
            raise AppError(
                status_code=409,
                code="generation_cancelled",
                message="本次生成已由用户停止，未保存半成品。",
                retryable=True,
            ) from exc
        except ProviderConfigurationError as exc:
            raise AppError(
                status_code=503,
                code=exc.code,
                message="真实模型尚未完成配置。",
                retryable=False,
            ) from exc
        except ProviderRequestError as exc:
            provider_error_contract = {
                "provider_timeout": (504, "模型服务响应超时，请稍后重试。"),
                "provider_connection_failed": (503, "暂时无法连接模型服务。"),
                "provider_rate_limited": (503, "模型服务当前请求过多，请稍后重试。"),
                "provider_upstream_unavailable": (503, "模型服务暂时不可用。"),
                "provider_rejected_request": (502, "模型服务拒绝了本次请求。"),
            }
            status_code, message = provider_error_contract.get(
                exc.code,
                (
                    503 if exc.retryable else 502,
                    "模型服务暂时无法完成请求。",
                ),
            )
            raise AppError(
                status_code=status_code,
                code=exc.code,
                message=message,
                retryable=exc.retryable,
            ) from exc
        except ProviderError as exc:
            raise AppError(
                status_code=502,
                code=exc.code,
                message="模型响应未通过协议校验。",
                retryable=False,
            ) from exc
        except ChatPipelineError as exc:
            raise AppError(
                status_code=exc.status_code,
                code=exc.code,
                message=exc.message,
                retryable=exc.status_code >= 500,
            ) from exc
        finally:
            if (
                pipeline_task is not None
                and app.state.active_chat_tasks.get(request_id) is pipeline_task
            ):
                app.state.active_chat_tasks.pop(request_id, None)

        return StreamingResponse(
            stream_chat_events(execution),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    return app


app = create_app()
