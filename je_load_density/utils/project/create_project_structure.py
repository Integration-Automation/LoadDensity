from os import getcwd
from pathlib import Path
from threading import Lock
from typing import Optional

from je_load_density.utils.json.json_file.json_file import write_action_json
from je_load_density.utils.project.template.template_executor import executor_template_1, executor_template_2
from je_load_density.utils.project.template.template_keyword import template_keyword_1, template_keyword_2


def create_dir(dir_name: str) -> None:
    """
    建立目錄
    Create directory

    :param dir_name: 要建立的目錄名稱 (Directory name to create)
    """
    Path(dir_name).mkdir(parents=True, exist_ok=True)


def create_template(parent_name: str, project_path: Optional[str] = None) -> None:
    """
    建立模板檔案 (Create template files)

    :param parent_name: 專案主目錄名稱 (Project parent folder name)
    :param project_path: 專案路徑 (Project path), 預設為當前工作目錄 (default: current working directory)
    """
    if project_path is None:
        project_path = getcwd()

    project_root = Path(project_path) / parent_name
    keyword_dir_path = project_root / "keyword"
    executor_dir_path = project_root / "executor"

    # 建立 keyword JSON 檔案
    if keyword_dir_path.exists() and keyword_dir_path.is_dir():
        write_action_json(str(keyword_dir_path) + "keyword1.json", template_keyword_1)
        write_action_json(str(keyword_dir_path) + "keyword2.json", template_keyword_2)

    # 建立 executor Python 檔案
    if executor_dir_path.exists() and executor_dir_path.is_dir():
        lock = Lock()
        with lock:
            with open(executor_dir_path / "executor_one_file.py", "w+", encoding="utf-8") as file:
                file.write(
                    executor_template_1.replace(
                        "{temp}",
                        str(keyword_dir_path / "keyword1.json")
                    )
                )
            with open(executor_dir_path / "executor_folder.py", "w+", encoding="utf-8") as file:
                file.write(
                    executor_template_2.replace(
                        "{temp}",
                        str(keyword_dir_path)
                    )
                )


def create_project_dir(project_path: Optional[str] = None, parent_name: str = "LoadDensity") -> None:
    """
    建立專案目錄結構 (Create project directory structure)

    :param project_path: 專案路徑 (Project path), 預設為當前工作目錄 (default: current working directory)
    :param parent_name: 專案主目錄名稱 (Project parent folder name)
    """
    if project_path is None:
        project_path = getcwd()

    project_root = Path(project_path) / parent_name
    create_dir(str(project_root) + "keyword")
    create_dir(str(project_root) + "executor")
    create_template(parent_name, project_path)