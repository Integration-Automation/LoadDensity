import sys

from je_load_density.utils.test_record.record_test_result_class import test_record
from je_load_density.utils.exception.exception import HTMLException
from je_load_density.utils.exception.exception_tag import html_generate_no_data_tag
from threading import Lock

lock = Lock()

_html_string = \
    r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <title>Load Density Report</title>

    <style>
      
        body{{
            font-size: 100%;
        }}

        h1{{
            font-size: 2em;
        }}

        .main_table {{
            margin: 0 auto;
            border-collapse: collapse;
            width: 75%;
            font-size: 1.5em;
        }}

        .success_table_head {{
            border: 3px solid #262626;
            background-color: aqua;
            font-family: "Times New Roman", sans-serif;
            text-align: center;
        }}

        .failure_table_head {{
            border: 3px solid #262626;
            background-color: #f84c5f;
            font-family: "Times New Roman", sans-serif;
            text-align: center;
        }}

        .table_data_field_title {{
            border: 3px solid #262626;
            padding: 0;
            margin: 0;
            background-color: #dedede;
            font-family: "Times New Roman", sans-serif;
            text-align: center;
            width: 25%;
        }}

        .table_data_field_text {{
            border: 3px solid #262626;
            padding: 0;
            margin: 0;
            background-color: #dedede;
            font-family: "Times New Roman", sans-serif;
            text-align: left;
            width: 75%;
        }}

        .text {{
            text-align: center;
            font-family: "Times New Roman", sans-serif;
        }}
    </style>
</head>
<body>
<h1 class="text">
    Test Report
</h1>
{success_table}
{failure_table}
</body>
</html>
""".strip()

_success_table = \
    r"""
   <table class="main_table">
    <thead>
    <tr>
        <th colspan="2" class="success_table_head">Test Report</th>
    </tr>
    </thead>
    <tbody>
    <tr>
        <td class="table_data_field_title">Method</td>
        <td class="table_data_field_text">{Method}</td>
    </tr>
    <tr>
        <td class="table_data_field_title">test_url</td>
        <td class="table_data_field_text">{test_url}</td>
    </tr>
    <tr>
        <td class="table_data_field_title">name</td>
        <td class="table_data_field_text">{name}</td>
    </tr>
    <tr>
        <td class="table_data_field_title">status_code</td>
        <td class="table_data_field_text">{status_code}</td>
    </tr>
    <tr>
        <td class="table_data_field_title">text</td>
        <td class="table_data_field_text">{text}</td>
    </tr>
    <tr>
        <td class="table_data_field_title">content</td>
        <td class="table_data_field_text">{content}</td>
    </tr>
    <tr>
        <td class="table_data_field_title">headers</td>
        <td class="table_data_field_text">{headers}</td>
    </tr>
    </tbody>
</table>
    <br>
    """.strip()

_failure_table = \
    r"""
<table class="main_table">
    <thead>
    <tr>
        <th colspan="2" class="failure_table_head">Test Report</th>
    </tr>
    </thead>
    <tbody>
    <tr>
        <td class="table_data_field_title">http_method</td>
        <td class="table_data_field_text">{http_method}</td>
    </tr>
    <tr>
        <td class="table_data_field_title">test_url</td>
        <td class="table_data_field_text">{test_url}</td>
    </tr>
    <tr>
        <td class="table_data_field_title">name</td>
        <td class="table_data_field_text">{name}</td>
    </tr>
    <tr>
        <td class="table_data_field_title">status_code</td>
        <td class="table_data_field_text">{status_code}</td>
    </tr>
    <tr>
        <td class="table_data_field_title">error</td>
        <td class="table_data_field_text">{error}</td>
    </tr>
    </tbody>
</table>
<br>
    """.strip()


def generate_html(html_name: str = "default_name"):
    """
    format html_string and output html file
    :param html_name: save html file name
    :return: html_string
    """
    if len(test_record.record_list) == 0 and len(test_record.error_record_list) == 0:
        raise HTMLException(html_generate_no_data_tag)
    else:
        success = ""
        for record_data in test_record.record_list:
            success = "".join(
                [
                    success,
                    _success_table.format(
                        Method=record_data.get("http_method"),
                        test_url=record_data.get("test_url"),
                        name=record_data.get("name"),
                        status_code=record_data.get("status_code"),
                        text=record_data.get("text"),
                        content=record_data.get("content"),
                        headers=record_data.get("headers"),
                    )
                ]
            )
        failure = ""
        if len(test_record.error_record_list) == 0:
            pass
        else:
            for record_data in test_record.error_record_list:
                failure = "".join(
                    [
                        failure,
                        _failure_table.format(
                            http_method=record_data[0].get("http_method"),
                            test_url=record_data[0].get("test_url"),
                            name=record_data[0].get("name"),
                            status_code=record_data[0].get("status_code"),
                            error=record_data[0].get("error"),
                        ),
                    ]
                )
        new_html_string = _html_string.format(success_table=success, failure_table=failure)
        try:
            lock.acquire()
            with open(html_name + ".html", "w+") as file_to_write:
                file_to_write.write(
                    new_html_string
                )
        except Exception as error:
            print(repr(error), file=sys.stderr)
        finally:
            lock.release()
    return new_html_string
