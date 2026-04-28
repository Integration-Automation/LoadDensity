例外
====

階層
----

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

何時該攔截何者
--------------

* ``LoadDensityTestExecuteException`` — 動作 JSON 結構錯誤，或引用不存在的指令。攔截以呈現使用者輸入錯誤，不致掩蓋內部錯誤。
* ``LoadDensityHTMLException`` / ``LoadDensityGenerateJsonReportException`` — 在沒有紀錄時呼叫報告產生器（記憶體 store 為空）。
* ``LoadDensityAssertException`` — 預留給斷言層；目前 HTTP 斷言會經由 Locust 將 request 標為 fail 而非拋出。
* ``XMLException`` / ``XMLTypeException`` — XML 格式錯誤或未預期 payload 結構。
* ``CallbackExecutorException`` — callback executor 收到錯誤的 trigger 或 function。
* ``LoadDensityAddCommandException`` — ``add_command_to_executor`` 收到非 callable。

所有自訂例外皆繼承自 ``LoadDensityTestException``，攔截該類別即可達成全面錯誤處理。
