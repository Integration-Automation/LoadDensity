# 程式審核：LoadDensity

審核者＝工作區程式審核；日期＝2026-10-22；對象＝`LoadDensity`；結論＝需修正。

## 審核者

工作區程式審核。日期 2026-10-22。對象為工作樹 `D:\Codes\LoadDensity` 的套件 `je_load_density`（Locust 負載測試）。本輪是熱點審核，不是全庫逐函式評分。

## 審核規範

共通規範在工作區 repo [JE-Chen/Codes](https://github.com/JE-Chen/Codes) 的 `docs/code-review-standard.md`。下面留下 2026-10-22 這次審核所用的條款，讓審核紀錄的依據對得上那一次。之後的審核以工作區那份為準。本專案更嚴的條款仍以本節與本專案的 `CLAUDE.md` 為準。

1. 設計：目標 URL 進入 Locust 的路徑必須與公開契約一致；換 engine 不得靜默改打別的主機。
2. 可讀性：認知複雜度 ≤ 15、函式 ≤ 80 行、巢狀 ≤ 4、參數 ≤ 7、行寬 ≤ 120；專案更嚴者從嚴。
3. 錯誤處理：不使用裸 `except:`；對外失敗要留下可辨識原因，不得默吞後繼續打錯目標。
4. 死碼：寫入後無人讀取、且會讓呼叫端以為已生效的設定，視同缺陷或建議。
5. 型別與 docstring：公開進入點要能看出 host 與 `request_url` 誰贏。
6. 安全：不對不受信任輸入使用 `eval`／`exec`／`pickle`／`yaml.load`；`subprocess` 只用參數列表；不把密文寫進日誌；`urlopen` 要限制方案。
7. 測試：熱點應有契約測試；本輪不執行測試、不啟動 Locust、不對任何主機施壓。
8. 效能：匯入套件不得連外；Locust、gevent 修補與請求掛鉤只在選到 Locust 路徑時發生。
9. §6：APITestka 的絕對 `request_url`、隱藏舊旗標、Python 專用套件閘門開關不得被 action 檔打開。
10. 文件同步：`architecture.md`、套件 docstring 與實際匯入行為必須一致。

嚴重度：缺陷（必須修）、建議（應修，尚無立即損害）、備註（已核對，不是缺陷）。通過＝無未關閉缺陷；有條件通過＝無立即損害；需修正＝有未關閉缺陷。

## 審核紀錄

### 方法

已讀 `architecture.md`、`CLAUDE.md`、`progress.md` 前 80 行，並對照 §6 後半與 HTTP 使用者文件。搜尋範圍是 `je_load_density/**/*.py`，排除 `test/`、`build/`、`dist/`、`__pycache__/` 與文件產生物。關鍵字含 `eval(`、`exec(`、`shell=True`、`pickle`、`yaml.load`、`verify=False`、裸 `except:`、`subprocess`，並沿目標 URL、套件閘門與匯入副作用往下讀到實際呼叫點。每一則發現都對過來源，沒有只靠搜尋命中。

### 發現

#### CR-01

- 位置：`je_load_density/wrapper/start_wrapper/locust_start.py` 第 282–286 行；寫入位置為 `je_load_density/utils/logging/loggin_instance.py` 第 75–102 行。
- 說明：Locust 路徑的 `start_test` 在 INFO 把整個 `user_detail_dict` 與 `**kwargs`（含 `tasks`、`variables`、`connection`、`db_sources`）寫進日誌。動作裡的 password、bearer token、`Authorization` 與連線字串會原樣出現。檔案處理器等級是 INFO，路徑是 `~/.je_load_density/logs/LoadDensity.log`（或 `LOAD_DENSITY_LOG_FILE`），同帳號各程序共用、延遲開啟、超過 10MB 才輪替一份 `.1`。stderr 只收 WARNING，所以桌面工作程序把 stdout／stderr 轉走並不能擋住這筆。公開 `start_test` 與 `LD_start_test` 都經 `engine/entrypoints.py` 進入這條 Locust 實作。
- 依據：規範 6；`architecture.md` §7「never log secrets」；`CLAUDE.md` 安全節不得記錄 token 或含憑證的請求本文。
- 狀態：未關閉。缺陷。
- 建議：啟動日誌只留使用者類型、人數、spawn、時間、runner 與 engine。任務本文、標頭、變數、連線與資料庫來源改為不記錄，或先去掉憑證欄位。既有日誌檔裡已寫入的內容需由操作者自行清除，程式無法追溯。

#### CR-02

- 位置：`je_load_density/wrapper/user_template/http_user_template.py` 第 28–38、55–60 行；`fast_http_user_template.py` 第 28–38 行；`async_http_user_template.py` 第 38–66、107–118 行；`wrapper/user_template/request_executor.py` 第 169–190 行；`wrapper/proxy/user/http_user_proxy.py` 第 19–33 行；`engine/entrypoints.py` 第 41–56 行；`engine/async_http.py` 第 84–93 行。
- 說明：Locust HTTP／FastHTTP 的目標是任務的 `request_url` 或 `url`，經參數展開後直接交給 `client.get`／`post` 等。絕對 URL 就是被打的主機，與 §6 的 APITestka 契約及桌面表單一致（`gui/main_widget.py` 第 144–148 行要求 http(s) 且有 hostname；`gui/run_worker.py` 第 102–104 行把該 URL 放進任務）。相對路徑則只相對於類別常數 `host = "http://localhost"`。setter 的 `host` 會進 proxy，HTTP 範本卻不讀 `default_host`。`user_detail_dict["host"]` 也不會寫進 Locust `Environment`。原生 asyncio 反而用 `user_detail_dict` 的 `host`／`base_url` 做 `urljoin`。同一個 `start_test`、相對路徑、字典裡帶了 host 時，Locust 打向 localhost，asyncio 打向字典裡的主機。HTTPX 範本建立 `httpx.Client` 時也沒有 `base_url`，相對路徑不會套用類別 host。
- 依據：規範 1、4、5、9。文件 `docs/source/En/doc/http_users/http_users_doc.rst` 寫相對 `host`，但沒有說明這個 host 是類別常數，也不是 `start_test` 的 host 參數。
- 狀態：未關閉。建議。絕對 `request_url` 這條主路徑仍然打到呼叫端給的 URL，所以不算立即打錯已宣告的絕對目標。
- 建議：Locust HTTP／FastHTTP／HTTPX 若收到 setter `host` 或 `user_detail_dict["host"]`，應把它設成該次使用者的 base，步驟裡的絕對 URL 仍優先。未實作前，文件應寫明相對路徑只吃類別常數，且 Locust 忽略字典裡的 host。

#### CR-03

- 位置：`architecture.md` 第 63–64 行與 `je_load_density/mcp_server/server.py` 第 8–12 行；對照 `je_load_density/__init__.py` 第 1–4、812–823 行，以及 `architecture.md` 第 222–224 行。
- 說明：§3 與 MCP 模組說明仍寫「匯入套件就會匯入 locust，並做 gevent `patch_all()`」。現況是 `__getattr__` 按固定 `_EXPORTS` 延遲載入；`import je_load_density`、CLI 解析器與原生 engine 不會載入 Locust，也不會在匯入時對外連線。選到 Locust 後，`create_locust_env.py` 第 20 行才 `setup_logging`，`request_hook.py` 才向 `events.request` 註冊。`utils/metrics/__init__.py` 在被第一次取用時會一併匯入 `locust.events`，那是匯出函式被點名，不是套件匯入，而且該次匯入仍不發請求。
- 依據：規範 8、10。§6 後段已改成延遲載入，§3 與 MCP docstring 沒有一起改。
- 狀態：未關閉。建議。行為本身符合「匯入不打外部」。
- 建議：把 §3 與 `mcp_server/server.py` 的匯入描述改成與 §6、`__init__.py` 相同。不要再寫套件匯入會修補執行緒。

#### CR-04

- 位置：`je_load_density/utils/security/rate_limit_probe.py` 第 37–39 行；`wrapper/user_template/fuzz_http_user_template.py` 第 42–56 行；`utils/recording/cdp_capture.py` 第 30–35 行；同型別還有 `soap_user_template.py` 第 52–56 行、`vault_user_template.py` 第 38–39 行、`consul_user_template.py` 第 26–28 行、`fcm_user_template.py` 的 `urlopen`。
- 說明：上述 `urlopen` 把呼叫端給的 URL 直接打開，沒有先限制方案。同套件的 Toxiproxy、OAuth2、通知器與 InfluxDB 已拒絕 http(s) 以外的方案，避免 `file://` 等進入 `urlopen`。`LD_probe_rate_limit` 是 executor 指令，動作檔與 socket 用戶端都叫得到；回傳不含本文，但非 http(s) 仍會被打開。fuzz／SOAP／Vault／Consul 則是操作者指定的壓測目標，風險較低，卻與已有閘門不一致。
- 依據：規範 6。對照 `utils/chaos/toxiproxy.py` 第 12–15 行與 `utils/metrics/influxdb_sink.py` 第 54–67 行。
- 狀態：未關閉。建議。負荷測試本來就要打呼叫端給的 http(s) URL，此項沒有在匯入時連外。
- 建議：共用一個 http(s) 方案檢查，套到 `probe_rate_limit`、CDP 發現、fuzz 與其他 stdlib HTTP 範本。Locust 的 `client.*` 路徑維持現狀即可。

沒有第 5 則以後的發現。

### 總評

目標 URL 的主路徑是清楚的：動作或桌面表單裡的絕對 `request_url`／`url` 進入 `request_executor.execute_task`，再進 Locust 的 HTTP 方法；協議範本則用步驟欄位，否則用 setter `host`（`default_host`）。匯入 `je_load_density` 不會打外部，也沒有 `eval`、`exec`、`shell=True`、`pickle`、`yaml.load`、`verify=False` 或裸 `except:`。未關閉的缺陷只有 CR-01：Locust 一啟動就把可能含憑證的參數寫進共用日誌。CR-02 到 CR-04 不會在匯入或絕對 URL 的正常路徑上立刻打錯主機。

`Executor.__init__`（`utils/executor/action_executor.py`）遠超過 80 行，內容是 `LD_*` 指令表，不是高複雜度分支，本輪不升為缺陷。熱點函式的巢狀與參數數量未超過加嚴上限。

### 已核對

- 套件目錄是 `je_load_density/`。`build/lib` 下的複本未審。
- `yaml_file.py` 使用 `yaml.safe_load`／`safe_dump`。
- `subprocess` 只出現在 `utils/chaos/chaos_mesh.py`（kubectl 參數列表，無 shell）與 `utils/ai/root_cause.py`（固定的 `git log --stat`）。`loaddensity shell` 是 `code.InteractiveConsole`（`utils/dx/repl.py`），不是 `shell=True`。
- gRPC `stub_path` 先經點號識別字檢查才 `importlib`（`grpc_user_template.py`）；這是設計過的允許形式，未看到繞過後直接執行任意字串。
- 套件閘門：`PackageManager` 只註冊函式、拒絕型別是 `LoadDensityTestExecuteException`。`allow_packages` 與 `set_allow_arbitrary_packages` 只在 `Executor` 上，不在 `event_dict`，動作檔不能自己打開。預設仍放行並發 `DeprecationWarning`，與三份 README 及 `progress.md` #23 一致，不是允許清單被繞過，不計缺陷。
- 桌面工作程序會複製當下的允許清單與 `allow_arbitrary_packages`（`gui/run_worker.py` 第 123–128 行），沒有另開一道閘門。
- 任務裡的 `verify` 是轉交給用戶端的欄位，不是程式預設關閉驗證。原生用戶端預設 `verify=True`（`async_http.py` 第 69 行）。
- 參數函式只有 `uuid`、`now`、`randint`，沒有把 `${...}` 交給 `eval`。
- §6：APITestka 依賴的絕對 `request_url` 會原樣進入 Locust；隱藏的 `--execute_str` 等仍在 `__main__.py`，且是 `json.loads` 不是 `eval`。
- socket 預設 `localhost`，token 可選、比對在核心處理器；啟動時才 `monkey.patch_all()`，不是匯入時。

### 未涵蓋

未執行測試、未啟動 Locust、未對任何主機送流量。未讀 `test/`、`build/`、`docs/` 產生物、編輯器與 `deploy/`。`je_action_core` 的 `_check_allowed` 與 `SAFE_BUILTINS` 實作不在本樹，只核對本套件怎麼接上。41 個協議範本沒有逐一追每個客戶端呼叫，只抽查 HTTP 主路徑與會 `urlopen` 的範本。

### 本專案加嚴

採用 `CLAUDE.md`：複雜度 15、函式 80、巢狀 4、參數 7、行寬 120；禁止對不受信任輸入 `eval`／`exec`／`pickle.loads`／`yaml.load`；`subprocess` 禁止 `shell=True`；明確逾時；不得記錄密文。CR-01 直接違反最後一條。CR-02 涉及文件所說的 host 與程式實際使用的 host 不一致。

### 結論

需修正。未關閉缺陷 1 則（CR-01），建議 3 則（CR-02、CR-03、CR-04）。修掉 CR-01 之前不能算通過。
