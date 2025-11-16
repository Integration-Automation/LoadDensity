import sys
from threading import Lock
from xml.dom.minidom import parseString
from typing import Tuple

from je_load_density.utils.generate_report.generate_json_report import generate_json
from je_load_density.utils.xml.change_xml_structure.change_xml_structure import dict_to_elements_tree


def generate_xml() -> Tuple[str, str]:
    """
    產生 XML 字串 (Generate XML strings)

    :return: (成功測試 XML 字串, 失敗測試 XML 字串)
             (success_xml_str, failure_xml_str)
    """
    success_dict, failure_dict = generate_json()

    # 包裝成 xml_data 根節點 (Wrap into xml_data root node)
    success_dict = {"xml_data": success_dict}
    failure_dict = {"xml_data": failure_dict}

    success_xml_str = dict_to_elements_tree(success_dict)
    failure_xml_str = dict_to_elements_tree(failure_dict)

    return success_xml_str, failure_xml_str


def generate_xml_report(xml_file_name: str = "default_name") -> Tuple[str, str]:
    """
    輸出 XML 報告檔案 (Generate XML report files)

    :param xml_file_name: 輸出檔案名稱前綴 (Output file name prefix)
    :return: (成功檔案路徑, 失敗檔案路徑)
    """
    success_xml_str, failure_xml_str = generate_xml()

    # 使用 minidom 美化輸出 (Pretty print XML using minidom)
    success_xml = parseString(success_xml_str).toprettyxml()
    failure_xml = parseString(failure_xml_str).toprettyxml()

    lock = Lock()
    success_path = f"{xml_file_name}_success.xml"
    failure_path = f"{xml_file_name}_failure.xml"

    try:
        with lock:  # 使用 with 確保自動 acquire/release
            with open(failure_path, "w+", encoding="utf-8") as file_to_write:
                file_to_write.write(failure_xml)

            with open(success_path, "w+", encoding="utf-8") as file_to_write:
                file_to_write.write(success_xml)

        return success_path, failure_path

    except Exception as error:
        print(repr(error), file=sys.stderr)
        return "", ""