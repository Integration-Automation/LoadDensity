from je_load_density.utils.test_record.test_record_class import TestRecord


class TestTestRecord:

    def test_init_empty(self):
        record = TestRecord()
        assert record.test_record_list == []
        assert record.error_record_list == []

    def test_append_records(self):
        record = TestRecord()
        record.test_record_list.append({"Method": "GET", "status_code": "200"})
        record.error_record_list.append({"Method": "POST", "error": "timeout"})
        assert len(record.test_record_list) == 1
        assert len(record.error_record_list) == 1

    def test_clear_records(self):
        record = TestRecord()
        record.test_record_list.append({"a": 1})
        record.error_record_list.append({"b": 2})
        record.clear_records()
        assert record.test_record_list == []
        assert record.error_record_list == []
