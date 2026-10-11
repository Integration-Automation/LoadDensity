"""Action files: je_action_core's JSON reader and writer with LoadDensity's exception and messages."""
from typing import Union

from je_action_core import ActionJsonFile, JsonFileMessages, JsonFileSettings

from je_load_density.utils.exception.exception_tags import cant_find_json_error, cant_save_json_error
from je_load_density.utils.exception.exceptions import LoadDensityTestJsonException

# Any error is wrapped, as LoadDensity always did; a missing file reads "<tag>: <tag>" as it always has.
_json_file = ActionJsonFile(JsonFileSettings(
    error=LoadDensityTestJsonException,
    messages=JsonFileMessages(missing=f"{cant_find_json_error}: {cant_find_json_error}",
                              unreadable=f"{cant_find_json_error}: {{error}}",
                              unwritable=f"{cant_save_json_error}: {{error}}"),
    read_errors=(Exception,),
    write_errors=(Exception,),
))


def read_action_json(json_file_path: str) -> Union[dict, list]:
    """
    讀取 JSON 檔案並回傳內容
    Read JSON file and return its content

    :param json_file_path: JSON 檔案路徑 (path to JSON file)
    :return: JSON 內容 (dict or list)
    :raises LoadDensityTestJsonException: 當檔案不存在或無法讀取時 (if file not found or cannot be read)
    """
    return _json_file.read(json_file_path)


def write_action_json(json_save_path: str, action_json: Union[dict, list]) -> None:
    """
    將資料寫入 JSON 檔案
    Write data into JSON file (data that cannot be serialised leaves the file as it was)

    :param json_save_path: JSON 檔案儲存路徑 (path to save JSON file)
    :param action_json: 要寫入的資料 (data to write, dict or list)
    :raises LoadDensityTestJsonException: 當檔案無法寫入時 (if file cannot be saved)
    """
    _json_file.write(json_save_path, action_json)
