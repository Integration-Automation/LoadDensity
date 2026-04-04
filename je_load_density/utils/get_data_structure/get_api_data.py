import requests
import requests.exceptions
from typing import Union, Dict


def get_api_response_data(
    response: requests.Response,
    start_time: Union[str, float, int],
    end_time: Union[str, float, int]
) -> Dict[str, Union[str, int, dict, bytes]]:
    """
    使用 requests.Response 建立測試資料字典
    Create a data dictionary from requests.Response

    :param response: requests response 物件 (requests response object)
    :param start_time: 測試開始時間 (test start time)
    :param end_time: 測試結束時間 (test end time)
    :return: 包含以下欄位的字典 (dictionary including):
        - status_code
        - text
        - content
        - headers
        - encoding
        - cookies
        - elapsed
        - history
        - request_method
        - request_url
        - request_body
        - start_time
        - end_time
        - json (if status_code == 200 and response.json() is valid)
    """
    response_data: Dict[str, Union[str, int, dict, bytes]] = {
        "status_code": response.status_code,
        "text": response.text,
        "content": response.content,
        "headers": dict(response.headers),
        "encoding": response.encoding,
        "cookies": response.cookies.get_dict(),
        "elapsed": response.elapsed.total_seconds() if response.elapsed else None,
        "history": [r.url for r in response.history] if response.history else [],
        "request_method": response.request.method,
        "request_url": response.request.url,
        "request_body": response.request.body,
        "start_time": start_time,
        "end_time": end_time,
    }

    # 嘗試解析 JSON (Try parsing JSON)
    try:
        if response.status_code == 200:
            response_data["json"] = response.json()
        else:
            response_data["json"] = None
    except (requests.exceptions.JSONDecodeError, ValueError):
        response_data["json"] = None

    return response_data