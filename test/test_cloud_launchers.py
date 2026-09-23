"""Real tests for the cloud worker launchers (progress.md #1), with the cloud SDKs replaced by fakes.

Nothing reaches AWS, Google or Azure: boto3, google-auth / urlopen and the Azure SDK are swapped
for stand-ins that record what the launcher asked for.
"""
import io
import json
import threading
import time
from types import SimpleNamespace

import pytest

from je_load_density.cloud import aws_fargate, aws_lambda, azure_aci, gcp_cloud_run
from je_load_density.utils.test_record.test_record_class import test_record_instance


class _FakeBoto3:
    def __init__(self, client):
        self._client = client
        self.requested = []

    def client(self, service, region_name=None):
        self.requested.append((service, region_name))
        return self._client


def test_fargate_runs_one_task_per_worker_with_its_index(monkeypatch):
    calls = []
    ecs = SimpleNamespace(run_task=lambda **kwargs: calls.append(kwargs) or {"tasks": [{}]})
    boto3 = _FakeBoto3(ecs)
    monkeypatch.setattr(aws_fargate, "_import_boto3", lambda: boto3)
    responses = aws_fargate.launch_fargate_workers(
        cluster="load", task_definition="ld:3", workers=3, subnets=["subnet-1"],
        security_groups=["sg-1"], region_name="eu-west-1", overrides_env={"TARGET": "https://x"})
    assert boto3.requested == [("ecs", "eu-west-1")]
    assert len(responses) == 3
    network = calls[0]["networkConfiguration"]["awsvpcConfiguration"]
    assert network == {"subnets": ["subnet-1"], "securityGroups": ["sg-1"], "assignPublicIp": "DISABLED"}
    for index, call in enumerate(calls):
        assert call["launchType"] == "FARGATE"
        env = {item["name"]: item["value"] for item in call["overrides"]["containerOverrides"][0]["environment"]}
        assert env == {"TARGET": "https://x", "LD_WORKER_INDEX": str(index), "LD_WORKER_COUNT": "3"}


def test_lambda_results_come_back_in_worker_order(monkeypatch):
    def invoke(FunctionName, InvocationType, Payload):  # noqa: N803 - boto3 keyword names
        payload = json.loads(Payload)
        # Later workers answer first, so completion order is the reverse of worker order.
        time.sleep(0.05 * (3 - payload["worker_index"]))
        return {"Payload": io.BytesIO(json.dumps({"worker": payload["worker_index"],
                                                  "of": payload["worker_count"],
                                                  "url": payload["url"]}).encode("utf-8"))}

    monkeypatch.setattr(aws_lambda, "_import_boto3", lambda: _FakeBoto3(SimpleNamespace(invoke=invoke)))
    results = aws_lambda.invoke_lambda_workers("ld-worker", workers=3, payload_template={"url": "https://x"})
    assert [result["worker"] for result in results] == [0, 1, 2]
    assert all(result["of"] == 3 and result["url"] == "https://x" for result in results)


def test_lambda_non_json_payload_is_returned_raw(monkeypatch):
    fake = SimpleNamespace(invoke=lambda **_kwargs: {"Payload": b"not json"})
    monkeypatch.setattr(aws_lambda, "_import_boto3", lambda: _FakeBoto3(fake))
    assert aws_lambda.invoke_lambda_workers("f", workers=1, payload_template={}) == [{"raw": "not json"}]


def test_lambda_handler_reports_only_its_own_invocation(monkeypatch):
    import je_load_density.engine.asyncio_engine as engine

    async def fake_run(tasks, users, duration_seconds, http2):
        test_record_instance.test_record_list.append({"name": tasks[0]["request_url"]})
        return {"requests": len(test_record_instance.test_record_list),
                "failures": len(test_record_instance.error_record_list)}

    monkeypatch.setattr(engine, "run_async_load", fake_run)
    test_record_instance.clear_records()
    event = {"url": "https://x", "users": 1, "duration": 0.1}
    first = aws_lambda.lambda_worker_handler(event, None)
    second = aws_lambda.lambda_worker_handler(event, None)  # a warm start reuses the process
    assert first == second == {"requests": 1, "failures": 0}
    test_record_instance.clear_records()


def test_cloud_run_posts_overrides_with_a_bearer_token(monkeypatch):
    sent = {}

    class _Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        sent.update(url=request.full_url, headers=dict(request.header_items()),
                    body=json.loads(request.data), timeout=timeout)
        return _Response(b'{"name": "operations/1"}')

    monkeypatch.setattr(gcp_cloud_run, "_bearer_token", lambda _scopes: "tok")
    monkeypatch.setattr(gcp_cloud_run.urllib.request, "urlopen", fake_urlopen)
    result = gcp_cloud_run.run_cloud_run_job("proj", "asia-east1", "ld/job?x", parallelism=4, task_count=8)
    assert result == {"name": "operations/1"}
    assert sent["url"] == "https://run.googleapis.com/v2/projects/proj/locations/asia-east1/jobs/ld%2Fjob%3Fx:run"
    assert sent["headers"]["Authorization"] == "Bearer tok"
    assert sent["body"] == {"overrides": {"parallelism": 4, "taskCount": 8}}


def test_aci_creates_one_group_per_worker(monkeypatch):
    created = []
    lock = threading.Lock()

    def record(**kwargs):
        with lock:
            created.append(kwargs)
        return object()

    class _Model:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    fake = {
        "DefaultAzureCredential": lambda: "cred",
        "Client": lambda credential, subscription: SimpleNamespace(
            container_groups=SimpleNamespace(begin_create_or_update=record)),
        "Container": _Model, "ContainerGroup": _Model, "EnvironmentVariable": _Model,
        "ResourceRequests": _Model, "ResourceRequirements": _Model,
        "RestartPolicy": SimpleNamespace(never="Never"), "OSType": SimpleNamespace(linux="Linux"),
    }
    monkeypatch.setattr(azure_aci, "_import_azure", lambda: fake)
    responses = azure_aci.launch_aci_workers("sub", "rg", "eastasia", "ld:latest", workers=2,
                                             overrides_env={"TARGET": "https://x"})
    assert [response["name"] for response in responses] == ["loaddensity-worker-0", "loaddensity-worker-1"]
    group = created[1]["container_group"]
    assert created[1]["resource_group_name"] == "rg"
    assert group.restart_policy == "Never" and group.os_type == "Linux"
    env = {item.name: item.value for item in group.containers[0].environment_variables}
    assert env == {"TARGET": "https://x", "LD_WORKER_INDEX": "1", "LD_WORKER_COUNT": "2"}


@pytest.mark.parametrize("module, call", [
    (aws_fargate, lambda: aws_fargate.launch_fargate_workers("c", "t", 1, ["s"])),
    (aws_lambda, lambda: aws_lambda.invoke_lambda_workers("f", 1, {})),
])
def test_missing_sdk_is_a_clear_error(monkeypatch, module, call):
    monkeypatch.setitem(__import__("sys").modules, "boto3", None)
    with pytest.raises(RuntimeError, match="boto3 is required"):
        call()
