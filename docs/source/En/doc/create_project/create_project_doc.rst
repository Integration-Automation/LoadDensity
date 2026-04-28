Create Project
==============

Overview
--------

``create_project_dir`` (CLI: ``je_load_density init``) scaffolds a
LoadDensity project skeleton at a chosen path. The skeleton contains
a sample action JSON, a runner script, and a placeholder for assets.

Python API
----------

.. code-block:: python

    from je_load_density import create_project_dir
    create_project_dir("./my_load_test")

CLI
---

.. code-block:: bash

    python -m je_load_density init ./my_load_test

Layout
------

::

    my_load_test/
    ├── run.py                 # tiny runner that reads the action JSON
    └── action.json            # sample action JSON

After scaffolding, edit ``action.json`` (see
:doc:`../action_executor/action_executor_doc`) and run::

    python run.py

or::

    python -m je_load_density run action.json
