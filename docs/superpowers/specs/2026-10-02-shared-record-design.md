# 共用 request record v1 設計草案

狀態：2026-10-02 已確認，依使用者指示開始實作。此文件是第一個子專案的規格；整批範圍見
[測試平台設計](2026-10-02-testing-platform-roadmap.md)。

## 目的與邊界

讓 APITestka 的功能結果、LoadDensity 的 Locust／asyncio 結果與 WebRunner synthetic check
可用同一套 JSON 格式保存、比較與追蹤。第一階段只定義並接上 request record；
單一腳本三模式、分散式恢復、UI 與 extras CI 依 roadmap 分別交付。
WebRunner 的 browser action／screenshot／trace 舊紀錄不轉成 HTTP response；
monitor 保留自身結果，新增關聯 run_id 與 request 結果來源。

## 所有權與架構

ActionCore 新增純標準函式庫的 request record 型別、驗證與序列化工具，保留零外部相依。
它不 import Locust、requests、httpx、Qt 或雲端 SDK，也不管理 framework 的 singleton。
APITestka 與 LoadDensity 的 adapter 負責將各自 response／exception 轉成 canonical record。
schema_version=`1` 是結果契約版本，與各套件發版號獨立。

ActionCore 先發佈具有該介面的版本，再提高使用端相依下限；測試期間可指定隔離 checkout。
不能直接改共用 executor 的 action execution record，亦不能改它原有的 repr、key 或 error 行為。

## Canonical 欄位

每一筆成功或失敗使用相同物件結構，以下欄位必須出現；未知的量值用 null，不捏造零值。

| 欄位 | 型別／規則 |
| --- | --- |
| schema_version | integer，固定 1 |
| record_id | string，run 內唯一；同一結果重送保留同一 ID |
| run_id | 非空 string，每次執行重新建立 |
| source | `apitestka`／`loaddensity`／`webrunner` |
| phase | `functional`／`load`／`synthetic` |
| engine | 非空 string，例如 `requests`／`httpx`／`locust`／`asyncio` |
| worker_id | string 或 null，本機可為 null |
| scenario_id | string 或 null |
| step_id | string 或 null，對應腳本的穩定步驟識別 |
| protocol | 非空 string，例如 `http`；其他協定以 extension 承載特定資訊 |
| request_method | string，HTTP method 大寫 |
| request_url | string，原 request endpoint；不得以 request name 取代 |
| name | string，request label，缺少時使用 method 與 endpoint |
| status_code | integer 或 null；transport failure 為 null |
| start_time | 有限 float 或 null，UTC epoch seconds |
| end_time | 有限 float 或 null，UTC epoch seconds；存在時不得小於 start_time |
| response_time_ms | 有限、非負 float 或 null，monotonic 計算的耗時 |
| response_length | 非負 integer 或 null，實際 response bytes 長度 |
| outcome | `passed`／`failed` |
| error | null 或 `{kind: string, message: string}`，failed 時必須有 error |
| assertions | JSON array，每筆含 type、passed；失敗附 message |
| extensions | JSON object，保留協定或來源特有資訊，不覆寫 canonical 欄位 |

HTTP response 若實際回傳 status，即使 assertion 不通過仍保存原 status 與 latency。
record 工具只保存 runner 的判定，不自行把 status 改判為成功或失敗。
第一階段保留各 runner 目前的判定；後續引擎與腳本對等階段才統一
「HTTP 4xx／5xx 預設 failed，明確 status expectation 命中時可 passed，其他 assertions 仍需通過」。
Transport failure 保存實際已耗時間，error.kind 區分 timeout／connection／tls／其他 transport。
設定錯誤在 preflight 丟例外，不製造零毫秒「request 已執行」結果。
assertion failure、HTTP status failure 與 runner internal error 使用不同 kind。
新紀錄的 end_time 使用 start_time 加上 monotonic 耗時，避免 wall clock 校正產生負持續時間。

選填 payload 欄位為 `text`、`headers`、`content_base64`、`request_body`。
bytes 使用 base64；headers 轉為 JSON object；datetime 統一轉 epoch；timedelta 轉為毫秒。
token、Authorization、Cookie 等敏感資料沿用各 runner 的遮罩策略；壓力模式預設不存完整 body。
擴充欄位不要求保存任意 Python object，不能以 `str(response)` 當成正常序列化。

## 範例

```json
{
  "schema_version": 1,
  "record_id": "run-001-worker-0-1",
  "run_id": "run-001",
  "source": "loaddensity",
  "phase": "load",
  "engine": "asyncio",
  "worker_id": "worker-0",
  "scenario_id": "checkout",
  "step_id": "get-health",
  "protocol": "http",
  "request_method": "GET",
  "request_url": "http://127.0.0.1:8080/health",
  "name": "health",
  "status_code": 200,
  "start_time": 1790899200.0,
  "end_time": 1790899200.025,
  "response_time_ms": 25.0,
  "response_length": 12,
  "outcome": "passed",
  "error": null,
  "assertions": [{"type": "status_code", "passed": true}],
  "extensions": {}
}
```

## 相容性與資料流

