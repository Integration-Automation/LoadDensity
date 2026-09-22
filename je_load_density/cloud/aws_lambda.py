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
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional


def _import_boto3():
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError(
            "boto3 is required for the AWS Lambda adapter; "
            "install with: pip install boto3"
        ) from error
    return boto3


def invoke_lambda_workers(
    function_name: str,
    workers: int,
    payload_template: Dict[str, Any],
    region_name: Optional[str] = None,
    invocation_type: str = "RequestResponse",
) -> List[Dict[str, Any]]:
    """Invoke ``workers`` Lambda functions in parallel and collect results."""
    boto3 = _import_boto3()
    client = boto3.client("lambda", region_name=region_name)
    results: List[Dict[str, Any]] = []

    def _invoke(index: int) -> Dict[str, Any]:
        payload = dict(payload_template)
        payload["worker_index"] = index
        payload["worker_count"] = workers
        response = client.invoke(
            FunctionName=function_name,
            InvocationType=invocation_type,
            Payload=json.dumps(payload).encode("utf-8"),
        )
        body_bytes = response.get("Payload", b"").read() if hasattr(
            response.get("Payload"), "read"
        ) else response.get("Payload", b"")
        body_text = body_bytes.decode("utf-8") if body_bytes else "{}"
        try:
            return json.loads(body_text)
        except json.JSONDecodeError:
            return {"raw": body_text}

    # Results come back in worker order (results[i] is worker i), not completion order, so a
    # caller can tell which slice each summary belongs to.
    with ThreadPoolExecutor(max_workers=max(workers, 1)) as pool:
        futures = [pool.submit(_invoke, i) for i in range(workers)]
        results.extend(future.result() for future in futures)
    return results


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
