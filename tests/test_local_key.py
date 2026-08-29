"""Tests for the stored local API key (#361, #362)."""

from __future__ import annotations

import json
import stat
from unittest.mock import patch

import pytest

from pyzotero import _helpers


@pytest.fixture(autouse=True)
def _isolated_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv(_helpers.LOCAL_KEY_ENV, raising=False)
    monkeypatch.delenv(_helpers.LOCAL_SERVER_ID_ENV, raising=False)
    return tmp_path


class TestKeyPath:
    def test_under_xdg_config_home(self, tmp_path):
        assert _helpers.local_key_path() == (
            tmp_path / "pyzotero" / "local-api-key.json"
        )

    def test_falls_back_to_dot_config(self, monkeypatch, tmp_path):
        monkeypatch.delenv("XDG_CONFIG_HOME")
        monkeypatch.setenv("HOME", str(tmp_path))
        assert _helpers.local_key_path() == (
            tmp_path / ".config" / "pyzotero" / "local-api-key.json"
        )


class TestSaveAndLoad:
    def test_round_trip(self):
        path = _helpers.save_local_key("abc123", "srv1")
        assert path == _helpers.local_key_path()
        assert json.loads(path.read_text()) == {"server_id": "srv1", "key": "abc123"}
        assert _helpers.load_local_key() == ("srv1", "abc123")

    def test_file_is_private(self):
        path = _helpers.save_local_key("abc123", None)
        assert stat.S_IMODE(path.stat().st_mode) == stat.S_IRUSR | stat.S_IWUSR

    def test_missing_server_id_is_none(self):
        _helpers.save_local_key("abc123", None)
        assert _helpers.load_local_key() == (None, "abc123")

    def test_no_file(self):
        assert _helpers.load_local_key() == (None, None)

    def test_corrupt_file(self):
        path = _helpers.local_key_path()
        path.parent.mkdir(parents=True)
        path.write_text("not json")
        assert _helpers.load_local_key() == (None, None)

    def test_wrong_shape(self):
        path = _helpers.local_key_path()
        path.parent.mkdir(parents=True)
        path.write_text("[1, 2]")
        assert _helpers.load_local_key() == (None, None)

    def test_env_overrides_file(self, monkeypatch):
        _helpers.save_local_key("filekey", "filesrv")
        monkeypatch.setenv(_helpers.LOCAL_KEY_ENV, "envkey")
        assert _helpers.load_local_key() == (None, "envkey")
        monkeypatch.setenv(_helpers.LOCAL_SERVER_ID_ENV, "envsrv")
        assert _helpers.load_local_key() == ("envsrv", "envkey")


class TestWriteClient:
    def test_no_key_names_the_remedy(self):
        with pytest.raises(RuntimeError, match="pyzotero authorize"):
            _helpers.get_write_client()

    def test_stored_key_is_used(self):
        _helpers.save_local_key("abc123", "srv1")
        with patch("pyzotero._helpers.get_zotero_client") as client:
            _helpers.get_write_client(locale="de-DE")
        client.assert_called_once_with(
            "de-DE", server_id="srv1", local_api_key="abc123"
        )
