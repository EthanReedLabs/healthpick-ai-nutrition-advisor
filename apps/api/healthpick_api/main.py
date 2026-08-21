"""FastAPI application factory and Phase 03 contract surface."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from healthpick_api.chat import (
    ChatPipeline,
    ChatPipelineError,
    build_chat_pipeline,
    stream_chat_events,
)
from healthpick_api.config import Settings, get_settings
from healthpick_api.errors import AppError
from healthpick_api.models import (
    ChatFinalEvent,
    ChatRequest,
    ComponentStatus,
    ErrorResponse,
    HealthResponse,
)
from healthpick_api.providers import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRequestError,
)

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


def create_app(
    settings: Settings | None = None,
    *,
    chat_pipeline: ChatPipeline | None = None,
) -> FastAPI:
    runtime = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        yield
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[runtime.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
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
                "database": ComponentStatus(status="not_checked"),
                "llm": llm_status,
                "embedding": embedding_status,
            },
        )

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
        },
        summary="Stream one evidence-grounded chat response",
        description=(
            "SSE event order: meta, zero or more citation events, token events, then final. "
            "Failures detected before streaming use the stable JSON ErrorResponse contract."
        ),
    )
    async def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
        try:
            pipeline = app.state.chat_pipeline
            if pipeline is None:
                pipeline = build_chat_pipeline(runtime)
                app.state.chat_pipeline = pipeline
            execution = await pipeline.run(payload, request_id=request_id_from(request))
        except ProviderConfigurationError as exc:
            raise AppError(
                status_code=503,
                code=exc.code,
                message="真实模型尚未完成配置。",
                retryable=False,
            ) from exc
        except ProviderRequestError as exc:
            raise AppError(
                status_code=503 if exc.retryable else 502,
                code=exc.code,
                message="模型服务暂时无法完成请求。",
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
