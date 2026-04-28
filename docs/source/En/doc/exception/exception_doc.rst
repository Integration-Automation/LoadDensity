Exceptions
==========

Hierarchy
---------

::

    Exception
    └── LocustNotFoundException
    └── LoadDensityTestException
        ├── LoadDensityTestJsonException
        ├── LoadDensityGenerateJsonReportException
        ├── LoadDensityTestExecuteException
        ├── LoadDensityAssertException
        ├── LoadDensityHTMLException
        ├── LoadDensityAddCommandException
        ├── XMLException
        │   └── XMLTypeException
        └── CallbackExecutorException

When to catch what
------------------

* ``LoadDensityTestExecuteException`` — Action JSON shape is wrong, or
  an unknown command was referenced. Catch this to surface user-input
  errors without crashing on internal exceptions.
* ``LoadDensityHTMLException`` /
  ``LoadDensityGenerateJsonReportException`` — Report generation ran
  with no records (in-memory store empty).
* ``LoadDensityAssertException`` — Reserved for future use by the
  assertions layer; HTTP assertions today fail the request via Locust
  rather than raise.
* ``XMLException`` / ``XMLTypeException`` — Malformed XML or unexpected
  payload shape in the XML utilities.
* ``CallbackExecutorException`` — The callback executor was given an
  invalid trigger or function reference.
* ``LoadDensityAddCommandException`` — ``add_command_to_executor`` was
  passed a non-callable.

All custom exceptions inherit from ``LoadDensityTestException``, so
catching that one class is enough for blanket error handling.
