import sys
from threading import Lock
from typing import List, Tuple

from je_load_density.utils.exception.exceptions import LoadDensityHTMLException
from je_load_density.utils.exception.exception_tags import html_generate_no_data_tag
from je_load_density.utils.test_record.test_record_class import test_record_instance

# HTML 標頭 (HTML head)
_HTML_STRING_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <title>Load Density Report</title>
    <style>
        body { font-size: 100%; }
        h1 { font-size: 2em; }
        .main_table { margin: 0 auto; border-collapse: collapse; width: 75%; font-size: 1.5em; }
        .success_table_head { border: 3px solid #262626; background-color: aqua; font-family: "Times New Roman", sans-serif; text-align: center; }
        .failure_table_head { border: 3px solid #262626; background-color: #f84c5f; font-family: "Times New Roman", sans-serif; text-align: center; }
        .table_data_field_title { border: 3px solid #262626; background-color: #dedede; font-family: "Times New Roman", sans-serif; text-align: center; width: 25%; }
        .table_data_field_text { border: 3px solid #262626; background-color: #dedede; font-family: "Times New Roman", sans-serif; text-align: left; width: 75%; }
        .text { text-align: center; font-family: "Times New Roman", sans-serif; }
    </style>
</head>
<body>
<h1 class="text">Test Report</h1>
""".strip()

# HTML 結尾 (HTML bottom)
_HTML_STRING_BOTTOM = """</body></html>""".strip()

# 成功測試表格模板 (Success table template)
_SUCCESS_TABLE = r"""
<table class="main_table">
<thead>
<tr><th colspan="2" class="success_table_head">Test Report</th></tr>
</thead>
<tbody>
<tr><td class="table_data_field_title">Method</td><td class="table_data_field_text">{Method}</td></tr>
<tr><td class="table_data_field_title">test_url</td><td class="table_data_field_text">{test_url}</td></tr>
<tr><td class="table_data_field_title">name</td><td class="table_data_field_text">{name}</td></tr>
<tr><td class="table_data_field_title">status_code</td><td class="table_data_field_text">{status_code}</td></tr>
<tr><td class="table_data_field_title">text</td><td class="table_data_field_text">{text}</td></tr>
<tr><td class="table_data_field_title">content</td><td class="table_data_field_text">{content}</td></tr>
<tr><td class="table_data_field_title">headers</td><td class="table_data_field_text">{headers}</td></tr>
</tbody>
</table>
<br>
""".strip()

# 失敗測試表格模板 (Failure table template)
_FAILURE_TABLE = r"""
<table class="main_table">
<thead>
<tr><th colspan="2" class="failure_table_head">Test Report</th></tr>
</thead>
<tbody>
<tr><td class="table_data_field_title">http_method</td><td class="table_data_field_text">{http_method}</td></tr>
<tr><td class="table_data_field_title">test_url</td><td class="table_data_field_text">{test_url}</td></tr>
<tr><td class="table_data_field_title">name</td><td class="table_data_field_text">{name}</td></tr>
<tr><td class="table_data_field_title">status_code</td><td class="table_data_field_text">{status_code}</td></tr>
<tr><td class="table_data_field_title">error</td><td class="table_data_field_text">{error}</td></tr>
</tbody>
</table>
<br>
""".strip()


def generate_html() -> Tuple[List[str], List[str]]:
    """
    產生 HTML 片段 (Generate HTML fragments)

    :return: (成功測試清單, 失敗測試清單)
             (list of success test HTML fragments, list of failure test HTML fragments)
    """
    if not test_record_instance.test_record_list and not test_record_instance.error_record_list:
        raise LoadDensityHTMLException(html_generate_no_data_tag)

    success_list: List[str] = [
        _SUCCESS_TABLE.format(
            Method=record.get("Method"),
            test_url=record.get("test_url"),
            name=record.get("name"),
            status_code=record.get("status_code"),
            text=record.get("text"),
            content=record.get("content"),
            headers=record.get("headers"),
        )
        for record in test_record_instance.test_record_list
    ]

    failure_list: List[str] = [
        _FAILURE_TABLE.format(
            http_method=record.get("Method"),
            test_url=record.get("test_url"),
            name=record.get("name"),
            status_code=record.get("status_code"),
            error=record.get("error"),
        )
        for record in test_record_instance.error_record_list
    ]

    return success_list, failure_list


def generate_html_report(html_name: str = "default_name") -> str:
    """
    產生完整 HTML 報告並輸出檔案
    Generate full HTML report and save to file

    :param html_name: 輸出檔案名稱 (Output file name, without extension)
    :return: HTML 字串 (HTML string)
    """
    _lock = Lock()
    success_list, failure_list = generate_html()

    try:
        with _lock:  # 使用 with 確保自動 acquire/release
            html_path = f"{html_name}.html"
            with open(html_path, "w+", encoding="utf-8") as file_to_write:
                file_to_write.write(_HTML_STRING_HEAD)
                file_to_write.writelines(success_list)
                file_to_write.writelines(failure_list)
                file_to_write.write(_HTML_STRING_BOTTOM)
            return html_path
    except Exception as error:
        print(repr(error), file=sys.stderr)
        return ""