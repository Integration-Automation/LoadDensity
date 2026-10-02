"""
AWS Lambda ephemeral worker adapter.

The pattern: deploy a Lambda whose handler runs LoadDensity's asyncio
engine against a slice of the task list, then aggregate results via SQS
or directly via Lambda response payload. This module is the launcher —
it does NOT package the Lambda itself; that's a Terraform/CDK concern.

Usage::

    from je_load_density.cloud.aws_lambda import invoke_lambda_workers

    results = invoke_lambda_workers(
        function_name="loaddensity-worker",
        workers=10,
        payload_template={"url": "https://api/x", "users": 50, "duration": 30},
        region_name="us-east-1",
    )
"""

import json
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from ._validation import CloudLaunchError, positive_integer, required_string, sdk_error_types


def _import_boto3():
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError(
            "boto3 is required for the AWS Lambda adapter; "
            "install with: pip install boto3"
        ) from error
    return boto3


def _consume_payload(payload: Any, read_body: bool) -> Any:
    close = getattr(payload, "close", None)
    try:
        if hasattr(payload, "close") and not callable(close):
            raise ValueError("malformed Lambda payload close method")
        read = getattr(payload, "read", None)
        if hasattr(payload, "read") and not callable(read):
            raise ValueError("malformed Lambda payload read method")
        return read() if read_body and callable(read) else payload
    finally:
        if callable(close):
            close()


def _decode_payload(response: Dict[str, Any]) -> Dict[str, Any]:
    body = _consume_payload(response.get("Payload", b""), read_body=True)
    if not isinstance(body, (bytes, str)):
        raise ValueError("malformed Lambda payload")
    text = body.decode("utf-8") if isinstance(body, bytes) else body
    if not text.strip():
        raise ValueError("empty Lambda worker payload")
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
    if not isinstance(decoded, dict):
        raise ValueError("Lambda worker payload must be an object")
    return decoded


def _judge_response(response: Dict[str, Any], index: int, invocation_type: str) -> Dict[str, Any]:
    if not isinstance(response, dict):
        raise ValueError("malformed Lambda response")
    expected_status = {"RequestResponse": 200, "Event": 202, "DryRun": 204}[invocation_type]
    payload = _decode_payload(response) if invocation_type == "RequestResponse" else {}
    if invocation_type != "RequestResponse":
        _consume_payload(response.get("Payload"), read_body=False)
    if response.get("StatusCode") != expected_status or "FunctionError" in response:
        failed_response = {**response, "worker_payload": payload}
        raise CloudLaunchError("lambda", [index], [], "invocation failed or returned FunctionError", failed_response)
    if invocation_type == "RequestResponse":
        return payload
    return {"status": "accepted" if invocation_type == "Event" else "validated",
            "worker_index": index, "StatusCode": expected_status}


def _collect_results(futures: List[Future]) -> List[Dict[str, Any]]:
    results = []
    errors = []
    for future in futures:
        try:
            results.append(future.result())
        except CloudLaunchError as error:
            errors.append(error)
    if errors:
        failed_workers = [index for error in errors for index in error.failed_workers]
        error = CloudLaunchError("lambda", failed_workers, results, "one or more invocations failed",
                                 errors[0].response)
        raise error from (errors[0].__cause__ or errors[0])
    return results


def invoke_lambda_workers(
    function_name: str,
    workers: int,
    payload_template: Dict[str, Any],
    region_name: Optional[str] = None,
    invocation_type: str = "RequestResponse",
) -> List[Dict[str, Any]]:
    """Invoke positive ``workers`` and return worker-ordered results.

    FunctionError and malformed responses raise CloudLaunchError with other
    successful results. Event returns acceptance only; DryRun returns validation.
    Non-JSON text remains available as ``raw``. No invocation is retried.
    """
    positive_integer(workers, "workers")
    required_string(function_name, "function_name")
    if invocation_type not in {"RequestResponse", "Event", "DryRun"}:
        raise ValueError("invocation_type must be RequestResponse, Event or DryRun")
    if not isinstance(payload_template, dict):
        raise ValueError("payload_template must be a dictionary")
    # Serialize before creating clients or submitting any work.
    template = json.dumps(payload_template)
    boto3 = _import_boto3()
    service_errors = sdk_error_types("aws")
    try:
        client = boto3.client("lambda", region_name=region_name)
    except service_errors as error:
        raise CloudLaunchError("lambda", list(range(workers)), [], "client initialization failed") from error

    def _invoke(index: int) -> Dict[str, Any]:
        payload = json.loads(template)
        payload["worker_index"] = index
        payload["worker_count"] = workers
        try:
            response = client.invoke(
                FunctionName=function_name, InvocationType=invocation_type,
                Payload=json.dumps(payload).encode("utf-8"),
            )
        except service_errors as error:
            raise CloudLaunchError("lambda", [index], [], "invoke failed") from error
        try:
            return _judge_response(response, index, invocation_type)
        except (ValueError,) + service_errors as error:
            raise CloudLaunchError("lambda", [index], [], "invalid invocation response",
                                   response if isinstance(response, dict) else None) from error

    # Results come back in worker order (results[i] is worker i), not completion order, so a
    # caller can tell which slice each summary belongs to.
    with ThreadPoolExecutor(max_workers=max(workers, 1)) as pool:
        futures = [pool.submit(_invoke, i) for i in range(workers)]
        return _collect_results(futures)


def lambda_worker_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Reference Lambda handler. Deploy this as the worker function and
    invoke with ``invoke_lambda_workers``.
    """
    import asyncio

    from je_load_density.engine.asyncio_engine import run_async_load
    from je_load_density.utils.test_record.test_record_class import test_record_instance

    # A warm Lambda reuses the process, and the records are process-global: without this the
    # summary of every invocation after the first would include the ones before it.
    test_record_instance.clear_records()
    tasks = event.get("tasks") or [{
        "method": event.get("method", "get"),
        "request_url": event["url"],
    }]
    return asyncio.run(run_async_load(
        tasks=tasks,
        users=int(event.get("users", 10)),
        duration_seconds=float(event.get("duration", 10.0)),
        http2=bool(event.get("http2", False)),
    ))
