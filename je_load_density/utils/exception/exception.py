class LocustNotFoundException(Exception):
    pass


class JELoadingTestException(Exception):
    pass


class JELoadingTestJsonException(JELoadingTestException):
    pass


class JELoadingTestExecuteException(JELoadingTestException):
    pass


class JELoadingAssertException(JELoadingTestException):
    pass
