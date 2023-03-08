class LocustNotFoundException(Exception):
    pass


class LoadDensityTestException(Exception):
    pass

# json
class LoadDensityTestJsonException(LoadDensityTestException):
    pass

class LoadDensityGenerateJsonReportException(LoadDensityTestException):
    pass


class LoadDensityTestExecuteException(LoadDensityTestException):
    pass


class LoadDensityAssertException(LoadDensityTestException):
    pass


class LoadDensityHTMLException(LoadDensityTestException):
    pass


class LoadDensityAddCommandException(LoadDensityTestException):
    pass

