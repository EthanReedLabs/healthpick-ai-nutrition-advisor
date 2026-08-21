from __future__ import annotations

import httpx2
import pytest
from healthpick_api.config import Settings
from healthpick_api.providers import (
    LLMMessage,
    LLMRequest,
    MockLLMProvider,
    OpenAICompatibleLLMProvider,
    ProviderConfigurationError,
    ProviderProtocolError,
    ProviderRequestError,
    build_llm_provider,
)


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


@pytest.mark.anyio
async def test_real_provider_parses_openai_compatible_response() -> None:
    async def handler(incoming: httpx2.Request) -> httpx2.Response:
        assert incoming.url.path == "/v1/chat/completions"
        assert incoming.headers["x-request-id"] == "req-provider-test"
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
