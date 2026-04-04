import json
import os
import tempfile

import pytest

from je_load_density.utils.json.json_file.json_file import read_action_json, write_action_json
from je_load_density.utils.exception.exceptions import LoadDensityTestJsonException


class TestWriteActionJson:

    def test_write_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.json")
            data = {"key": "value", "number": 123}
            write_action_json(path, data)
            with open(path, "r", encoding="utf-8") as f:
                assert json.load(f) == data

    def test_write_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.json")
            data = [1, 2, 3]
            write_action_json(path, data)
            with open(path, "r", encoding="utf-8") as f:
                assert json.load(f) == data

    def test_write_unicode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.json")
            data = {"name": "測試"}
            write_action_json(path, data)
            with open(path, "r", encoding="utf-8") as f:
                result = json.load(f)
            assert result["name"] == "測試"


class TestReadActionJson:

    def test_read_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.json")
            data = {"hello": "world"}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            result = read_action_json(path)
            assert result == data

    def test_read_nonexistent_file_raises(self):
        with pytest.raises(LoadDensityTestJsonException):
            read_action_json("/nonexistent/path/to/file.json")

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "roundtrip.json")
            data = {"actions": [["step1", {}], ["step2", {"param": 1}]]}
            write_action_json(path, data)
            result = read_action_json(path)
            assert result == data
