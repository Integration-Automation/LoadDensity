# LoadDensity 與跨專案測試流程設計草案

狀態：2026-10-02 已確認；以下描述目標行為，各項實作狀態依 progress.md 與 updates 記錄。

## 目標與範圍

一份版本控制中的測試腳本分別用於功能測試、壓力測試與上線後合成監控：
APITestka 判定功能正確性，LoadDensity 測量容量與 SLA，WebRunner 的
`synthetic_monitoring` 負責週期執行、失敗／恢復門檻與狀態變化通知。
這批工作也涵蓋 UI 重新設計、煙霧測試、Docker extras 安裝矩陣、百分位數帶狀圖、
async 引擎對等、雲端後端測試，以及分散式健康檢查與失聯重新分配。

假設：「百位數」指「百分位數」；UI 範圍包含 PySide6 GUI 與現有 web dashboard。
功能測試與監控共用同一套正確性檢查；壓力測試另外套用負載與 SLA 設定。

## 現況與相依關係

- `engine/asyncio_engine.py` 只支援 HTTP 請求的部分欄位，未接入 `start_test`。
  它共用程序全域 record，使用一個 client；scenario、extractor 與個別使用者狀態尚未對等。
- `__init__.py` 直接載入 Locust。async 子模組也會經過套件初始化，必須處理 gevent
  monkey patch 對 asyncio、執行緒與 TLS 的影響，不能只增加一個引擎參數。
- Locust 的成功／失敗 record 是字典；APITestka 成功 record 使用
  `request_method`、`request_url`、`request_time_sec` 等欄位，失敗 record 常為二元素清單。
- `APITestka/je_api_testka/integrations/load_density*.py` 已有腳本轉換與子行程執行，
  目前轉換部分 request 指令與 status assertion，其他內容會列在 `skipped`。
- `WebRunner/.../synthetic_monitoring/monitor.py` 已提供 `from_action_files(files, runner)`、
  `tick_once()`、`run_for()`。check 沒有丟例外便視為通過，因此整合必須將測試失敗轉為例外。
- `_wait_for_workers()` 最多等 60 秒，逾時記警告後仍開跑；只計算 clients 的數量。
- GUI 將 RPS 與 p95 畫在同一條數值軸；離線 chart report 使用 `ts` 或 request index，
  與 request hook 提供的 `start_time` 不一致。
- `test/test_cloud_launchers.py` 已有成功路徑與 SDK 缺少測試；四個後端仍需補錯誤與邊界情境。
- CI 有 Windows／Ubuntu、Python 3.10–3.14 的單元測試，沒有獨立 extras 容器安裝矩陣。

## 可選方向

| 方向 | 優點 | 代價 |
| --- | --- | --- |
| 共用版本化契約，各專案保留 runner（建議） | 延伸既有 APITestka 橋接；結果能比較；引擎彼此隔離 | 需要協調 schema 與相容性測試 |
| 只在 LoadDensity 加轉換層 | 跨 repo 改動較少 | APITestka 與監控仍有多套 record 真實來源 |
| 由 TestPioneer 統一編排所有模式 | 重用既有多 runner 編排 | 擴大本批範圍；不能單靠編排解決 script 與 record 語意差異 |

建議採第一種。TestPioneer 之後可以呼叫這些 runner，本批不新增另一套編排平台。
record 契約與正規化的共用基礎放在既有零相依的 ActionCore；HTTP transport adapter、
報表與監控策略留在各專案。ActionCore 的「action 執行紀錄」與「request 結果」保持不同型別。

## 子專案與交付順序

每一列都有獨立的設計、實作計畫與驗收；不把整批視為一個不可拆分的改動。

| 順序 | 子專案 | 完成條件 |
| --- | --- | --- |
| 1 | 共用 record 契約 | APITestka、Locust 與 asyncio 的成功、assertion failure、transport failure 都能輸出同一 schema，舊介面仍可讀 |
| 2 | 煙霧測試與 Docker extras CI | checkout 建置的 wheel 在乾淨容器安裝、`pip check`、實際能力檢查；本機 HTTP 的 CLI／報表／SLA 閉環能通過及正確失敗 |
| 3 | Async 引擎對等 | 同一腳本從 Python、action、CLI、GUI 進入兩引擎；scenario、狀態隔離、負載控制、取消、輸出、監控與分散式語意均有對等測試 |
| 4 | 分散式恢復與雲端後端 | ready gate、心跳、失聯重新分配、重連與結果去重；四個雲端 adapter 的失敗／部分失敗測試完整 |
| 5 | 共用腳本三種模式 | 一份來源實際執行功能、容量與兩輪以上監控；正確性失敗在每種模式都可觀察，沒有默默丟棄 assertion |
| 6 | UI 與百分位數圖 | GUI／dashboard 顯示一致的 run 狀態、容量與延遲；時間窗百分位數在即時圖與輸出報表一致 |

