Dynamic Package Loading
=======================

The ``PackageManager`` allows you to dynamically import Python packages at runtime and
register all their public functions into the executor's event dictionary.

Basic Usage
-----------

.. code-block:: python

    from je_load_density import executor

    # Load a package and make all its functions available as executor actions
    executor.execute_action([
        ["LD_add_package_to_executor", ["my_custom_package"]]
    ])

After loading, all functions from the package can be called by name in JSON scripts
or via ``executor.execute_action()``.

How It Works
------------

1. Uses ``importlib.util.find_spec()`` to locate the package
2. Imports the package with ``importlib.import_module()``
3. Uses ``inspect.getmembers()`` with ``isfunction`` to find all functions in the package
4. Registers each function into the executor's ``event_dict``

.. note::

    Only top-level functions in the package are registered. Classes, constants, and
    submodules are not automatically added.

PackageManager API
------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Method
     - Description
   * - ``load_package_if_available(package)``
     - Try to import a package. Returns the module or ``None`` if not found.
   * - ``add_package_to_executor(package)``
     - Import a package and register all its functions into the executor.

Example: Using a Custom Package
--------------------------------

Suppose you have a custom package ``my_utils`` with a function ``compute()``:

.. code-block:: python

    from je_load_density import executor

    # Register the package
    executor.execute_action([
        ["LD_add_package_to_executor", ["my_utils"]]
    ])

    # Now you can call compute() by name
    executor.execute_action([
        ["compute", [42]]
    ])

Using in JSON Scripts
---------------------

.. code-block:: json

    [
        ["LD_add_package_to_executor", ["my_utils"]],
        ["compute", [42]]
    ]

Package Gate
------------

``LD_add_package_to_executor`` can load ``os`` or ``subprocess``, so the host program decides which packages it
may load:

.. code-block:: python

    from je_load_density import executor

    executor.allow_packages("my_utils")            # these, and their submodules
    executor.set_allow_arbitrary_packages(False)   # refuse everything else before importing it

Neither switch is an action command, so an action file (or a socket client) cannot open its own gate. A refused
package is never imported; the action's result is a ``LoadDensityTestExecuteException``.
``set_allow_arbitrary_packages(True)`` loads any package without a warning. Until the host calls either switch,
any package still loads but raises a ``DeprecationWarning``; a future release will refuse packages outside the
allowlist by default.
