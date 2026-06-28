"""Tests for the OAuth 1.0a key-acquisition helper.

The three Zotero OAuth endpoints are stubbed with an httpx MockTransport
injected via the ``transport`` seam, so no network access is required.
"""

from __future__ import annotations

import functools

import httpx
import pytest
from click.testing import CliRunner

from pyzotero.cli import main
from pyzotero.errors import OAuthError
from pyzotero.oauth import ZoteroCredentials, ZoteroOAuth


REQUEST_BODY = (
    "oauth_token=tmpTOKEN&oauth_token_secret=tmpSECRET&oauth_callback_confirmed=true"
)
ACCESS_BODY = "oauth_token=REALKEY&oauth_token_secret=REALKEY&userID=12345&username=foo"


def _transport(*, request_status: int = 200, access_status: int = 200):
    """Return a MockTransport stubbing the three OAuth endpoints."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "oauth/request" in url:
            return httpx.Response(request_status, text=REQUEST_BODY)
        if "oauth/access" in url:
            return httpx.Response(access_status, text=ACCESS_BODY)
        return httpx.Response(404, text="not found")

    return httpx.MockTransport(handler)


def test_authorize_url_contains_token_and_params():
    oauth = ZoteroOAuth("ck", "cs", transport=_transport())
    url = oauth.authorize_url(write_access=True)
    assert "oauth_token=tmpTOKEN" in url
    assert "write_access=1" in url
    assert "library_access=1" in url
    assert "all_groups=read" in url
    # the request token is stashed for the subsequent complete() call
    assert oauth.request_token == {
        "oauth_token": "tmpTOKEN",
        "oauth_token_secret": "tmpSECRET",
        "oauth_callback_confirmed": "true",
    }


def test_authorize_url_omits_unrequested_permissions():
    oauth = ZoteroOAuth("ck", "cs", transport=_transport())
    url = oauth.authorize_url(library_access=False, all_groups="none")
    assert "library_access" not in url
    assert "write_access" not in url
    assert "all_groups=none" in url


def test_complete_returns_credentials():
    oauth = ZoteroOAuth("ck", "cs", transport=_transport())
    oauth.authorize_url()
    creds = oauth.complete("verifier123")
    assert creds == ZoteroCredentials(api_key="REALKEY", userid="12345", username="foo")


def test_credentials_client_builds_zotero():
    creds = ZoteroCredentials(api_key="REALKEY", userid="12345", username="foo")
    zot = creds.client()
    assert zot.library_id == "12345"
    assert zot.library_type == "users"
    assert zot.api_key == "REALKEY"


def test_complete_from_url_extracts_verifier():
    oauth = ZoteroOAuth("ck", "cs", transport=_transport())
    oauth.authorize_url()
    callback = "https://app.example/callback?oauth_token=tmpTOKEN&oauth_verifier=abc"
    creds = oauth.complete_from_url(callback)
    assert creds.api_key == "REALKEY"


def test_complete_with_supplied_request_token():
    # Simulates a web app where the access leg runs in a separate instance.
    oauth = ZoteroOAuth("ck", "cs", transport=_transport())
    token = {"oauth_token": "tmpTOKEN", "oauth_token_secret": "tmpSECRET"}
    creds = oauth.complete("verifier123", request_token=token)
    assert creds.userid == "12345"


def test_request_token_failure_raises_oautherror():
    oauth = ZoteroOAuth("ck", "cs", transport=_transport(request_status=401))
    with pytest.raises(OAuthError, match="request token"):
        oauth.authorize_url()


def test_access_token_failure_raises_oautherror():
    oauth = ZoteroOAuth("ck", "cs", transport=_transport(access_status=401))
    oauth.authorize_url()
    with pytest.raises(OAuthError, match="access token"):
        oauth.complete("verifier123")


def test_complete_without_request_token_raises():
    oauth = ZoteroOAuth("ck", "cs", transport=_transport())
    with pytest.raises(OAuthError, match="No request token"):
        oauth.complete("verifier123")


def test_complete_from_url_without_verifier_raises():
    oauth = ZoteroOAuth("ck", "cs", transport=_transport())
    oauth.authorize_url()
    with pytest.raises(OAuthError, match="oauth_verifier"):
        oauth.complete_from_url("https://app.example/callback?oauth_token=tmpTOKEN")


def test_missing_extra_raises(monkeypatch):
    monkeypatch.setattr("pyzotero.oauth.OAuth1Client", None)
    with pytest.raises(OAuthError, match="oauth"):
        ZoteroOAuth("ck", "cs")


def test_cli_auth_command(monkeypatch):
    transport = _transport()
    # Inject the mock transport into the class the CLI constructs.
    monkeypatch.setattr(
        "pyzotero.oauth.ZoteroOAuth",
        functools.partial(ZoteroOAuth, transport=transport),
    )
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["auth", "--client-key", "ck", "--client-secret", "cs", "--write"],
        input="verifier123\n",
    )
    assert result.exit_code == 0
    assert "library_id: 12345" in result.output
    assert "api_key:    REALKEY" in result.output


def test_cli_auth_reads_env_credentials(monkeypatch):
    transport = _transport()
    monkeypatch.setattr(
        "pyzotero.oauth.ZoteroOAuth",
        functools.partial(ZoteroOAuth, transport=transport),
    )
    monkeypatch.setenv("ZOTERO_CLIENT_KEY", "ck")
    monkeypatch.setenv("ZOTERO_CLIENT_SECRET", "cs")
    runner = CliRunner()
    result = runner.invoke(main, ["auth"], input="verifier123\n")
    assert result.exit_code == 0
    assert "api_key:    REALKEY" in result.output