第 2 項可在第 1 項前先建立現況回歸基準。第 4 項的雲端契約測試可獨立交付，
分散式恢復需使用第 1 項的 run／worker／record 識別。第 6 項依賴已穩定的 run lifecycle 與統計資料。

## 煙霧測試與 extras 安裝矩陣

新增 `test/smoke/`：本機測試服務在獨立子行程啟動，避免 gevent／asyncio 互相影響。
涵蓋 wheel 安裝後的 CLI、`LD_start_test`、summary／JSON／JUnit、SQLite、SLA gate、
dashboard JSON／SSE、async 路徑與 offscreen GUI 啟動、執行、取消。測試不能只驗證 import 成功。

Docker job 從 `pyproject.toml` 產生 `base`、每個 extra、`all` 的矩陣，不維護另一份手寫 extras 清單。
每格使用新環境，只安裝該 wheel 與指定 extra；安裝、`pip check`、CLI 與相應 capability probe 任何一步失敗都讓 job 失敗。
probe 不可用 `importorskip` 掩蓋宣告應有的功能；沒有相依的 `mcp` extra 仍需協定握手。

PR 執行代表性 Python 3.12 的完整 extras 集合與 base 的 3.10／3.14；排程補齊 3.10–3.14。
若某個 extra 在宣告支援的版本裝不起來，應修正依賴／支援聲明，不能未經記錄排除。
GUI 容器安裝需要的系統函式庫並使用 offscreen；協定整合測試以 Compose 的健康檢查等候服務就緒。
`all` 另外驗證套件共存。extras 的真實網路服務測試與安裝 probe 分開報告，不能互相替代。

CI Stable／Dev 共用同一個可重用工作流程，保留 SHA 鎖定 actions、最小權限、job timeout，
並讓既有發版 job 等候必要的煙霧／extras 檢查。建置及發版工具仍沿用 hash lock。

## Async 引擎對等

`start_test` 保留預設 Locust 與既有參數，新增明確的 engine 選擇；`run_async_load` 保留可 await 的介面。
使用 Engine／RunHandle 邊界承接 start、stop、wait、snapshot，runner 的 I/O 排程各自實作。
套件 facade 延後載入 Locust／其 request hook，async 入口不可觸發 gevent patch。

對等清單至少涵蓋 request kwargs、labels、預期 status、全部現有 assertions／extractors、
sequence／weighted／conditional、retry、think time、throttle、CSV／DB／變數解析、
per-user cookie／session、spawn rate、stages／spike／soak、SLA、報表、SQLite、metrics exporters、
取消與例外清理，以及 local／master／worker 的生命週期。
目前全域 resolver 的使用者隔離問題（`progress.md` #15）是前置工作。

先交付 HTTP／HTTP2 的對等測試，再逐協定擴展 capability table。未支援的 protocol／設定在啟動前報錯；
不以同步 blocking call 包裝成 async 支援。只完成 HTTP 子階段時，不宣告整個 async 對等項目完成。
測試除結果數字外，也驗證並行上限、ramp、停止時不殘留 client／task／socket，以及每次 run 統計互不污染。

## 分散式健康與失聯重新分配

先核對目前安裝的 Locust 對 heartbeat、missing client 與 rebalance 的支援，重用它的公開機制，
LoadDensity 補上明確策略、可觀察狀態與測試，避免再造相互競爭的心跳／使用者分配器。

分開 target health 與 worker health。設定採 `worker_startup_timeout=60`、
`worker_heartbeat_interval=5`、`worker_lost_timeout=15`；皆需驗證正數，lost timeout 大於 interval。
`expected_workers` 是啟動 gate，只有 ready 且未失聯的 worker 算入。
預設逾時失敗並清理 runner；明確選擇 `worker_startup_policy="degraded"` 才降級開跑。

worker 狀態為 connecting／ready／running／lost／stopped。失聯時將「虛擬使用者容量」
重新分配到健康 worker，維持目標總使用者數與既有 ramp 約束；不重播可能已對目標產生副作用的單筆 HTTP request。
剩餘 worker 無法承擔時將 run 標成 degraded 或 failed，而不是宣稱維持目標容量。

