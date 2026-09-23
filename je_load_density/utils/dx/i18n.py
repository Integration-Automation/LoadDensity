"""
Localized error / message resolver.

Translates well-known LoadDensity error keys into one of the supported
locales. Falls back to English if the key (or locale) is not found.
"""

import os
from typing import Dict, Optional


_MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "cant_find_json": "Cannot find action JSON file.",
        "cant_save_json": "Cannot save action JSON file.",
        "missing_user_type": "Unsupported user type.",
        "missing_locust": "Locust is required to run start_test.",
        "missing_extra": "Optional dependency not installed.",
    },
    "zh-TW": {
        "cant_find_json": "找不到 action JSON 檔案。",
        "cant_save_json": "無法儲存 action JSON 檔案。",
        "missing_user_type": "不支援的 user type。",
        "missing_locust": "需要 Locust 才能呼叫 start_test。",
        "missing_extra": "選用相依套件尚未安裝。",
    },
    "zh-CN": {
        "cant_find_json": "找不到 action JSON 文件。",
        "cant_save_json": "无法保存 action JSON 文件。",
        "missing_user_type": "不支持的 user type。",
        "missing_locust": "需要 Locust 才能调用 start_test。",
        "missing_extra": "可选依赖尚未安装。",
    },
    "ja": {
        "cant_find_json": "アクション JSON ファイルが見つかりません。",
        "cant_save_json": "アクション JSON ファイルを保存できません。",
        "missing_user_type": "サポートされていない user type です。",
        "missing_locust": "start_test を呼ぶには Locust が必要です。",
        "missing_extra": "オプション依存パッケージがインストールされていません。",
    },
    "ko": {
        "cant_find_json": "action JSON 파일을 찾을 수 없습니다.",
        "cant_save_json": "action JSON 파일을 저장할 수 없습니다.",
        "missing_user_type": "지원되지 않는 user type 입니다.",
        "missing_locust": "start_test 호출에는 Locust 가 필요합니다.",
        "missing_extra": "선택적 의존성이 설치되지 않았습니다.",
    },
}


def get_current_locale() -> str:
    """Return the operator's chosen locale (default English)."""
    return os.environ.get("LD_LOCALE", "en")


def t(key: str, locale: Optional[str] = None) -> str:
    """Translate a message key."""
    locale_value = locale or get_current_locale()
    table = _MESSAGES.get(locale_value) or _MESSAGES["en"]
    return table.get(key) or _MESSAGES["en"].get(key) or key


def available_locales() -> list:
    """Return the supported locale codes."""
    return sorted(_MESSAGES.keys())
