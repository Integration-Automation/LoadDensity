Editor & CI Integration
=======================

Overview
--------

LoadDensity ships a stack of small integrations so action JSON authors
get the same feedback loop as application developers:

* **Action JSON linter** — 5 rules (unknown LD_*, hardcoded URLs,
  missing tasks, oversize bodies, invalid shape).
* **JSON Schema export** — Draft 2020-12 schema enumerating every
  registered ``LD_*`` command.
* **LSP server** — completion + diagnostics over stdio.
* **VS Code extension skeleton** — wraps the LSP for VS Code 1.85+.
* **Composite GitHub Action** — install, lint, run, annotate.
* **pre-commit hook** — lint every action JSON before commit.

Linter
------

.. code-block:: python

    from je_load_density import lint_action, lint_action_file

    findings = lint_action({"load_density": [["LD_typo"]]})
    # [{'rule': 'unknown-command', 'severity': 'error', 'message': ...}]

    file_findings = lint_action_file("actions/smoke.json")

Rules:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Rule
     - Description
   * - ``unknown-command``
     - ``LD_*`` name not registered in the executor.
   * - ``hardcoded-url``
     - Bare ``http(s)://`` URL without a ``${...}`` placeholder.
   * - ``missing-tasks``
     - ``LD_start_test`` without a ``tasks`` key.
   * - ``oversize-body``
     - Request body > 1 MiB (likely a fixture mistake).
   * - ``invalid-shape``
     - Action document is not a list / ``{load_density: [...]}``.

JSON Schema
-----------

.. code-block:: python

    from je_load_density import action_json_schema, export_schema

    schema = action_json_schema()
    export_schema("docs/reference/loaddensity-action-schema.json")

Drop the resulting file into your IDE's JSON Schema configuration to
get hover docs + auto-completion for ``LD_*`` command names.

LSP server
----------

.. code-block:: bash

    python -m je_load_density.action_lsp   # or: loaddensity-lsp

Implements the LSP 3.17 subset needed for VS Code, JetBrains LSP, and
Neovim:

* ``initialize`` / ``initialized`` / ``shutdown`` / ``exit``
* ``textDocument/didOpen`` / ``didChange`` (full document sync)
* ``textDocument/publishDiagnostics`` (linter on every change)
* ``textDocument/completion`` (every registered ``LD_*`` command)

VS Code extension
-----------------

``editors/vscode/`` contains a minimal extension that launches the LSP
over stdio.

.. code-block:: bash

    cd editors/vscode
    npm install
    npm run package
    code --install-extension loaddensity-0.1.0.vsix

Configuration keys:

* ``loaddensity.python`` — Python interpreter to launch the LSP.
* ``loaddensity.lspArgs`` — args passed to the interpreter.

GitHub Action
-------------

``action.yml`` at the repo root is a composite Action:

.. code-block:: yaml

    - uses: ./   # or: Integration-Automation/LoadDensity@v1
      with:
        action-file: actions/smoke.json
        python-version: "3.11"
        extras: "metrics,websocket"
        fail-on-error: "true"

Steps:

#. Install the requested Python.
#. ``pip install je_load_density[extras]``.
#. Lint the action JSON; ``::error::`` lines on file path.
#. Run the action JSON via the CLI.
#. Emit per-failure GitHub annotations; fail the job when any failure
   exists (if ``fail-on-error`` is ``true``).

pre-commit hook
---------------

``.pre-commit-hooks.yaml`` ships the ``loaddensity-lint`` hook:

.. code-block:: yaml

    - repo: https://github.com/Integration-Automation/LoadDensity
      rev: v1.0.0
      hooks:
        - id: loaddensity-lint
          files: '\.(json|action\.json)$'

The hook calls ``python -m je_load_density.tools.lint_files`` against
every staged path; missing files are silently skipped, error-severity
findings fail the commit.
