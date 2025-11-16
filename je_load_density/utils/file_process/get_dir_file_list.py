from pathlib import Path
from typing import List


def get_dir_files_as_list(
    dir_path: str = str(Path.cwd()),
    default_search_file_extension: str = ".json"
) -> List[str]:
    """
    取得指定目錄下所有符合副檔名的檔案清單
    Get all files in a directory that end with the given extension

    :param dir_path: 要搜尋的目錄路徑 (Directory path to search)
    :param default_search_file_extension: 要搜尋的副檔名 (File extension to search, e.g. ".json")
    :return: 檔案絕對路徑清單 (List of absolute file paths)
    """
    try:
        path_obj = Path(dir_path)
        if not path_obj.exists() or not path_obj.is_dir():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        return [
            str(file.resolve())
            for file in path_obj.rglob(f"*{default_search_file_extension.lower()}")
        ]
    except Exception as error:
        print(f"Error while scanning directory {dir_path}: {error}")
        return []