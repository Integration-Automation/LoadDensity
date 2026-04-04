import json
import os

from je_load_density.utils.file_process.get_dir_file_list import get_dir_files_as_list


class TestGetDirFilesAsList:

    def test_find_json_files(self, tmp_path):
        (tmp_path / "a.json").write_text("{}", encoding="utf-8")
        (tmp_path / "b.json").write_text("{}", encoding="utf-8")
        (tmp_path / "c.txt").write_text("text", encoding="utf-8")
        result = get_dir_files_as_list(str(tmp_path), ".json")
        assert len(result) == 2
        assert all(f.endswith(".json") for f in result)

    def test_find_nested_files(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.json").write_text("{}", encoding="utf-8")
        result = get_dir_files_as_list(str(tmp_path), ".json")
        assert len(result) == 1

    def test_no_matching_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("", encoding="utf-8")
        result = get_dir_files_as_list(str(tmp_path), ".json")
        assert result == []

    def test_nonexistent_dir(self):
        result = get_dir_files_as_list("/nonexistent/dir/path")
        assert result == []

    def test_custom_extension(self, tmp_path):
        (tmp_path / "file.xml").write_text("<root/>", encoding="utf-8")
        (tmp_path / "file.json").write_text("{}", encoding="utf-8")
        result = get_dir_files_as_list(str(tmp_path), ".xml")
        assert len(result) == 1
        assert result[0].endswith(".xml")
