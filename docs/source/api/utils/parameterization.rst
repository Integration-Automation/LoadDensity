Parameter Resolver API
======================

The parameter resolver expands ``${...}`` placeholders inside any
nested string / list / dict structure. It is invoked automatically on
every task before the user template touches it, so values flow
seamlessly between actions.

Resolver
--------

.. code-block:: python

    from je_load_density import parameter_resolver, resolve

    parameter_resolver.set_variable("base", "https://api.example.com")
    parameter_resolver.set_variables({"token": "abc", "tenant": "acme"})
    parameter_resolver.add_csv_source("users", "users.csv")
    parameter_resolver.clear()

    expanded = resolve({"url": "${var.base}/login", "id": "${uuid()}"})

Public helpers
--------------

.. code-block:: python

    from je_load_density import (
        register_variable, register_variables,
        register_csv_source, register_csv_sources,
        resolve,
    )

    register_variable("base", "https://api.example.com")
    register_variables({"tenant": "acme", "token": "abc"})

    register_csv_source("users", "users.csv")
    register_csv_sources([
        {"name": "products", "file_path": "products.csv", "cycle": False},
    ])

    payload = resolve({
        "url": "${var.base}/login",
        "json": {"email": "${csv.users.email}",
                 "password": "${csv.users.password}"},
    })

Supported placeholders
----------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Placeholder
     - Resolves to
   * - ``${var.NAME}``
     - Value passed to ``register_variable(s)``.
   * - ``${env.NAME}``
     - Environment variable ``NAME``.
   * - ``${csv.SOURCE.COLUMN}``
     - Next row of CSV source ``SOURCE`` (cycles by default).
   * - ``${faker.METHOD}``
     - Calls ``Faker().METHOD()`` (lazy import).
   * - ``${uuid()}``
     - New UUID 4 string.
   * - ``${now()}``
     - Local ISO-8601 timestamp (seconds).
   * - ``${randint(min, max)}``
     - Cryptographically-strong random int in ``[min, max]``.

Extractors
----------

Tasks may declare ``extract`` rules; matching values are written back
into the resolver under the chosen variable name. Sources:
``json_path``, ``header``, ``status_code``.

.. code-block:: json

    {
      "method": "post",
      "request_url": "${var.base}/login",
      "extract": [
        {"var": "auth_token", "from": "json_path", "path": "data.token"},
        {"var": "request_id", "from": "header",    "name": "X-Request-Id"}
      ]
    }

Subsequent tasks can read ``${var.auth_token}`` straight from the
resolver.

Action-JSON commands
--------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Command
     - Summary
   * - ``LD_register_variable`` / ``LD_register_variables``
     - Register one or many ``${var.x}`` values.
   * - ``LD_register_csv_source`` / ``LD_register_csv_sources``
     - Bind a CSV file to a ``${csv.name.col}`` source.
   * - ``LD_clear_resolver``
     - Reset every registered variable / source.
