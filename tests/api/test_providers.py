from __future__ import annotations

import json

import httpx2
import pytest
from healthpick_api.config import Settings
from healthpick_api.providers import (
    FailoverLLMProvider,
    LLMMessage,
    LLMRequest,
    MockLLMProvider,
    OpenAICompatibleLLMProvider,
    ProviderConfigurationError,
    ProviderProtocolError,
    ProviderRequestError,
    build_llm_provider,
)
from healthpick_api.providers.base import LLMResult, ProviderError


def request() -> LLMRequest:
    return LLMRequest(
        messages=(LLMMessage(role="user", content="低钠饮食是什么？"),),
        request_id="req-provider-test",
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_mock_provider_is_unmistakably_disclosed() -> None:
    provider = MockLLMProvider()
    result = await provider.generate(request())

    assert result.mode == "mock"
    assert result.provider == "healthpick_mock"
    assert result.content.startswith("[MOCK RESPONSE — NOT REAL MODEL OUTPUT]")
    assert result.metadata == {"disclosure": "mock_only"}


def test_factory_builds_mock_only_when_explicit() -> None:
    provider = build_llm_provider(Settings(llm_mode="mock", _env_file=None))
    assert isinstance(provider, MockLLMProvider)


class StubProvider:
    mode = "real"

    def __init__(
        self,
        name: str,
        *,
        result: LLMResult | None = None,
        error: ProviderError | None = None,
    ) -> None:
        self.provider_name = name
        self.model_name = f"{name}-model"
        self.result = result
        self.error = error
        self.calls = 0
        self.closed = False

    async def generate(self, _: LLMRequest) -> LLMResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result

    async def aclose(self) -> None:
        self.closed = True


def stub_result(provider: str) -> LLMResult:
    return LLMResult(
        content="provider result",
        provider=provider,
        model=f"{provider}-model",
        mode="real",
        latency_ms=1,
    )


@pytest.mark.anyio
async def test_failover_uses_backup_only_for_retryable_primary_failure() -> None:
    primary = StubProvider(
        "primary",
        error=ProviderRequestError("timeout", retryable=True, code="provider_timeout"),
    )
    backup = StubProvider("backup", result=stub_result("backup"))
    provider = FailoverLLMProvider(primary, backup)  # type: ignore[arg-type]

    result = await provider.generate(request())

    assert primary.calls == 1
    assert backup.calls == 1
    assert result.provider == "backup"
    assert result.metadata == {
        "failover": "used",
        "primary_provider": "primary",
        "primary_model": "primary-model",
        "primary_error_code": "provider_timeout",
    }
    await provider.aclose()
    assert primary.closed is True
    assert backup.closed is True


@pytest.mark.anyio
async def test_failover_does_not_retry_non_retryable_rejection() -> None:
    primary_error = ProviderRequestError(
        "bad request", retryable=False, code="provider_rejected_request"
    )
    primary = StubProvider("primary", error=primary_error)
    backup = StubProvider("backup", result=stub_result("backup"))
    provider = FailoverLLMProvider(primary, backup)  # type: ignore[arg-type]

    with pytest.raises(ProviderRequestError) as caught:
        await provider.generate(request())

    assert caught.value is primary_error
    assert backup.calls == 0


@pytest.mark.anyio
async def test_failover_normalizes_dual_failure() -> None:
    primary = StubProvider(
        "primary",
        error=ProviderRequestError("timeout", retryable=True, code="provider_timeout"),
    )
    backup = StubProvider(
        "backup",
        error=ProviderRequestError(
            "unavailable", retryable=True, code="provider_upstream_unavailable"
        ),
    )
    provider = FailoverLLMProvider(primary, backup)  # type: ignore[arg-type]

    with pytest.raises(ProviderRequestError) as caught:
        await provider.generate(request())

    assert caught.value.code == "provider_failover_exhausted"
    assert caught.value.retryable is True
    assert "unavailable" not in str(caught.value)


def test_factory_builds_explicit_real_failover() -> None:
    provider = build_llm_provider(
        Settings(
            llm_mode="real",
            llm_base_url="https://primary.example/v1",
            llm_api_key="primary-secret",
            llm_model="primary-model",
            llm_fallback_enabled=True,
            llm_fallback_base_url="https://backup.example/v1",
            llm_fallback_api_key="backup-secret",
            llm_fallback_model="backup-model",
            _env_file=None,
        )
    )
    assert isinstance(provider, FailoverLLMProvider)


def test_settings_reject_empty_enabled_fallback_key() -> None:
    with pytest.raises(ValueError, match="LLM_FALLBACK_API_KEY"):
        Settings(
            llm_mode="real",
            llm_base_url="https://primary.example/v1",
            llm_api_key="primary-secret",
            llm_model="primary-model",
            llm_fallback_enabled=True,
            llm_fallback_base_url="https://backup.example/v1",
            llm_fallback_api_key="",
            llm_fallback_model="backup-model",
            _env_file=None,
        )


def test_factory_rejects_incomplete_real_configuration() -> None:
    with pytest.raises(ProviderConfigurationError) as caught:
        build_llm_provider(
            Settings(
                llm_mode="real",
                llm_base_url=None,
                llm_api_key=None,
                llm_model=None,
                _env_file=None,
            )
        )
    assert "LLM_BASE_URL" in str(caught.value)
    assert "LLM_API_KEY" in str(caught.value)
    assert "LLM_MODEL" in str(caught.value)


def test_factory_rejects_empty_primary_key() -> None:
    with pytest.raises(ProviderConfigurationError, match="LLM_API_KEY"):
        build_llm_provider(
            Settings(
                llm_mode="real",
                llm_base_url="https://primary.example/v1",
                llm_api_key="",
                llm_model="primary-model",
                _env_file=None,
            )
        )


@pytest.mark.anyio
async def test_real_provider_parses_openai_compatible_response() -> None:
    async def handler(incoming: httpx2.Request) -> httpx2.Response:
        assert incoming.url.path == "/v1/chat/completions"
        assert incoming.headers["x-request-id"] == "req-provider-test"
        assert "reasoning_effort" not in json.loads(incoming.content)
        return httpx2.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": "  基于证据的回答。  "},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7},
            },
        )

    client = httpx2.AsyncClient(
        base_url="https://provider.example/v1",
        transport=httpx2.MockTransport(handler),
    )
    provider = OpenAICompatibleLLMProvider(
        provider_name="test-provider",
        base_url="https://ignored.example/v1",
        api_key="secret-not-logged",
        model_name="test-model",
        timeout_seconds=3,
        client=client,
    )
    result = await provider.generate(request())

    assert result.content == "基于证据的回答。"
    assert result.mode == "real"
    assert result.prompt_tokens == 11
    assert result.completion_tokens == 7
    assert result.finish_reason == "stop"
    await client.aclose()


