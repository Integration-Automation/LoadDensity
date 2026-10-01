Package Manager API
===================

The ``PackageManager`` class provides dynamic package loading and registration into
the executor's event dictionary.

PackageManager Class
--------------------

.. code-block:: python

    class PackageManager:
        installed_package_dict: dict[str, Any]
        executor: Optional[Any]

        def load_package_if_available(self, package: str) -> Optional[Any]: ...
        def add_package_to_executor(self, package: str) -> None: ...
        def allow_packages(self, *packages: str) -> None: ...
        def set_allow_arbitrary_packages(self, enabled: bool) -> None: ...

load_package_if_available()
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Try to import a package and cache it.

.. code-block:: python

    def load_package_if_available(self, package: str) -> Optional[Any]

**Parameters:**

* ``package`` — Package name to import

**Returns:** The imported module, or ``None`` if the package cannot be found.

Uses ``importlib.util.find_spec()`` to locate the package and ``importlib.import_module()``
to import it. Successfully imported packages are cached in ``installed_package_dict``.

add_package_to_executor()
~~~~~~~~~~~~~~~~~~~~~~~~~

Import a package and register all its functions into the executor's ``event_dict``.

.. code-block:: python

    def add_package_to_executor(self, package: str) -> None

**Parameters:**

* ``package`` — Package name to load and register

Uses ``inspect.getmembers()`` with ``isfunction`` predicate to find all functions
in the package.

**Raises:** ``LoadDensityTestExecuteException`` when the package gate refuses ``package``
(nothing is imported).

allow_packages() / set_allow_arbitrary_packages()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The package gate's switches. ``allow_packages`` adds packages, and their submodules, to the
allowlist; ``set_allow_arbitrary_packages`` allows (``True``) or refuses (``False``) everything
else. Until either is called, any package loads with a ``DeprecationWarning``. ``Executor`` has
the same two static methods; neither is an action command.

**Global instance:** ``package_manager``