有限工作分片使用 run_id、assignment_id、generation 與 lease；回收時 generation 遞增，
拒絕舊 lease 的遲到結果。record_id／worker_id 用於結果去重；重連不能造成 double assignment。
容量調整不保證跨機器搬移已登入 session，也不宣稱 exactly-once request；報告必須揭露受影響的 journey。
測試涵蓋啟動逾時、worker 被終止、網路中斷、遲到心跳、重連、全員失聯、負載形狀變化與 master 清理。

## 雲端後端測試

延伸現有 fake SDK 測試，覆蓋 Fargate／Lambda／Cloud Run／ACI 的非法數量／資源參數、
credentials failure、permission denied、timeout、限流、服務錯誤、部分成功與 malformed response。
特別驗證 Fargate 回傳 `failures`、Lambda `FunctionError`／非 JSON／Event 回應／warm invocation 隔離、
Cloud Run token refresh 與錯誤 HTTP 回應、ACI poller failure 與不同 worker 的唯一名稱。
測試 SDK 呼叫參數與結果判定，不能只驗證 fake 回傳值原封不動傳出。

合約測試使用可控 SDK stub／本機 HTTP，不申請真實雲端資源。實作時依官方文件核對 API payload；
若新增 retry，對可能已被服務接受的啟動請求必須使用服務支援的冪等識別，不能盲目重送。

## 單一腳本

保留 APITestka 的 action script 作為 request 與 correctness 的來源；可選的執行 profile
補充 load 與 synthetic 設定。延伸既有 APITestka→LoadDensity bridge，不複製 request 清單。
完整契約與 record 的第一階段設計見 [共用 record 設計](2026-10-02-shared-record-design.md)。

功能模式執行一次；load 模式將共用步驟套入負載引擎；synthetic 模式以 WebRunner 的 monitor
週期呼叫功能 runner。功能／assertion failure 必須轉成失敗結果並讓 monitor 的 check 丟例外，
不能把 executor 回傳或程序 exit code 0 視為充分的成功證據。
未知指令或無法轉換的檢查在 preflight 阻擋；需要 mode-specific 的動作明確標註，不靜默跳過。

## UI 與百分位數帶狀圖

GUI 主畫面：左側腳本／target／engine／負載設定；右側依序為 run 狀態與 Start／Stop、
使用者／RPS／failure rate／p50／p95／p99 指標、圖表、request 結果／logs／run history。
載入 action file、停止與多語系延伸既有元件；背景 runner 的更新只透過訊號進入 Qt UI。
running 時避免重複 Start，停止可見 stopping，失敗／完成保留結果供檢視。
web dashboard 以相同資訊順序呈現，窄螢幕堆疊顯示；動態 request 名稱透過 text node 安全呈現。

延遲圖採每秒時間窗的 p50 線、p50–p95 帶與 p95–p99 帶；RPS 使用獨立圖／軸。
GUI 用 QtCharts 的 area series；離線報表用 matplotlib `fill_between`；dashboard 用原生 SVG／canvas。
共用統計 helper 將成功與失敗合併並以 `start_time` epoch 排序；耗時使用 monotonic clock。
百分位數沿用既有排序索引規則：`index = int(round((p / 100) * (n - 1)))`，
其中 round 使用 Python 的 ties-to-even；取排序後該索引的值，不由各 UI 另算。
空窗顯示資料缺口而非零延遲，單樣本所有百分位數相同，RPS 為 count／實際 bucket 秒數。
不把平均數／已算好的 worker p95 再取平均當成全域百分位數。
即時資料採有界時間窗，歷史結果由持久化讀取，避免長時間監控無限累積記憶體。

## 驗證與文件

每個子專案補實際行為測試；既有 legacy CLI、APITestka bridge summary keys、record lists 保持相容。
跨 repo 的公開契約與 consumer 測試同步更新；涉及 WebRunner 工作樹前遵守 workspace 的即時 consumer 規則。
使用者行為變動在同一階段更新三份 README、Sphinx 與各 repo 的 `architecture.md` §6。
只有完成的項目才從 `progress.md` 移除並寫入 `docs/updates/`。

2026-10-02 基準：`.venv/Scripts/python.exe -m pytest` 執行 asyncio、cloud、chart report、
dashboard、record、GUI 的既有測試，27 passed；另有既有 gevent TLS monkey patch 與 pytest collection warning。
本機 Docker CLI 可呼叫，但 Docker Desktop Linux daemon 未啟動；容器驗證尚未執行。
