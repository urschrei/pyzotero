"""Shared helpers used by both the CLI and MCP server."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from pyzotero import zotero

LOCAL_KEY_ENV = "PYZOTERO_LOCAL_API_KEY"
LOCAL_SERVER_ID_ENV = "PYZOTERO_LOCAL_SERVER_ID"


def get_zotero_client(
    locale: str = "en-US",
    server_id: str | None = None,
    local_api_key: str | None = None,
) -> zotero.Zotero:
    """Get a Zotero client that is configured for local access.

    Without the two optional arguments the client can only read.
    ``local_api_key`` permits writes (see :meth:`Zotero.authorize_local`),
    and ``server_id`` supplies a server ID that was kept from an earlier
    session, which prevents one initial request. :func:`get_write_client`
    fills both in from the stored key.
    """
    return zotero.Zotero(
        library_id="0",
        library_type="user",
        local=True,
        locale=locale,
        server_id=server_id,
        local_api_key=local_api_key,
    )


def local_key_path() -> Path:
    """Return the path of the file that holds a stored local API key.

    The file is ``pyzotero/local-api-key.json`` under ``$XDG_CONFIG_HOME``,
    or under ``~/.config`` if that variable is not set.
    """
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "pyzotero" / "local-api-key.json"


def load_local_key() -> tuple[str | None, str | None]:
    """Return ``(server_id, key)`` for local writes.

    The environment variables ``PYZOTERO_LOCAL_API_KEY`` and
    ``PYZOTERO_LOCAL_SERVER_ID`` take precedence. If the key variable is not
    set, the key file from :func:`local_key_path` supplies both values. Each
    value is None if no source supplies it.
    """
    key = os.environ.get(LOCAL_KEY_ENV)
    if key:
        return os.environ.get(LOCAL_SERVER_ID_ENV) or None, key
    try:
        data = json.loads(local_key_path().read_text())
    except (OSError, ValueError):
        return None, None
    if not isinstance(data, dict):
        return None, None
    return data.get("server_id") or None, data.get("key") or None


def save_local_key(key: str, server_id: str | None) -> Path:
    """Write ``key`` and ``server_id`` to the key file. Return its path.

    The file gets mode 0600, so that only the user can read it.
    """
    path = local_key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"server_id": server_id, "key": key}, indent=2) + "\n")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path


def get_write_client(locale: str = "en-US") -> zotero.Zotero:
    """Get a local client that can write, using the stored local API key.

    This function does not request a key itself. The MCP client starts and
    restarts the server, so a request at startup would show a Zotero dialog
    with no clear cause. Run ``pyzotero authorize`` to get a permanent key.

    Raises:
        RuntimeError: No key is stored and none is set in the environment.

    """
    server_id, key = load_local_key()
    if not key:
        msg = (
            "No local API key. Run 'pyzotero authorize' and choose 'Always Allow' "
            f"so that the key persists, or set {LOCAL_KEY_ENV} in the environment."
        )
        raise RuntimeError(msg)
    return get_zotero_client(locale, server_id=server_id, local_api_key=key)


def normalise_doi(doi: str) -> str:
    """Normalise a DOI for case-insensitive matching.

    Strips common prefixes (https://doi.org/, http://doi.org/, doi:) and converts to lowercase.
    DOIs are case-insensitive per the DOI specification.
    """
    if not doi:
        return ""

    # Strip whitespace
    doi = doi.strip()

    # Strip common prefixes
    prefixes = ["https://doi.org/", "http://doi.org/", "doi:"]
    for prefix in prefixes:
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix) :]
            break

    # Convert to lowercase for case-insensitive matching
    return doi.lower().strip()


def build_doi_index_full(zot: zotero.Zotero) -> dict[str, dict[str, str]]:
    """Build a mapping of normalised DOIs to Zotero item keys and original DOIs.

    Returns:
        Dict mapping normalised DOIs to dicts with 'key' and 'original' fields

    """
    doi_map: dict[str, dict[str, str]] = {}
    for item in zot.everything(zot.items()):
        data = item.get("data", {})
        item_doi = data.get("DOI", "")
        if not item_doi:
            continue
        normalised_doi = normalise_doi(item_doi)
        item_key = data.get("key", "")
        if normalised_doi and item_key:
            doi_map[normalised_doi] = {"key": item_key, "original": item_doi}
    return doi_map


def build_doi_index(zot: zotero.Zotero) -> dict[str, str]:
    """Build a mapping of normalised DOIs to Zotero item keys."""
    return {norm: entry["key"] for norm, entry in build_doi_index_full(zot).items()}


def format_creators(creators: list[dict[str, Any]]) -> list[str]:
    """Flatten Zotero creator dicts to display strings.

    Zotero creators may carry either (firstName, lastName) or a single ``name``
    field; emit ``"<first> <last>"``, falling back to ``lastName`` or ``name``.
    Creators that have none of the recognised fields are dropped.
    """
    names: list[str] = []
    for creator in creators:
        if "lastName" in creator:
            if "firstName" in creator:
                names.append(f"{creator['firstName']} {creator['lastName']}")
            else:
                names.append(creator["lastName"])
        elif "name" in creator:
            names.append(creator["name"])
    return names


def format_s2_paper(
    paper: dict[str, Any], in_library: bool | None = None
) -> dict[str, Any]:
    """Format a Semantic Scholar paper for output.

    Args:
        paper: Normalised paper dict from semantic_scholar module
        in_library: Boolean indicating if paper is in local Zotero

    Returns:
        Formatted dict for output

    """
    result: dict[str, Any] = {
        "paperId": paper.get("paperId"),
        "doi": paper.get("doi"),
        "title": paper.get("title"),
        "authors": [a.get("name") for a in (paper.get("authors") or [])],
        "year": paper.get("year"),
        "venue": paper.get("venue"),
        "citationCount": paper.get("citationCount"),
        "referenceCount": paper.get("referenceCount"),
        "isOpenAccess": paper.get("isOpenAccess"),
        "openAccessPdfUrl": paper.get("openAccessPdfUrl"),
    }

    if in_library is not None:
        result["inLibrary"] = in_library

    return result


def annotate_with_library(
    papers: list[dict[str, Any]], doi_map: dict[str, str]
) -> list[dict[str, Any]]:
    """Annotate papers with in_library status based on DOI matching.

    Args:
        papers: List of normalised paper dicts
        doi_map: Dict mapping normalised DOIs to Zotero item keys

    Returns:
        List of formatted paper dicts with inLibrary field

    """
    results = []
    for paper in papers:
        doi = paper.get("doi")
        in_library = False
        if doi:
            normalised = normalise_doi(doi)
            in_library = normalised in doi_map
        results.append(format_s2_paper(paper, in_library))
    return results
