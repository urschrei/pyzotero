"""Tests for the console-script launchers in pyzotero._entry."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pyzotero import _entry


@pytest.mark.parametrize(
    ("launcher", "script", "extra"),
    [(_entry.cli, "pyzotero", "cli"), (_entry.mcp, "pyzotero-mcp", "mcp")],
)
def test_missing_extra_exits_with_hint(launcher, script, extra):
    with (
        patch("pyzotero._entry.find_spec", return_value=None),
        pytest.raises(SystemExit) as excinfo,
    ):
        launcher()
    message = str(excinfo.value)
    assert script in message
    assert f"pyzotero[{extra}]" in message
    assert "pyzotero[cli,mcp]" in message


def test_cli_delegates_when_extra_present():
    pytest.importorskip("click")
    with patch("pyzotero.cli.main") as main:
        _entry.cli()
    main.assert_called_once_with()


def test_mcp_delegates_when_extra_present():
    pytest.importorskip("mcp")
    with patch("pyzotero.mcp_server.main") as main:
        _entry.mcp()
    main.assert_called_once_with()
