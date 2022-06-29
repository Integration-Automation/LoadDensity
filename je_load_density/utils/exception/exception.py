class LocustNotFoundException(Exception):
    pass


class LoadDensityTestException(Exception):
    pass


class LoadDensityTestJsonException(LoadDensityTestException):
    pass


class LoadDensityTestExecuteException(LoadDensityTestException):
    pass


class LoadDensityAssertException(LoadDensityTestException):
    pass


class LoadDensityHTMLException(LoadDensityTestException):
    pass


class LoadDensityAddCommandException(LoadDensityTestException):
    pass
