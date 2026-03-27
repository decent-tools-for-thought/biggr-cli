"""HTTP client for BiGGr v3 API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .errors import ApiAuthError, ApiError, ApiRateLimitError, ApiResponseError


class BiggrClient:
    """Thin API transport wrapper around httpx."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(base_url=base_url, timeout=timeout_seconds)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> BiggrClient:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.close()

    def list_table(self, endpoint: str, params: Mapping[str, str] | None = None) -> dict[str, Any]:
        """Fetch a table endpoint via GET."""
        data = self._request_json("GET", endpoint, params=params)
        if not isinstance(data, dict):
            raise ApiResponseError("Expected table endpoint to return a JSON object.")
        return data

    def post_table(self, endpoint: str, form_data: Mapping[str, str]) -> dict[str, Any]:
        """Fetch a table endpoint via datatables-compatible POST form data."""
        data = self._request_json("POST", endpoint, data=dict(form_data))
        if not isinstance(data, dict):
            raise ApiResponseError("Expected table endpoint to return a JSON object.")
        return data

    def get_object(self, object_type: str, object_id: str | int) -> dict[str, Any]:
        """Fetch a single object/relationship via /objects API."""
        payload: dict[str, Any] = {"type": object_type, "id": object_id}
        data = self._request_json("POST", "/objects", json=payload)
        if not isinstance(data, dict):
            raise ApiResponseError("Expected objects endpoint to return a JSON object.")
        return data

    def get_download(self, resource: str) -> list[dict[str, Any]]:
        """Fetch bulk JSON downloads from /download endpoints."""
        data = self._request_json("GET", f"/download/{resource}")
        if not isinstance(data, list):
            raise ApiResponseError("Expected download endpoint to return a JSON list.")
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise ApiResponseError(
                    "Expected download item at index "
                    f"{index} to be an object, got {type(item).__name__}."
                )
            normalized.append(item)
        return normalized

    def get_escher_map(self, model_bigg_id: str, map_bigg_id: str) -> list[Any]:
        """Fetch raw Escher map JSON payload."""
        data = self._request_json("GET", f"/models/{model_bigg_id}/escher/{map_bigg_id}")
        if not isinstance(data, list):
            raise ApiResponseError("Expected Escher endpoint to return a JSON list.")
        return data

    def _request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise ApiError("Request timed out. Increase --timeout or retry later.") from exc
        except httpx.RequestError as exc:
            raise ApiError(f"Network error while contacting BiGGr API: {exc}") from exc

        if response.status_code in {401, 403}:
            raise ApiAuthError("API request failed with authorization error.")
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            suffix = f" Retry after {retry_after} seconds." if retry_after else ""
            raise ApiRateLimitError(f"BiGGr API rate limit reached.{suffix}")
        if response.status_code >= 400:
            body_preview = response.text.strip()
            detail = f" Response: {body_preview[:300]}" if body_preview else ""
            raise ApiError(f"API request failed with HTTP {response.status_code}.{detail}")

        try:
            return response.json()
        except ValueError as exc:
            raise ApiResponseError("Response was not valid JSON.") from exc
