==================
LoadDensity
==================

**A multi-protocol load and stress automation framework built on Locust**

LoadDensity (``je_load_density``) wraps Locust with a JSON-driven action
executor and adds first-class support for HTTP, WebSocket, gRPC, MQTT,
and raw TCP/UDP user templates. Every executor command has a
deterministic name (``LD_*``) and a single dispatch point, so an action
JSON can mix protocols, parameterised data, scenario flow, reports, and
metrics exporters in the same script.

* **PyPI**: https://pypi.org/project/je_load_density/
* **GitHub**: https://github.com/Integration-Automation/LoadDensity
* **License**: MIT

----

The documentation is split by language and by content type. Each
language manual is organised into chapters (Getting Started, Core API,
Actions, User Templates, Reporting, Orchestration, Recording & Data,
Tooling, Integrations, Reference); the API book holds the
auto-generated Python reference.

.. toctree::
   :maxdepth: 2
   :caption: English manual

   En/en_index.rst

.. toctree::
   :maxdepth: 2
   :caption: 繁體中文手冊

   Zh/zh_index.rst

.. toctree::
   :maxdepth: 2
   :caption: API reference

   api/api_index.rst

----

RoadMap
-------

* Project Kanban: https://github.com/orgs/Integration-Automation/projects
