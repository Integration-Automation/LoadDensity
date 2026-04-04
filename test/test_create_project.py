import os
import tempfile

from je_load_density.utils.project.create_project_structure import create_project_dir, create_dir


class TestCreateDir:

    def test_create_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "subdir", "nested")
            create_dir(target)
            assert os.path.isdir(target)

    def test_create_dir_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_dir(tmp)
            assert os.path.isdir(tmp)


class TestCreateProjectDir:

    def test_creates_keyword_and_executor_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_project_dir(project_path=tmp, parent_name="TestProject")
            project_root = os.path.join(tmp, "TestProject")
            assert os.path.isdir(os.path.join(project_root, "keyword"))
            assert os.path.isdir(os.path.join(project_root, "executor"))

    def test_executor_files_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_project_dir(project_path=tmp, parent_name="TestProject")
            executor_dir = os.path.join(tmp, "TestProject", "executor")
            assert os.path.isfile(os.path.join(executor_dir, "executor_one_file.py"))
            assert os.path.isfile(os.path.join(executor_dir, "executor_folder.py"))

    def test_keyword_files_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_project_dir(project_path=tmp, parent_name="TestProject")
            keyword_dir = os.path.join(tmp, "TestProject", "keyword")
            assert os.path.isfile(os.path.join(keyword_dir, "keyword1.json"))
            assert os.path.isfile(os.path.join(keyword_dir, "keyword2.json"))
