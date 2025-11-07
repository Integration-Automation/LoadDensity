import json
import sys
from threading import Lock
from typing import Tuple, Dict

from je_load_density.utils.exception.exception_tags import cant_generate_json_report
from je_load_density.utils.exception.exceptions import LoadDensityGenerateJsonReportException
from je_load_density.utils.test_record.test_record_class import test_record_instance


def generate_json() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """
    產生測試紀錄的 JSON 結構
    Generate JSON structure for test records

    :return: (成功測試字典, 失敗測試字典)
             (success_dict, failure_dict)
    """
    if not test_record_instance.test_record_list and not test_record_instance.error_record_list:
        raise LoadDensityGenerateJsonReportException(cant_generate_json_report)

    success_dict: Dict[str, dict] = {}
    failure_dict: Dict[str, dict] = {}

    # 成功測試紀錄 (Success records)
    for idx, record_data in enumerate(test_record_instance.test_record_list, start=1):
        success_dict[f"Success_Test{idx}"] = {
            "Method": str(record_data.get("Method")),
            "test_url": str(record_data.get("test_url")),
            "name": str(record_data.get("name")),
            "status_code": str(record_data.get("status_code")),
            "text": str(record_data.get("text")),
            "content": str(record_data.get("content")),
            "headers": str(record_data.get("headers")),
        }

    # 失敗測試紀錄 (Failure records)
    for idx, record_data in enumerate(test_record_instance.error_record_list, start=1):
        failure_dict[f"Failure_Test{idx}"] = {
            "Method": str(record_data.get("Method")),
            "test_url": str(record_data.get("test_url")),
            "name": str(record_data.get("name")),
            "status_code": str(record_data.get("status_code")),
            "error": str(record_data.get("error")),
        }

    return success_dict, failure_dict


def generate_json_report(json_file_name: str = "default_name") -> Tuple[str, str]:
    """
    輸出測試紀錄 JSON 報告
    Generate JSON report files for test records

    :param json_file_name: 輸出檔案名稱前綴 (Output file name prefix)
    :return: (成功檔案路徑, 失敗檔案路徑)
    """
    lock = Lock()
    success_dict, failure_dict = generate_json()

    success_path = f"{json_file_name}_success.json"
    failure_path = f"{json_file_name}_failure.json"

    try:
        with lock:  # 使用 with 確保自動 acquire/release
            with open(success_path, "w+", encoding="utf-8") as file_to_write:
                json.dump(success_dict, file_to_write, indent=4, ensure_ascii=False)

            with open(failure_path, "w+", encoding="utf-8") as file_to_write:
                json.dump(failure_dict, file_to_write, indent=4, ensure_ascii=False)

        return success_path, failure_path

    except Exception as error:
        print(repr(error), file=sys.stderr)
        return "", ""