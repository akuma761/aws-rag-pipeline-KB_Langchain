import json
import os
import tempfile
from unittest.mock import patch

from app.config import _load_config, _save_config, _load_stored_kb_id, _save_kb_id


def test_load_config_file_not_found():
    with patch("app.config._KB_CONFIG_PATH", "/nonexistent/path.json"):
        assert _load_config() == {}


def test_load_config_invalid_json():
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    f.write("not json")
    f.close()
    with patch("app.config._KB_CONFIG_PATH", f.name):
        assert _load_config() == {}
    os.remove(f.name)


def test_save_and_load_config():
    dir = tempfile.mkdtemp()
    path = os.path.join(dir, "test.json")
    with patch("app.config._KB_CONFIG_PATH", path):
        _save_config(kb_id="abc", bucket_name="my-bucket")
        data = _load_config()
        assert data["kb_id"] == "abc"
        assert data["bucket_name"] == "my-bucket"
    os.remove(path)
    os.rmdir(dir)


def test_save_config_merges():
    dir = tempfile.mkdtemp()
    path = os.path.join(dir, "test.json")
    with patch("app.config._KB_CONFIG_PATH", path):
        _save_config(kb_id="abc")
        _save_config(ds_id="def")
        data = _load_config()
        assert data["kb_id"] == "abc"
        assert data["ds_id"] == "def"
    os.remove(path)
    os.rmdir(dir)


def test_load_stored_kb_id_returns_empty_when_missing():
    with patch("app.config._load_config", return_value={}):
        assert _load_stored_kb_id() == ""


def test_load_stored_kb_id_returns_value():
    with patch("app.config._load_config", return_value={"kb_id": "test-kb"}):
        assert _load_stored_kb_id() == "test-kb"


def test_save_kb_id():
    with patch("app.config._save_config") as mock:
        _save_kb_id("new-kb")
        mock.assert_called_once_with(kb_id="new-kb")