1. 各 runner 建立 RequestRecord，集中交給該 run 的 RecordSink。
2. sink 將 canonical record 保存至 JSON／SQLite，並更新 bounded live statistics。
3. 舊的 `test_record_list`／`error_record_list` 介面由 legacy adapter 供既有報表與 consumer 使用。
   LoadDensity 保留 `Method`、`test_url`、字串 status 與 error 等既有型別；
   APITestka 保留 response-data return shape 與舊失敗清單，不在第一階段強制下游改格式。
4. 新的 canonical export 明確版本化；既有 summary 的 `totals` 與
   `latency_overall.p95_ms` 以及 `<report_name>.json` 不改名、不改意義。
5. legacy import 使用來源專用 adapter：LoadDensity 的 status `"0"` 作 transport sentinel，
   APITestka 失敗清單能取出的 method／URL 仍保存，沒有時間資訊便填 null。
   malformed record 回報帶位置的 validation error，不靜默丟掉。

明確指定 RunContext 隔離每次執行；全域 legacy singleton 只服務既有呼叫模式。
canonical sink 不能每次輸出都掃描全域成功／失敗清單，也不能因上一輪資料殘留改變本輪 summary。
跨 worker 不平均百分位數；本階段完整 raw record 可供離線統計，後續 distributed live
需要另外選擇可合併 histogram，該項未完成前不標示為精確的全域 live percentile。

## 預定檔案與介面責任

| 專案／路徑 | 責任 |
| --- | --- |
| ActionCore：`je_action_core/request_record.py` | RequestRecord／RecordError 型別、validate、JSON-safe serialization |
| LoadDensity：`utils/test_record/contract.py` | Locust／async record adapters、legacy import／export |
| LoadDensity：`utils/test_record/run_context.py` | RunContext、run-scoped RecordSink、record IDs 與統計隔離 |
| LoadDensity：`wrapper/event/request_hook.py` | 將 request event 交給 sink，保留 legacy hook 相容性 |
| LoadDensity：`engine/asyncio_engine.py` | 以同一 sink 記錄成功／失敗，補上真實 failure latency |
| LoadDensity：`utils/test_record/sqlite_persistence.py` | 版本化 canonical export 與既有資料庫相容讀取 |
| APITestka：`utils/test_record/contract.py` | requests／httpx／exception adapters，不改 transport return 值 |
| APITestka：`requests_wrapper/`、`httpx_wrapper/` | 接上 request sink，保存 assertion 與 HTTP failure |
| 各方：`architecture.md` §6、README、Sphinx、contract tests | 發版相依、schema 與 consumer 相容性 |

以上是路徑與責任規劃，實作計畫需在各 repo 規則與工作樹狀態檢查後固定確切 signature。

## 驗收

- 三條路徑對同一個本機 endpoint 輸出的 canonical keys／types 相同，engine 與來源可區分。
- 200／201、404／500、內容 assertion failure、timeout、connection refused 均保存 runner 的原 outcome。
  預期 404 的共同判定另由 roadmap 第 3／5 子專案驗收，不以 record adapter 偷改既有語意。
- response bytes、非 ASCII headers／錯誤訊息、datetime、timedelta 能 JSON round-trip。
- 兩個 run、並行使用者與 Lambda warm invocation 的 record 不交叉污染；重送 ID 可去重。
- legacy fixtures 的 success、failure list、status sentinel 與缺時間欄位皆可匯入。
- 舊 JSON／JUnit／summary／SQLite consumer、CLI 旗標與 APITestka load bridge 回歸測試通過。
- 新格式未知 schema version、負 latency、NaN、缺必要欄位與 malformed error 明確拒絕。
- ActionCore 的套件相依不增加，原 action executor 與其 consumer 測試全部通過。

## 後續單一腳本契約

以下是第 5 子專案的預定文件形狀，用以檢查 record 的 phase／step_id 是否足夠；
不屬於本階段已可使用的 CLI 功能：

```json
{
  "api_testka": [
    ["AT_test_api_method", {
      "http_method": "get",
      "test_url": "http://127.0.0.1:8080/health",
      "result_check_dict": {"status_code": 200}
    }]
  ],
  "execution_profiles": {
    "functional": {},
    "load": {
      "engine": "asyncio", "user_count": 20, "spawn_rate": 5, "test_time": 30,
      "sla": {"min_requests": 1, "max_failure_rate": 0, "max_p95_ms": 200}
    },
    "synthetic": {
      "interval_seconds": 60, "failure_threshold": 2, "recovery_threshold": 1
    }
  }
}
```

request 只寫一次；每種模式產生新 run_id，step_id 由來源 action index 或明確 name 穩定建立。
以獨立子行程啟動 LoadDensity，避免 Locust patch 污染 APITestka 或 monitor。
monitor 執行功能檢查，不在每個 interval 重跑容量測試。
依既有 APITestka bridge 擴展 request、assertion、extractor 轉換；無法轉換必須在啟動前報錯。
功能 runner 不能只看 exit code，需讀取結構化 outcome；synthetic 的 check 遇到 failed 要丟例外。
