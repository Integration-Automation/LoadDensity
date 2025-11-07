from pathlib import Path
from typing import Optional

# 定義常數，避免硬編碼
# Define constant to avoid hard-coded string
TEMPLATE_DIR = "je_load_density/template"


def _create_dir(dir_name: str) -> Optional[Path]:
    """
    建立專案目錄
    Create project directory

    :param dir_name: 要建立的目錄名稱 (Directory name to create)
    :return: 成功建立或已存在的 Path 物件 (Path object if created/existed), None if failed
    """
    try:
        path = Path(dir_name)
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as error:
        # 錯誤處理：避免因權限或路徑問題導致程式崩潰
        # Error handling: prevent crash due to permission or path issues
        print(f"Failed to create directory {dir_name}: {error}")
        return None


def create_template_dir() -> Optional[Path]:
    """
    建立模板目錄
    Create template directory

    :return: Path 物件或 None (Path object or None)
    """
    return _create_dir(TEMPLATE_DIR)