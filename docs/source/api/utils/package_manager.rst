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

**Global instance:** ``package_manager``
