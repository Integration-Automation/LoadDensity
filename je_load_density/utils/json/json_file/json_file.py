import json
from pathlib import Path
from threading import Lock
from typing import Any, Union

from je_load_density.utils.exception.exceptions import LoadDensityTestJsonException
from je_load_density.utils.exception.exception_tags import cant_find_json_error, cant_save_json_error


def read_action_json(json_file_path: str) -> Union[dict, list]:
    """
    讀取 JSON 檔案並回傳內容
    Read JSON file and return its content

    :param json_file_path: JSON 檔案路徑 (path to JSON file)
    :return: JSON 內容 (dict or list)
    :raises LoadDensityTestJsonException: 當檔案不存在或無法讀取時 (if file not found or cannot be read)
    """
    lock = Lock()
    try:
        with lock:
            file_path = Path(json_file_path)
            if file_path.exists() and file_path.is_file():
                with open(json_file_path, "r", encoding="utf-8") as read_file:
                    return json.load(read_file)
            else:
                raise LoadDensityTestJsonException(cant_find_json_error)
    except Exception as error:
        # 捕捉所有錯誤並轉換成自訂例外
        # Catch all errors and raise custom exception
        raise LoadDensityTestJsonException(f"{cant_find_json_error}: {error}")


def write_action_json(json_save_path: str, action_json: Union[dict, list]) -> None:
    """
    將資料寫入 JSON 檔案
    Write data into JSON file

    :param json_save_path: JSON 檔案儲存路徑 (path to save JSON file)
    :param action_json: 要寫入的資料 (data to write, dict or list)
    :raises LoadDensityTestJsonException: 當檔案無法寫入時 (if file cannot be saved)
    """
    lock = Lock()
    try:
        with lock:
            with open(json_save_path, "w+", encoding="utf-8") as file_to_write:
                json.dump(action_json, file_to_write, indent=4, ensure_ascii=False)
    except Exception as error:
        raise LoadDensityTestJsonException(f"{cant_save_json_error}: {error}")