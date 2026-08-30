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


ITEM_TYPE_FIELDS = {
    "book": ["title", "abstractNote", "date", "publisher", "numPages"],
    "journalArticle": ["title", "abstractNote", "date", "publicationTitle", "DOI"],
}

CREATOR_TYPES = {
    "book": ["author", "editor"],
    "journalArticle": ["author", "contributor"],
}


def _schema_mock(mock):
    """Give a mock client the schema calls that item validation makes."""
    mock.item_types.return_value = [
        {"itemType": name, "localized": name} for name in ITEM_TYPE_FIELDS
    ]
    mock.item_type_fields.side_effect = lambda t: [
        {"field": f, "localized": f} for f in ITEM_TYPE_FIELDS[t]
    ]
    mock.item_creator_types.side_effect = lambda t: [
        {"creatorType": c, "localized": c} for c in CREATOR_TYPES[t]
    ]
    return mock


@pytest.fixture
def write_zot():
    """Patch get_write_client to return a mock, and return the mock."""
    mock = _schema_mock(MagicMock())
    mock.create_collections.return_value = {"success": {"0": "NEWCOLL"}, "failed": {}}
    mock.create_items.return_value = {"success": {"0": "NEWITEM"}, "failed": {}}
    mock.item.side_effect = lambda key: {
        "key": key,
        "version": 3,
        "data": {"key": key, "version": 3, "collections": ["OLD"]},
    }
    with patch("pyzotero.cli.get_write_client", return_value=mock):
        yield mock


@pytest.fixture
def item_file(tmp_path):
    """Return a function that writes a payload to a JSON file and names it."""

    def write(payload, name="items.json"):
        path = tmp_path / name
        path.write_text(json.dumps(payload))
        return str(path)

    return write


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

    def test_createitem_refuses_without_key(self, runner, item_file):
        """The createitem argument is a file, so it needs its own case"""
        path = item_file({"itemType": "book", "title": "A Book"})
        result = runner.invoke(cli.main, ["createitem", path])
        assert result.exit_code == 1
        assert "pyzotero authorize" in result.output

    def test_locale_reaches_write_client(self, runner, write_zot):
        with patch("pyzotero.cli.get_write_client", return_value=write_zot) as gwc:
            runner.invoke(cli.main, ["--locale", "de-DE", "createcollection", "N"])
        gwc.assert_called_once_with("de-DE")


