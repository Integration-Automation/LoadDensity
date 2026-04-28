Parameter Resolver
==================

Overview
--------

The parameter resolver expands ``${...}`` placeholders inside any
nested string / list / dict structure. It is invoked automatically on
every task before the user template touches it, so values flow
seamlessly between actions.

Supported placeholders
----------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Placeholder
     - Resolves to
   * - ``${var.NAME}``
     - The value passed to ``register_variable`` / ``register_variables``.
   * - ``${env.NAME}``
     - Environment variable ``NAME``.
   * - ``${csv.SOURCE.COLUMN}``
     - The next row from CSV source ``SOURCE`` (cycles by default).
   * - ``${faker.METHOD}``
     - Calls ``Faker().METHOD()`` (lazy import, optional dependency).
   * - ``${uuid()}``
     - A new UUID 4 string.
   * - ``${now()}``
     - Local time in ISO-8601 (seconds resolution).
   * - ``${randint(min, max)}``
     - Cryptographically-strong random int in ``[min, max]``.

Unknown placeholders are left in place so missing data is visible
during a dry run.

Registering data
----------------

.. code-block:: python

    from je_load_density import (
        register_variable, register_variables,
        register_csv_source, register_csv_sources,
    )

    register_variable("base", "https://api.example.com")
    register_variables({"token": "abc", "tenant": "acme"})

    register_csv_source("users", "users.csv")            # cycles
    register_csv_sources([
        {"name": "products", "file_path": "products.csv", "cycle": False},
    ])

CSV files must have a header row. Each call to ``${csv.name.col}``
returns the value at column ``col`` from the next row.

Action-JSON usage
-----------------

The same APIs are available through the executor so an entire run can
be parameterised from JSON:

.. code-block:: json

    {"load_density": [
      ["LD_register_variables", {"variables": {"base": "https://api.example.com"}}],
      ["LD_register_csv_sources", {"sources": [
        {"name": "users", "file_path": "users.csv"}
      ]}],
      ["LD_start_test", {
        "user_detail_dict": {"user": "fast_http_user"},
        "tasks": [{
          "method": "post",
          "request_url": "${var.base}/login",
          "json": {"email": "${csv.users.email}", "password": "${csv.users.password}"}
        }]
      }]
    ]}

Extracting values from responses
--------------------------------

HTTP tasks may declare ``extract`` rules; matching values are written
back into the resolver under the chosen variable name:

.. code-block:: json

    {
      "method": "post",
      "request_url": "${var.base}/login",
      "json": {"email": "u@example.com", "password": "secret"},
      "extract": [
        {"var": "auth_token", "from": "json_path", "path": "data.token"},
        {"var": "request_id", "from": "header", "name": "X-Request-Id"},
        {"var": "status", "from": "status_code"}
      ]
    }

Subsequent tasks can read ``${var.auth_token}`` straight from the
resolver.

Clearing
--------

Call ``parameter_resolver.clear()`` (or ``LD_clear_resolver``) between
runs to discard accumulated state.
