from je_load_density.utils.exception.exceptions import (
    LoadDensityTestException,
    LoadDensityTestJsonException,
    LoadDensityGenerateJsonReportException,
    LoadDensityTestExecuteException,
    LoadDensityHTMLException,
    CallbackExecutorException,
    XMLException,
    XMLTypeException,
)


class TestExceptionHierarchy:

    def test_json_exception_is_subclass(self):
        assert issubclass(LoadDensityTestJsonException, LoadDensityTestException)

    def test_json_report_exception_is_subclass(self):
        assert issubclass(LoadDensityGenerateJsonReportException, LoadDensityTestException)

    def test_execute_exception_is_subclass(self):
        assert issubclass(LoadDensityTestExecuteException, LoadDensityTestException)

    def test_html_exception_is_subclass(self):
        assert issubclass(LoadDensityHTMLException, LoadDensityTestException)

    def test_callback_exception_is_subclass(self):
        assert issubclass(CallbackExecutorException, LoadDensityTestException)

    def test_xml_exception_is_subclass(self):
        assert issubclass(XMLException, LoadDensityTestException)

    def test_xml_type_exception_is_subclass(self):
        assert issubclass(XMLTypeException, XMLException)

    def test_exception_message(self):
        err = LoadDensityTestJsonException("test error message")
        assert str(err) == "test error message"
