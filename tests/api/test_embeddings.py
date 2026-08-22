from __future__ import annotations

import json

import httpx2
import pytest
from healthpick_api.config import Settings
from healthpick_api.embeddings import (
    EmbeddingRequest,
    OpenAICompatibleEmbeddingProvider,
    build_embedding_provider,
)
from healthpick_api.providers import (
    ProviderConfigurationError,
    ProviderProtocolError,
    ProviderRequestError,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_factory_rejects_disabled_or_incomplete_embedding_configuration() -> None:
    with pytest.raises(ProviderConfigurationError, match="disabled"):
        build_embedding_provider(Settings(embedding_mode="disabled", _env_file=None))

    with pytest.raises(ProviderConfigurationError, match="EMBEDDING_BASE_URL"):
        build_embedding_provider(
            Settings(
                embedding_mode="real",
                embedding_base_url=None,
                embedding_api_key=None,
                embedding_model=None,
                embedding_dimensions=None,
                _env_file=None,
            )
        )


@pytest.mark.anyio
async def test_embedding_provider_parses_and_orders_vectors() -> None:
    async def handler(incoming: httpx2.Request) -> httpx2.Response:
        assert incoming.url.path == "/v1/embeddings"
        assert incoming.headers["x-request-id"] == "embed-test"
        assert json.loads(incoming.content)["dimensions"] == 3
        return httpx2.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0, 1, 0]},
                    {"index": 0, "embedding": [1, 0, 0]},
                ],
                "usage": {"prompt_tokens": 8},
            },
        )

    client = httpx2.AsyncClient(
        base_url="https://provider.example/v1",
        transport=httpx2.MockTransport(handler),
    )
    provider = OpenAICompatibleEmbeddingProvider(
        provider_name="test",
        base_url="https://ignored.example/v1",
        api_key="not-logged",
        model_name="embed-test",
        dimensions=3,
        timeout_seconds=3,
        client=client,
    )
    result = await provider.embed(EmbeddingRequest(inputs=("一", "二"), request_id="embed-test"))

    assert result.vectors == ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    assert result.prompt_tokens == 8
    await client.aclose()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        {"data": []},
        {"data": [{"index": 0, "embedding": [1, 2]}]},
        {"data": [{"index": 0, "embedding": [1, True, 3]}]},
        "nonfinite",
    ],
)
async def test_embedding_provider_rejects_invalid_payload(payload: object) -> None:
    async def handler(_: httpx2.Request) -> httpx2.Response:
        if payload == "nonfinite":
            return httpx2.Response(
                200,
                content=b'{"data":[{"index":0,"embedding":[1,Infinity,3]}]}',
                headers={"Content-Type": "application/json"},
            )
        return httpx2.Response(200, json=payload)

    client = httpx2.AsyncClient(
        base_url="https://provider.example/v1",
        transport=httpx2.MockTransport(handler),
    )
    provider = OpenAICompatibleEmbeddingProvider(
        provider_name="test",
        base_url="https://ignored.example/v1",
        api_key="not-logged",
        model_name="embed-test",
        dimensions=3,
        timeout_seconds=3,
        client=client,
    )
    with pytest.raises(ProviderProtocolError):
        await provider.embed(EmbeddingRequest(inputs=("一",)))
    await client.aclose()


@pytest.mark.anyio
async def test_embedding_provider_normalizes_http_error() -> None:
    async def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(429, json={"error": "private detail"})

    client = httpx2.AsyncClient(
        base_url="https://provider.example/v1",
        transport=httpx2.MockTransport(handler),
    )
    provider = OpenAICompatibleEmbeddingProvider(
        provider_name="test",
        base_url="https://ignored.example/v1",
        api_key="not-logged",
        model_name="embed-test",
        dimensions=3,
        timeout_seconds=3,
        client=client,
    )
    with pytest.raises(ProviderRequestError) as caught:
        await provider.embed(EmbeddingRequest(inputs=("一",)))
    assert caught.value.status_code == 429
    assert caught.value.code == "embedding_rate_limited"
    assert "private detail" not in str(caught.value)
    await client.aclose()
