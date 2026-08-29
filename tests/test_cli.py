"""Tests for the CLI write commands (#361)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("click")

from click.testing import CliRunner

from pyzotero import cli
from pyzotero._helpers import local_key_path


USAGE_ERROR = 2  # click's exit code for bad arguments


@pytest.fixture(autouse=True)
def _isolated_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("PYZOTERO_LOCAL_API_KEY", raising=False)
    monkeypatch.delenv("PYZOTERO_LOCAL_SERVER_ID", raising=False)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def write_zot():
    """Patch get_write_client to return a mock, and return the mock."""
    mock = MagicMock()
    mock.create_collections.return_value = {"success": {"0": "NEWCOLL"}, "failed": {}}
    mock.item.side_effect = lambda key: {
        "key": key,
        "version": 3,
        "data": {"key": key, "version": 3, "collections": ["OLD"]},
    }
    with patch("pyzotero.cli.get_write_client", return_value=mock):
        yield mock


class TestKeyGate:
    @pytest.mark.parametrize(
        "args",
        [
            ["createcollection", "Name"],
            ["addtocollection", "COLL", "ABC123"],
            ["removefromcollection", "COLL", "ABC123"],
            ["movetocollection", "--from", "A", "--to", "B", "ABC123"],
        ],
    )
    def test_refuses_without_key(self, runner, args):
        result = runner.invoke(cli.main, args)
        assert result.exit_code == 1
        assert "pyzotero authorize" in result.output

    def test_locale_reaches_write_client(self, runner, write_zot):
        with patch("pyzotero.cli.get_write_client", return_value=write_zot) as gwc:
            runner.invoke(cli.main, ["--locale", "de-DE", "createcollection", "N"])
        gwc.assert_called_once_with("de-DE")


class TestCreateCollection:
    def test_top_level(self, runner, write_zot):
        result = runner.invoke(cli.main, ["createcollection", "Top"])
        assert result.exit_code == 0, result.output
        assert "NEWCOLL" in result.output
        assert write_zot.create_collections.call_args[0][0] == [{"name": "Top"}]

    def test_nested_json(self, runner, write_zot):
        result = runner.invoke(
            cli.main, ["createcollection", "Kids", "--parent", "PARENT1", "--json"]
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {
            "created": "NEWCOLL",
            "name": "Kids",
            "parent": "PARENT1",
        }
        assert write_zot.create_collections.call_args[0][0] == [
            {"name": "Kids", "parentCollection": "PARENT1"}
        ]

    def test_rejection_is_an_error(self, runner, write_zot):
        write_zot.create_collections.return_value = {
            "success": {},
            "failed": {"0": {"code": 400, "message": "Bad name"}},
        }
        result = runner.invoke(cli.main, ["createcollection", "Bad"])
        assert result.exit_code == 1
        assert "Bad name" in result.output


class TestMembership:
    def test_add_many(self, runner, write_zot):
        result = runner.invoke(
            cli.main, ["addtocollection", "COLL1", "ABC123", "DEF456", "--json"]
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {
            "collection": "COLL1",
            "added": ["ABC123", "DEF456"],
        }
        calls = write_zot.addto_collection.call_args_list
        assert [c[0][0] for c in calls] == ["COLL1", "COLL1"]
        assert [c[0][1]["key"] for c in calls] == ["ABC123", "DEF456"]

    def test_add_text_output(self, runner, write_zot):
        result = runner.invoke(cli.main, ["addtocollection", "COLL1", "ABC123"])
        assert result.exit_code == 0, result.output
        assert "Added 1 items to COLL1: ABC123" in result.output

    def test_remove(self, runner, write_zot):
        result = runner.invoke(
            cli.main, ["removefromcollection", "COLL1", "ABC123", "--json"]
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {
            "collection": "COLL1",
            "removed": ["ABC123"],
        }
        args = write_zot.deletefrom_collection.call_args[0]
        assert args[0] == "COLL1"
        assert args[1]["key"] == "ABC123"

    def test_move(self, runner, write_zot):
        result = runner.invoke(
            cli.main,
            ["movetocollection", "--from", "OLD", "--to", "NEW", "ABC123", "--json"],
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {
            "from": "OLD",
            "to": "NEW",
            "moved": ["ABC123"],
        }
        args = write_zot.moveto_collection.call_args[0]
        assert args[:2] == ("OLD", "NEW")
        assert args[2]["key"] == "ABC123"

    def test_move_requires_both_collections(self, runner, write_zot):
        result = runner.invoke(cli.main, ["movetocollection", "--from", "OLD", "ABC"])
        assert result.exit_code == USAGE_ERROR
        assert "--to" in result.output

    def test_requires_at_least_one_item(self, runner, write_zot):
        result = runner.invoke(cli.main, ["addtocollection", "COLL1"])
        assert result.exit_code == USAGE_ERROR

    def test_failure_names_item_and_progress(self, runner, write_zot):
        """A batch stops at the first failure and reports what is already done"""
        write_zot.addto_collection.side_effect = [None, RuntimeError("boom"), None]
        result = runner.invoke(
            cli.main, ["addtocollection", "COLL1", "AAA", "BBB", "CCC"]
        )
        assert result.exit_code == 1
        assert "BBB: boom" in result.output
        assert "changed 1 of 3 items" in result.output
        assert "AAA" in result.output
        # the third item is not attempted
        assert write_zot.addto_collection.call_count == len(["AAA", "BBB"])


class TestAuthorize:
    @pytest.fixture
    def read_zot(self):
        mock = MagicMock()
        mock.server_id = "srv1"
        with patch("pyzotero.cli.get_zotero_client", return_value=mock):
            yield mock

    def test_persistent_key_is_stored(self, runner, read_zot):
        read_zot.authorize_local.return_value = {"key": "abc123", "remember": True}
        result = runner.invoke(cli.main, ["authorize"])
        assert result.exit_code == 0, result.output
        path = local_key_path()
        assert json.loads(path.read_text()) == {"server_id": "srv1", "key": "abc123"}
        assert str(path) in result.output

    def test_no_store_flag(self, runner, read_zot):
        read_zot.authorize_local.return_value = {"key": "abc123", "remember": True}
        result = runner.invoke(cli.main, ["authorize", "--no-store"])
        assert result.exit_code == 0, result.output
        assert not local_key_path().exists()
        assert "PYZOTERO_LOCAL_API_KEY" in result.output

    def test_single_use_key_is_not_stored(self, runner, read_zot):
        read_zot.authorize_local.return_value = {"key": "once", "remember": False}
        result = runner.invoke(cli.main, ["authorize"])
        assert result.exit_code == 0, result.output
        assert not local_key_path().exists()
        assert "single-use" in result.output

    def test_app_name_passed_through(self, runner, read_zot):
        read_zot.authorize_local.return_value = {"key": "k", "remember": True}
        runner.invoke(cli.main, ["authorize", "--app-name", "My tool"])
        read_zot.authorize_local.assert_called_once_with("My tool")
