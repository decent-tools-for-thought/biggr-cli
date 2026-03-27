from __future__ import annotations

import httpx
import pytest

from biggr_cli.client import BiggrClient
from biggr_cli.errors import ApiError, ApiRateLimitError, ApiResponseError


def _transport(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(base_url="https://example.test/api/v3", timeout=5, transport=handler)


def test_get_object_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/objects")
        return httpx.Response(200, json={"id": "iML1515", "object": {"_type": "Model"}})

    with _transport(httpx.MockTransport(handler)) as http_client:
        client = BiggrClient("https://example.test/api/v3", 5, http_client=http_client)
        result = client.get_object("model", "iML1515")
        assert result["object"]["_type"] == "Model"


def test_rate_limit_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "3"}, text="Too many requests")

    with _transport(httpx.MockTransport(handler)) as http_client:
        client = BiggrClient("https://example.test/api/v3", 5, http_client=http_client)
        with pytest.raises(ApiRateLimitError):
            client.list_table("/models")


def test_invalid_json_response() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    with _transport(httpx.MockTransport(handler)) as http_client:
        client = BiggrClient("https://example.test/api/v3", 5, http_client=http_client)
        with pytest.raises(ApiResponseError):
            client.list_table("/models")


def test_http_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with _transport(httpx.MockTransport(handler)) as http_client:
        client = BiggrClient("https://example.test/api/v3", 5, http_client=http_client)
        with pytest.raises(ApiError):
            client.list_table("/models")
