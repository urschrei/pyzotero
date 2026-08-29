"""Console-script entry points.

The CLI needs the ``cli`` extra and the MCP server needs the ``mcp`` extra,
but ``[project.scripts]`` installs both scripts whichever extra is present.
Each entry point checks for its extra before it imports the module that
needs it, so that a missing extra ends in a short message and not in a
traceback.
"""

from __future__ import annotations

import sys
from importlib.util import find_spec

INSTALL_HINT = (
    "pyzotero: {script} needs the '{extra}' extra, which is not installed.\n"
    "Install it with:  pip install 'pyzotero[{extra}]'\n"
    "or, as a tool:    uv tool install 'pyzotero[cli,mcp]'"
)


def _require(module: str, *, extra: str, script: str) -> None:
    """Exit with an installation hint if ``module`` is not importable."""
    if find_spec(module) is None:
        sys.exit(INSTALL_HINT.format(script=script, extra=extra))


def cli() -> None:
    """Start the CLI after checking for the ``cli`` extra."""
    _require("click", extra="cli", script="pyzotero")
    from pyzotero.cli import main  # noqa: PLC0415

    main()


def mcp() -> None:
    """Start the MCP server after checking for the ``mcp`` extra."""
    _require("mcp", extra="mcp", script="pyzotero-mcp")
    from pyzotero.mcp_server import main  # noqa: PLC0415

    main()