@pytest.mark.anyio
async def test_real_provider_forwards_optional_reasoning_effort() -> None:
    async def handler(incoming: httpx2.Request) -> httpx2.Response:
        assert json.loads(incoming.content)["reasoning_effort"] == "none"
        return httpx2.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]},
        )

    client = httpx2.AsyncClient(
        base_url="https://provider.example/v1",
        transport=httpx2.MockTransport(handler),
    )
    provider = OpenAICompatibleLLMProvider(
        provider_name="test-provider",
        base_url="https://ignored.example/v1",
        api_key="secret-not-logged",
        model_name="test-model",
        timeout_seconds=3,
        client=client,
    )
    result = await provider.generate(
        LLMRequest(
            messages=(LLMMessage(role="user", content="test"),),
            reasoning_effort="none",
        )
    )
    assert result.content == "ok"
    await client.aclose()


@pytest.mark.anyio
async def test_real_provider_marks_429_retryable_without_leaking_body() -> None:
    async def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(429, json={"error": "secret provider detail"})

    client = httpx2.AsyncClient(
        base_url="https://provider.example/v1",
        transport=httpx2.MockTransport(handler),
    )
    provider = OpenAICompatibleLLMProvider(
        provider_name="test-provider",
        base_url="https://ignored.example/v1",
        api_key="secret-not-logged",
        model_name="test-model",
        timeout_seconds=3,
        client=client,
    )
    with pytest.raises(ProviderRequestError) as caught:
        await provider.generate(request())

    assert caught.value.status_code == 429
    assert caught.value.retryable is True
    assert caught.value.code == "provider_rate_limited"
    assert "secret provider detail" not in str(caught.value)
    await client.aclose()


@pytest.mark.anyio
async def test_real_provider_marks_400_non_retryable() -> None:
    async def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(400, json={"error": "bad input"})

    client = httpx2.AsyncClient(
        base_url="https://provider.example/v1",
        transport=httpx2.MockTransport(handler),
    )
    provider = OpenAICompatibleLLMProvider(
        provider_name="test-provider",
        base_url="https://ignored.example/v1",
        api_key="secret-not-logged",
        model_name="test-model",
        timeout_seconds=3,
        client=client,
    )
    with pytest.raises(ProviderRequestError) as caught:
        await provider.generate(request())
    assert caught.value.retryable is False
    assert caught.value.code == "provider_rejected_request"
    await client.aclose()


@pytest.mark.anyio
async def test_real_provider_normalizes_timeout() -> None:
    async def handler(incoming: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("timed out", request=incoming)

    client = httpx2.AsyncClient(
        base_url="https://provider.example/v1",
        transport=httpx2.MockTransport(handler),
    )
    provider = OpenAICompatibleLLMProvider(
        provider_name="test-provider",
        base_url="https://ignored.example/v1",
        api_key="secret-not-logged",
        model_name="test-model",
        timeout_seconds=3,
        client=client,
    )
    with pytest.raises(ProviderRequestError) as caught:
        await provider.generate(request())
    assert caught.value.retryable is True
    assert caught.value.status_code is None
    assert caught.value.code == "provider_timeout"
    await client.aclose()


@pytest.mark.anyio
async def test_real_provider_distinguishes_connection_failure() -> None:
    async def handler(incoming: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused", request=incoming)

    client = httpx2.AsyncClient(
        base_url="https://provider.example/v1",
        transport=httpx2.MockTransport(handler),
    )
    provider = OpenAICompatibleLLMProvider(
        provider_name="test-provider",
        base_url="https://ignored.example/v1",
        api_key="secret-not-logged",
        model_name="test-model",
        timeout_seconds=3,
        client=client,
    )
    with pytest.raises(ProviderRequestError) as caught:
        await provider.generate(request())
    assert caught.value.code == "provider_connection_failed"
    assert caught.value.retryable is True
    await client.aclose()


@pytest.mark.anyio
async def test_real_provider_rejects_invalid_success_payload() -> None:
    async def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"choices": []})

    client = httpx2.AsyncClient(
        base_url="https://provider.example/v1",
        transport=httpx2.MockTransport(handler),
    )
    provider = OpenAICompatibleLLMProvider(
        provider_name="test-provider",
        base_url="https://ignored.example/v1",
        api_key="secret-not-logged",
        model_name="test-model",
        timeout_seconds=3,
        client=client,
    )
    with pytest.raises(ProviderProtocolError):
        await provider.generate(request())
    await client.aclose()