class TestCreateItem:
    def test_single_item(self, runner, write_zot, item_file):
        path = item_file({"itemType": "book", "title": "A Book"})
        result = runner.invoke(cli.main, ["createitem", path])
        assert result.exit_code == 0, result.output
        assert "Created 1 items: NEWITEM" in result.output
        assert write_zot.create_items.call_args[0][0] == [
            {"itemType": "book", "title": "A Book"}
        ]

    def test_list_of_items(self, runner, write_zot, item_file):
        write_zot.create_items.return_value = {
            "success": {"0": "KEY1", "1": "KEY2"},
            "failed": {},
        }
        path = item_file(
            [
                {"itemType": "book", "title": "One"},
                {"itemType": "journalArticle", "title": "Two", "DOI": "10.1234/x"},
            ]
        )
        result = runner.invoke(cli.main, ["createitem", path])
        assert result.exit_code == 0, result.output
        assert "Created 2 items: KEY1, KEY2" in result.output
        assert len(write_zot.create_items.call_args[0][0]) == len(["One", "Two"])

    def test_stdin(self, runner, write_zot):
        result = runner.invoke(
            cli.main,
            ["createitem", "-"],
            input=json.dumps({"itemType": "book", "title": "Piped"}),
        )
        assert result.exit_code == 0, result.output
        assert "NEWITEM" in result.output
        assert write_zot.create_items.call_args[0][0] == [
            {"itemType": "book", "title": "Piped"}
        ]

    def test_creators_and_other_common_keys_are_accepted(
        self, runner, write_zot, item_file
    ):
        path = item_file(
            {
                "itemType": "book",
                "title": "A Book",
                "creators": [{"creatorType": "author", "lastName": "Shelley"}],
                "collections": ["EXISTING"],
                "relations": {},
            }
        )
        result = runner.invoke(cli.main, ["createitem", path])
        assert result.exit_code == 0, result.output

    def test_invalid_itemtype(self, runner, write_zot, item_file):
        path = item_file(
            [{"itemType": "book", "title": "Fine"}, {"itemType": "notAType"}]
        )
        result = runner.invoke(cli.main, ["createitem", path])
        assert result.exit_code == 1
        assert "index 1" in result.output
        assert "notAType" in result.output
        write_zot.create_items.assert_not_called()

    def test_invalid_field(self, runner, write_zot, item_file):
        path = item_file({"itemType": "book", "title": "A Book", "issue": "3"})
        result = runner.invoke(cli.main, ["createitem", path])
        assert result.exit_code == 1
        assert "index 0" in result.output
        assert "issue" in result.output
        write_zot.create_items.assert_not_called()

    def test_missing_itemtype(self, runner, write_zot, item_file):
        path = item_file({"title": "No type"})
        result = runner.invoke(cli.main, ["createitem", path])
        assert result.exit_code == 1
        assert "no itemType" in result.output

    def test_collection_option(self, runner, write_zot, item_file):
        path = item_file(
            [
                {"itemType": "book", "title": "One"},
                {"itemType": "book", "title": "Two", "collections": ["FD9AUNP2"]},
            ]
        )
        result = runner.invoke(
            cli.main, ["createitem", path, "--collection", "FD9AUNP2"]
        )
        assert result.exit_code == 0, result.output
        sent = write_zot.create_items.call_args[0][0]
        # the key is added once, and an item that already has it is unchanged
        assert [i["collections"] for i in sent] == [["FD9AUNP2"], ["FD9AUNP2"]]

    def test_tag_option(self, runner, write_zot, item_file):
        path = item_file({"itemType": "book", "title": "One", "tags": ["existing"]})
        result = runner.invoke(
            cli.main, ["createitem", path, "--tag", "one", "--tag", "two"]
        )
        assert result.exit_code == 0, result.output
        sent = write_zot.create_items.call_args[0][0]
        # a string tag becomes a tag object, and the new tags follow it
        assert sent[0]["tags"] == [
            {"tag": "existing"},
            {"tag": "one"},
            {"tag": "two"},
        ]

    def test_tag_is_not_repeated(self, runner, write_zot, item_file):
        path = item_file({"itemType": "book", "title": "One", "tags": [{"tag": "one"}]})
        runner.invoke(cli.main, ["createitem", path, "--tag", "one"])
        sent = write_zot.create_items.call_args[0][0]
        assert sent[0]["tags"] == [{"tag": "one"}]

    def test_json_output(self, runner, write_zot, item_file):
        path = item_file({"itemType": "book", "title": "A Book"})
        result = runner.invoke(
            cli.main,
            ["createitem", path, "--collection", "COLL1", "--tag", "t", "--json"],
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {
            "created": ["NEWITEM"],
            "collection": "COLL1",
            "tags": ["t"],
        }

    def test_rejection_names_failures_and_progress(self, runner, write_zot, item_file):
        write_zot.create_items.return_value = {
            "success": {"0": "KEY1"},
            "failed": {"1": {"code": 400, "message": "Invalid field"}},
        }
        path = item_file(
            [{"itemType": "book", "title": "One"}, {"itemType": "book", "title": "Two"}]
        )
        result = runner.invoke(cli.main, ["createitem", path])
        assert result.exit_code == 1
        assert "rejected 1 of 2 items" in result.output
        assert "Invalid field" in result.output
        assert "KEY1" in result.output

    def test_malformed_json(self, runner, write_zot, tmp_path):
        path = tmp_path / "broken.json"
        path.write_text("{not json")
        result = runner.invoke(cli.main, ["createitem", str(path)])
        assert result.exit_code == 1
        assert "valid JSON" in result.output

    def test_scalar_json(self, runner, write_zot, item_file):
        result = runner.invoke(cli.main, ["createitem", item_file("a string")])
        assert result.exit_code == 1
        assert "object or a list of objects" in result.output

    def test_empty_list(self, runner, write_zot, item_file):
        result = runner.invoke(cli.main, ["createitem", item_file([])])
        assert result.exit_code == 1
        assert "No items to create" in result.output

    def test_missing_file(self, runner, write_zot, tmp_path):
        result = runner.invoke(cli.main, ["createitem", str(tmp_path / "absent.json")])
        assert result.exit_code == USAGE_ERROR


class TestListItemFields:
    @pytest.fixture
    def read_zot(self):
        mock = _schema_mock(MagicMock())
        with patch("pyzotero.cli.get_zotero_client", return_value=mock):
            yield mock

    def test_fields_and_creator_types(self, runner, read_zot):
        result = runner.invoke(cli.main, ["listitemfields", "book"])
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {
            "itemType": "book",
            "fields": ITEM_TYPE_FIELDS["book"],
            "creatorTypes": CREATOR_TYPES["book"],
        }

    def test_requires_an_item_type(self, runner, read_zot):
        result = runner.invoke(cli.main, ["listitemfields"])
        assert result.exit_code == USAGE_ERROR


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
