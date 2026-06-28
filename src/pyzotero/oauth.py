"""OAuth 1.0a helper for obtaining a Zotero API key.

Zotero implements OAuth 1.0a as a way to provision an API key on a user's
behalf, so that an application does not have to ask the user to create a key by
hand. The handshake's only product is a normal Zotero API key plus the user's
numeric ID: the ``oauth_token`` returned by the access step *is* the API key.
Once obtained, the key is used exactly as a manually-created one would be.

The flow has three legs:

1. Fetch a temporary request token (signed with the application's client key
   and secret).
2. Send the user to the authorisation URL to approve the requested permissions.
3. Exchange the approved request token and a verifier for the access token,
   which carries the API key and user ID.

To use this module an application must first be registered at
https://www.zotero.org/oauth/apps to obtain a *client key* and *client secret*
(the OAuth consumer credentials). These are distinct from the API key the flow
produces.

OAuth support requires the optional ``oauth`` extra::

    pip install pyzotero[oauth]

Example::

    from pyzotero.oauth import ZoteroOAuth

    oauth = ZoteroOAuth(client_key, client_secret)
    url = oauth.authorize_url(write_access=True)
    # send the user to ``url``; they approve and receive a verifier code
    creds = oauth.complete(verifier)
    zot = creds.client()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

import httpx

from .errors import OAuthError

if TYPE_CHECKING:
    from ._client import Zotero

# Authlib failures plus transport-level errors are wrapped as OAuthError.
try:
    from authlib.integrations.httpx_client import OAuth1Client
    from authlib.integrations.httpx_client import OAuthError as _AuthlibOAuthError

    _OAUTH_FAILURES: tuple[type[BaseException], ...] = (
        httpx.HTTPError,
        _AuthlibOAuthError,
    )
except ImportError:  # pragma: no cover - exercised only without the extra
    OAuth1Client = None  # ty: ignore[invalid-assignment]
    _OAUTH_FAILURES = (httpx.HTTPError,)

REQUEST_TOKEN_URL = "https://www.zotero.org/oauth/request"  # noqa: S105 - URL, not a secret
AUTHORIZE_URL = "https://www.zotero.org/oauth/authorize"
ACCESS_TOKEN_URL = "https://www.zotero.org/oauth/access"  # noqa: S105 - URL, not a secret


@dataclass(frozen=True)
class ZoteroCredentials:
    """Credentials produced by a completed OAuth handshake.

    Attributes:
        api_key: A Zotero API key usable for authenticated requests.
        userid: The user's numeric Zotero ID, used as ``library_id``.
        username: The user's Zotero username, if returned by the server.

    """

    api_key: str
    userid: str
    username: str | None = None

    def client(self, **kwargs: Any) -> Zotero:
        """Return a ``Zotero`` client configured with these credentials.

        Any keyword arguments are forwarded to the ``Zotero`` constructor.
        """
        from ._client import Zotero  # noqa: PLC0415 - deferred to avoid import cost

        return Zotero(
            library_id=self.userid,
            library_type="user",
            api_key=self.api_key,
            **kwargs,
        )


class ZoteroOAuth:
    """Drive Zotero's OAuth 1.0a handshake to obtain an API key.

    Args:
        client_key: The application's OAuth client (consumer) key.
        client_secret: The application's OAuth client (consumer) secret.
        callback: The OAuth callback. Defaults to ``"oob"`` (out-of-band), in
            which Zotero displays a verifier code for the user to copy. Web
            applications should pass a registered redirect URL instead.
        transport: An optional httpx transport, used to inject a mock transport
            in tests. Mirrors the ``client`` injection seam on ``Zotero``.

    """

    def __init__(
        self,
        client_key: str,
        client_secret: str,
        callback: str = "oob",
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if OAuth1Client is None:
            err = (
                "OAuth support requires the 'oauth' extra. "
                "Install it with: pip install pyzotero[oauth]"
            )
            raise OAuthError(err)
        self.client_key = client_key
        self.client_secret = client_secret
        self.callback = callback
        self._transport = transport
        self._request_token: dict[str, str] | None = None

    @property
    def request_token(self) -> dict[str, str] | None:
        """The temporary request token from the most recent ``authorize_url``.

        Web applications can persist this between the request leg and the
        access leg (which span separate HTTP requests) and supply it back via
        the ``request_token`` argument to ``complete``/``complete_from_url``.
        """
        return self._request_token

    def _make_client(self, **kwargs: Any) -> OAuth1Client:
        """Build an OAuth1Client with the stored credentials and any transport."""
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return OAuth1Client(self.client_key, self.client_secret, **kwargs)

    def authorize_url(
        self,
        *,
        library_access: bool = True,
        write_access: bool = False,
        notes_access: bool = False,
        all_groups: str = "read",
        identity: bool = False,
    ) -> str:
        """Fetch a request token and return the URL to send the user to.

        The boolean flags map to Zotero's permission parameters. ``all_groups``
        sets the access level for current and future groups and must be one of
        ``"none"``, ``"read"`` or ``"write"``. Setting ``identity`` requests the
        user's identity only, without creating a key.

        The request token is stored on the instance for a subsequent
        ``complete`` call and is also available via ``request_token``.
        """
        params: dict[str, Any] = {}
        if library_access:
            params["library_access"] = 1
        if write_access:
            params["write_access"] = 1
        if notes_access:
            params["notes_access"] = 1
        if all_groups:
            params["all_groups"] = all_groups
        if identity:
            params["identity"] = 1
        try:
            with self._make_client(redirect_uri=self.callback) as client:
                self._request_token = dict(
                    client.fetch_request_token(REQUEST_TOKEN_URL)
                )
                return client.create_authorization_url(AUTHORIZE_URL, **params)
        except _OAUTH_FAILURES as exc:
            err = f"Failed to obtain an OAuth request token: {exc}"
            raise OAuthError(err) from exc

    def complete(
        self,
        verifier: str,
        *,
        request_token: dict[str, str] | None = None,
    ) -> ZoteroCredentials:
        """Exchange the approved request token for an API key.

        Args:
            verifier: The verifier code returned by Zotero after the user
                approves the application.
            request_token: The temporary request token. Optional when the same
                instance performed ``authorize_url``; required when the access
                leg runs in a separate process (e.g. a web request handler).

        Returns:
            A ``ZoteroCredentials`` carrying the API key and user ID.

        """
        token = request_token or self._request_token
        if token is None:
            err = (
                "No request token available; call authorize_url() first "
                "or pass request_token"
            )
            raise OAuthError(err)
        try:
            with self._make_client(
                token=token["oauth_token"],
                token_secret=token["oauth_token_secret"],
            ) as client:
                access = client.fetch_access_token(ACCESS_TOKEN_URL, verifier=verifier)
        except _OAUTH_FAILURES as exc:
            err = f"Failed to obtain an OAuth access token: {exc}"
            raise OAuthError(err) from exc
        try:
            return ZoteroCredentials(
                api_key=access["oauth_token"],
                userid=str(access["userID"]),
                username=access.get("username"),
            )
        except KeyError as exc:
            err = f"OAuth access response was missing a required field: {exc}"
            raise OAuthError(err) from exc

    def complete_from_url(
        self,
        authorization_response: str,
        *,
        request_token: dict[str, str] | None = None,
    ) -> ZoteroCredentials:
        """Complete the handshake from a callback redirect URL.

        Convenience for web applications: extracts the ``oauth_verifier`` query
        parameter from the URL Zotero redirected the user to, then delegates to
        ``complete``.
        """
        query = parse_qs(urlparse(authorization_response).query)
        verifiers = query.get("oauth_verifier")
        if not verifiers:
            err = "No oauth_verifier found in the authorization response URL"
            raise OAuthError(err)
        return self.complete(verifiers[0], request_token=request_token)
