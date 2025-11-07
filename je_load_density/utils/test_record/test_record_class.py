from typing import List, Dict


class TestRecord:
    """
    測試紀錄類別
    Test record class

    用來保存成功與失敗的測試紀錄。
    Used to store success and failure test records.
    """

    def __init__(self) -> None:
        # 成功測試紀錄 (Success test records)
        self.test_record_list: List[Dict] = []
        # 失敗測試紀錄 (Failure test records)
        self.error_record_list: List[Dict] = []

    def clear_records(self) -> None:
        """
        清除所有測試紀錄
        Clear all test records
        """
        self.test_record_list.clear()
        self.error_record_list.clear()


# 建立全域測試紀錄實例
# Create global test record instance
test_record_instance = TestRecord()