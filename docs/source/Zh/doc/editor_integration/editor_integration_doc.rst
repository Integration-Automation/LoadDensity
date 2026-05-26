編輯器與 CI 整合
================

概觀
----

LoadDensity 附帶一組整合工具,讓寫 action JSON 的人享有與 app 開發者
同等的迴授:

* **Action JSON linter** — 5 條規則(unknown LD_*、hardcoded URL、
  missing tasks、oversize body、invalid shape)
* **JSON Schema 匯出** — Draft 2020-12,列舉所有 ``LD_*`` 指令
* **LSP server** — stdio 上的 completion + diagnostics
* **VS Code 擴充套件骨架** — 包裝 LSP,VS Code 1.85+
* **Composite GitHub Action** — install、lint、run、annotate
* **pre-commit hook** — commit 前 lint 每個 action JSON

Linter
------

.. code-block:: python

    from je_load_density import lint_action, lint_action_file

    findings = lint_action({"load_density": [["LD_typo"]]})

規則:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 規則
     - 說明
   * - ``unknown-command``
     - ``LD_*`` 名稱未在 executor 註冊
   * - ``hardcoded-url``
     - 裸 ``http(s)://`` URL,未帶 ``${...}`` 佔位符
   * - ``missing-tasks``
     - ``LD_start_test`` 缺 ``tasks``
   * - ``oversize-body``
     - 請求 body > 1 MiB(通常是 fixture 弄錯)
   * - ``invalid-shape``
     - 動作文件非 list 或 ``{load_density: [...]}``

JSON Schema
-----------

.. code-block:: python

    from je_load_density import action_json_schema, export_schema

    schema = action_json_schema()
    export_schema("docs/reference/loaddensity-action-schema.json")

把產出的檔案放到 IDE 的 JSON Schema 設定即可獲得 ``LD_*`` 指令名稱的
hover 文件與自動補完。

LSP server
----------

.. code-block:: bash

    python -m je_load_density.action_lsp   # 或: loaddensity-lsp

實作 LSP 3.17 子集,VS Code、JetBrains LSP、Neovim 皆可使用:

* ``initialize`` / ``initialized`` / ``shutdown`` / ``exit``
* ``textDocument/didOpen`` / ``didChange``(整檔同步)
* ``textDocument/publishDiagnostics``(每次變更跑 linter)
* ``textDocument/completion``(所有 ``LD_*`` 指令)

VS Code 擴充套件
----------------

``editors/vscode/`` 內含最小擴充套件,以 stdio 啟動 LSP:

.. code-block:: bash

    cd editors/vscode
    npm install
    npm run package
    code --install-extension loaddensity-0.1.0.vsix

設定鍵:

* ``loaddensity.python`` — 啟動 LSP 的 Python 直譯器
* ``loaddensity.lspArgs`` — 傳給直譯器的引數

GitHub Action
-------------

repo 根目錄的 ``action.yml`` 是 composite Action:

.. code-block:: yaml

    - uses: ./   # 或: Integration-Automation/LoadDensity@v1
      with:
        action-file: actions/smoke.json
        python-version: "3.11"
        extras: "metrics,websocket"
        fail-on-error: "true"

執行步驟:

#. 安裝指定的 Python
#. ``pip install je_load_density[extras]``
#. lint action JSON,失敗以檔案路徑帶 ``::error::``
#. 用 CLI 執行 action JSON
#. 對每個失敗紀錄輸出 GitHub annotation;``fail-on-error=true``
   時整個 job 視為失敗

pre-commit hook
---------------

``.pre-commit-hooks.yaml`` 提供 ``loaddensity-lint`` hook:

.. code-block:: yaml

    - repo: https://github.com/Integration-Automation/LoadDensity
      rev: v1.0.0
      hooks:
        - id: loaddensity-lint
          files: '\.(json|action\.json)$'

hook 會對每個 staged 路徑呼叫 ``python -m je_load_density.tools.lint_files``;
不存在的檔案會被靜默跳過,error 嚴重度的 finding 會讓 commit 失敗。
