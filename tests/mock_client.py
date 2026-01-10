"""Mock HTTP client for testing using httpx MockTransport."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx


class CaseInsensitiveDict(dict):
    """A dict that allows case-insensitive key access."""

    def __getitem__(self, key: str) -> str:
        # Try exact match first
        try:
            return super().__getitem__(key)
        except KeyError:
            pass
        # Try case-insensitive match
        key_lower = key.lower()
        for k, v in self.items():
            if k.lower() == key_lower:
                return v
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        if super().__contains__(key):
            return True
        if isinstance(key, str):
            key_lower = key.lower()
            return any(k.lower() == key_lower for k in self.keys())
        return False

    def get(self, key: str, default: str | None = None) -> str | None:
        try:
            return self[key]
        except KeyError:
            return default


@dataclass
class RecordedRequest:
    """Captured request for inspection."""

    method: str
    url: str
    _headers: dict[str, str]
    body: bytes

    @property
    def headers(self) -> CaseInsensitiveDict:
        """Return headers with case-insensitive access."""
        return CaseInsensitiveDict(self._headers)

    @property
    def querystring(self) -> dict[str, list[str]]:
        """Parse query string from URL."""
        parsed = urlparse(self.url)
        return parse_qs(parsed.query)

    def json(self) -> Any:
        """Parse body as JSON."""
        return json.loads(self.body.decode("utf-8"))


@dataclass
class MockRoute:
    """A mocked route definition."""

    method: str
    url: str
    body: str | bytes | Callable = ""
    status: int = 200
    content_type: str = "application/json"
    headers: dict[str, str] = field(default_factory=dict)

    def matches(self, request: httpx.Request) -> bool:
        """Check if this route matches the request."""
        if request.method != self.method:
            return False
        request_url = str(request.url).split("?")[0]
        route_url = self.url.split("?")[0]
        return request_url == route_url

    def respond(
        self, request: httpx.Request, recorded: RecordedRequest
    ) -> httpx.Response:
        """Generate response for this route."""
        # Ensure all header values are strings
        response_headers = {"content-type": self.content_type}
        for k, v in self.headers.items():
            response_headers[k] = str(v)

        if callable(self.body):
            # httpretty callback: (request, uri, headers) -> [status, headers, body]
            result = self.body(recorded, str(request.url), response_headers)
            status, resp_headers, body = result
            if isinstance(body, str):
                body = body.encode("utf-8")
            # Ensure callback response headers are strings too
            resp_headers = {k: str(v) for k, v in resp_headers.items()}
            return httpx.Response(status, headers=resp_headers, content=body)

        body = self.body
        if isinstance(body, str):
            body = body.encode("utf-8")
        return httpx.Response(self.status, headers=response_headers, content=body)


class MockClient:
    """Mock HTTP client with request recording."""

    def __init__(self):
        self.routes: list[MockRoute] = []
        self.requests: list[RecordedRequest] = []
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get the httpx Client with mock transport."""
        if self._client is None:
            self._client = httpx.Client(
                transport=httpx.MockTransport(self._handle),
                follow_redirects=True,
            )
        return self._client

    def register(
        self,
        method: str,
        url: str,
        body: str | bytes | Callable = "",
        status: int = 200,
        content_type: str = "application/json",
        headers: dict[str, Any] | None = None,
    ) -> None:
        """Register a mock route."""
        # Convert header values to strings
        str_headers = {}
        if headers:
            str_headers = {k: str(v) for k, v in headers.items()}

        self.routes.append(
            MockRoute(
                method=method,
                url=url,
                body=body,
                status=status,
                content_type=content_type,
                headers=str_headers,
            )
        )

    def reset(self) -> None:
        """Clear all routes and recorded requests."""
        self.routes.clear()
        self.requests.clear()

    def last_request(self) -> RecordedRequest | None:
        """Get the last recorded request."""
        return self.requests[-1] if self.requests else None

    def latest_requests(self) -> list[RecordedRequest]:
        """Get all recorded requests."""
        return self.requests.copy()

    def _handle(self, request: httpx.Request) -> httpx.Response:
        """Handle an HTTP request."""
        recorded = RecordedRequest(
            method=request.method,
            url=str(request.url),
            _headers=dict(request.headers),
            body=request.content,
        )
        self.requests.append(recorded)

        for route in reversed(self.routes):
            if route.matches(request):
                return route.respond(request, recorded)

        return httpx.Response(404, content=b"Not Found")
