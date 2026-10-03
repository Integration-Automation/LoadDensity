# Cloud Backend Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate cloud launcher inputs and report service, partial-launch and malformed-response failures without creating real resources.

**Architecture:** Keep the four public launchers and lazy optional SDK imports. Share preflight validation and a RuntimeError subtype carrying successful/accepted responses and failed worker indices. No adapter retry is added.

**Tech Stack:** Python 3.10+, pytest, controllable SDK doubles, urllib, local HTTP.

**Spec:** `docs/superpowers/specs/2026-10-02-testing-platform-roadmap.md`, 雲端後端測試.

## Global Constraints

- 合約測試使用可控 SDK stub／本機 HTTP，不申請真實雲端資源。
- 測試 SDK 呼叫參數與結果判定，不能只驗證 fake 回傳值原封不動傳出。
- 對可能已被服務接受的啟動請求必須使用服務支援的冪等識別，不能盲目重送。
- Preserve public launcher signatures and successful response shapes where API-correct.
- Root worker owns README/Sphinx/architecture/log updates and commits.

## Review Focus

- bool, fractional and zero worker counts must fail before SDK calls.
- Previously accepted workers remain inspectable after another worker fails.
- A Lambda HTTP success containing FunctionError must fail; Event means accepted only.
- Cloud Run run overrides do not support parallelism: reject it before authentication.
- ACI group names differ across launches and failed polling cannot report success.

### Task 1: AWS worker contracts

**Files:** Modify `je_load_density/cloud/aws_fargate.py`, `aws_lambda.py`; create `_validation.py`; test `test/test_cloud_contracts.py`, `test/test_cloud_launchers.py`.

**Interfaces:** `CloudLaunchError(RuntimeError)` exposes `responses`, `failed_workers`, `backend`; successes keep Fargate raw responses and Lambda worker-ordered dictionaries.

- [x] Write failing tests for invalid counts/network/env; Fargate failures/malformed tasks; Lambda FunctionError/status/non-JSON/Event and mixed results. Assert index/count overrides, service call count, accepted responses, error causes and closed payload streams.
- [x] Run `python -m pytest test/test_cloud_contracts.py -q`; observe contract failures.
- [x] Implement positive integer/string/env validation, SDK error chaining, strict response judgement and isolated reference handler behavior.
- [x] Run AWS contract and existing launcher tests; expect all AWS tests passing.

### Task 2: Cloud Run REST contract

**Files:** Modify `je_load_density/cloud/gcp_cloud_run.py`; test `test/test_cloud_contracts.py`.

**Interfaces:** `run_cloud_run_job(...) -> Dict[str, Any]` returns a valid Operation; non-None `parallelism` raises ValueError because jobs.run does not support that override.

- [x] Write failing tests for unsupported parallelism, invalid task_count/timeout/overrides, empty token, bad Operation/error JSON. Test refresh, permission/timeout/throttle/server errors with stubs and local HTTP; assert POST/auth/payload/timeout and no retry.
- [x] Run Cloud Run tests and observe failures.
- [x] Validate supported overrides; refresh token per call; reject empty token and malformed/error operations.
- [x] Run Cloud Run tests; expect passing.

### Task 3: Azure operation lifecycle

**Files:** Modify `je_load_density/cloud/azure_aci.py`; test `test/test_cloud_contracts.py`, `test/test_cloud_launchers.py`.

**Interfaces:** `launch_aci_workers(...) -> List[Dict[str, Any]]` waits for provisioning, returns unique name/status/resource_id; exceptions retain prior responses and failed indices.

- [x] Write failing tests for positive finite cpu/memory, DNS prefix limits, unique names between runs, poller failure/malformed result, credentials/permissions/timeout/throttle and partial provisioning. Assert model fields and create calls.
- [x] Run ACI tests and observe failures.
- [x] Add unique invocation suffix, await poller.result, validate successful resource, chain SDK errors with partial evidence.
- [x] Run `python -m pytest test/test_cloud_launchers.py test/test_cloud_contracts.py -q`; expect passing; root runs whole suite after integration.

## Additional SDK verification

`test/test_cloud_sdk_contracts.py` uses botocore Stubber/StreamingBody, official AWS and Google exception classes, and a local Azure HttpTransport implementing a successful PUT response. It checks the real Azure serializer and long-running operation result. These twelve tests require the corresponding cloud extras; the mandatory contract tests do not skip when SDKs are absent.

Red evidence: initial contracts 87 failed / 5 passed; expanded boundaries 13 failed / 98 passed; missing public error export 1 failed / 1 passed; missing Lambda decoded failure payload and ACI attempted name 2 failed.

Green evidence: cloud contracts and official SDK verification 141 passed. Production complexity maximum 10, function length maximum 73 lines, no lines over 120 characters. Final whole-suite evidence is recorded by the coordinating worker in the update log.

## Execution rulings

- Execution and design were already approved before dispatch; continue without another approval gate.
- SDK-specific exceptions are caught at service boundaries only; unexpected programming exceptions propagate.
- Cloud Run parallelism migration: configure parallelism on the deployed Job; use task_count for the run override.
- Commits and shared documentation are performed by the coordinating worker.
