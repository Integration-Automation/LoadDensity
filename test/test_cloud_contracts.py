"""Cloud boundary contracts: no credentials or remote resources are used."""

import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from je_load_density.cloud import aws_fargate, aws_lambda, azure_aci, gcp_cloud_run


def test_cloud_launch_error_has_public_import():
    import je_load_density.cloud as cloud
    error_type = getattr(cloud, "CloudLaunchError", None)
    assert error_type is not None and issubclass(error_type, RuntimeError)


def test_lambda_warm_handler_clears_records_after_failed_invocation(monkeypatch):
    import je_load_density.engine.asyncio_engine as engine
    from je_load_density.utils.test_record.test_record_class import test_record_instance
    calls = []
    async def run(tasks, users, duration_seconds, http2):
        calls.append((tasks, users, duration_seconds, http2))
        assert test_record_instance.test_record_list == []
        assert test_record_instance.error_record_list == []
        test_record_instance.error_record_list.append({"name": "old-failure"})
        if len(calls) == 1:
            raise ValueError("controlled invocation failure")
        return {"requests": 1, "failures": 1}
    monkeypatch.setattr(engine, "run_async_load", run)
    event = {"url": "https://target.invalid", "users": 2, "duration": 0.5, "http2": True}
    try:
        with pytest.raises(ValueError, match="controlled"):
            aws_lambda.lambda_worker_handler(event, None)
        assert aws_lambda.lambda_worker_handler(event, None) == {"requests": 1, "failures": 1}
        assert calls == [([{"method": "get", "request_url": "https://target.invalid"}], 2, 0.5, True)] * 2
        assert event == {"url": "https://target.invalid", "users": 2, "duration": 0.5, "http2": True}
    finally:
        test_record_instance.clear_records()


class ServiceFailure(OSError):
    """Controllable SDK transport failure at the external service boundary."""


class BotoStub:
    def __init__(self, operation):
        self.operation = operation
        self.calls = []

    def client(self, service, region_name=None):
        self.calls.append((service, region_name))
        return SimpleNamespace(run_task=self.operation, invoke=self.operation)


def aws_stub(monkeypatch, module, operation):
    stub = BotoStub(operation)
    monkeypatch.setattr(module, "_import_boto3", lambda: stub)
    return stub


@pytest.mark.parametrize("count", [0, -1, True, 1.5, "2"])
@pytest.mark.parametrize("backend", ["fargate", "lambda", "aci"])
def test_invalid_worker_counts_fail_before_sdk_import(monkeypatch, count, backend):
    def forbidden():
        pytest.fail("invalid configuration reached SDK import")
    module = {"fargate": aws_fargate, "lambda": aws_lambda, "aci": azure_aci}[backend]
    monkeypatch.setattr(module, "_import_azure" if backend == "aci" else "_import_boto3", forbidden)
    with pytest.raises(ValueError, match="workers"):
        if backend == "fargate":
            module.launch_fargate_workers("c", "t", count, ["s"])
        elif backend == "lambda":
            module.invoke_lambda_workers("f", count, {})
        else:
            module.launch_aci_workers("sub", "rg", "region", "image", count)


@pytest.mark.parametrize("kwargs", [
    {"subnets": []}, {"subnets": [""]}, {"subnets": ["s"] * 17},
    {"security_groups": ["g"] * 6}, {"overrides_env": {"LD_WORKER_INDEX": "99"}},
    {"overrides_env": {"N": 1}}, {"cluster": ""}, {"assign_public_ip": "yes"},
])
def test_fargate_invalid_resources_fail_before_sdk(monkeypatch, kwargs):
    monkeypatch.setattr(aws_fargate, "_import_boto3", lambda: pytest.fail("SDK reached"))
    arguments = dict(cluster="c", task_definition="t", workers=1, subnets=["s"])
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        aws_fargate.launch_fargate_workers(**arguments)


@pytest.mark.parametrize("bad", [
    {"tasks": [], "failures": [{"reason": "RESOURCE:CPU"}]},
    {"tasks": []}, {"tasks": [{}]}, {"tasks": "bad"}, None,
    {"tasks": [{"taskArn": 123}]}, {"tasks": [{"taskArn": " "}]},
])
def test_fargate_failed_or_malformed_launch_retains_prior_tasks(monkeypatch, bad):
    calls = []
    def run(**kwargs):
        calls.append(kwargs)
        return {"tasks": [{"taskArn": "arn:first"}], "failures": []} if len(calls) == 1 else bad
    aws_stub(monkeypatch, aws_fargate, run)
    with pytest.raises(RuntimeError) as caught:
        aws_fargate.launch_fargate_workers("cluster", "definition", 3, ["s"])
    assert caught.value.failed_workers == [1]
    assert caught.value.responses[0]["tasks"][0]["taskArn"] == "arn:first"
    assert len(calls) == 2
    assert calls[1]["count"] == 1
    assert calls[1]["overrides"]["containerOverrides"][0]["environment"][0]["value"] == "1"


def test_fargate_response_with_tasks_and_failures_preserves_accepted_task(monkeypatch):
    aws_stub(monkeypatch, aws_fargate, lambda **kwargs: {
        "tasks": [{"taskArn": "arn:accepted"}], "failures": [{"reason": "partial"}]})
    with pytest.raises(RuntimeError) as caught:
        aws_fargate.launch_fargate_workers("c", "t", 1, ["s"])
    assert caught.value.responses[0]["tasks"][0]["taskArn"] == "arn:accepted"
    assert caught.value.failed_workers == [0]


@pytest.mark.parametrize("module", [aws_fargate, aws_lambda])
@pytest.mark.parametrize("reason", ["credentials", "permission denied", "timeout", "throttled", "service error"])
def test_aws_service_errors_preserve_cause_without_resending(monkeypatch, module, reason):
    calls = []
    error = ServiceFailure(reason)
    def fail(**kwargs):
        calls.append(kwargs)
        raise error
    aws_stub(monkeypatch, module, fail)
    with pytest.raises(RuntimeError) as caught:
        if module is aws_fargate:
            module.launch_fargate_workers("c", "t", 1, ["s"])
        else:
            module.invoke_lambda_workers("f", 1, {})
    assert caught.value.__cause__ is error
    assert caught.value.failed_workers == [0]
    assert caught.value.responses == []
    assert len(calls) == 1


@pytest.mark.parametrize("response", [
    {"StatusCode": 200, "FunctionError": "Unhandled", "Payload": b'{"errorMessage":"bad"}'},
    {"StatusCode": 500, "Payload": b'{}'}, {"Payload": b'{}'},
    {"StatusCode": 200, "Payload": b'[]'}, {"StatusCode": 200, "Payload": b'null'},
    {"StatusCode": 200, "Payload": b'\xff'}, None,
    {"StatusCode": 200}, {"StatusCode": 200, "Payload": b""},
    {"StatusCode": 200, "FunctionError": "", "Payload": b"{}"},
])
def test_lambda_bad_responses_fail_with_worker_identity(monkeypatch, response):
    aws_stub(monkeypatch, aws_lambda, lambda **kwargs: response)
    with pytest.raises(RuntimeError) as caught:
        aws_lambda.invoke_lambda_workers("f", 1, {})
    assert caught.value.failed_workers == [0]


def test_lambda_event_reports_acceptance_without_execution_success(monkeypatch):
    calls = []
    def invoke(**kwargs):
        calls.append(kwargs)
        return {"StatusCode": 202, "Payload": io.BytesIO(b"")}
    aws_stub(monkeypatch, aws_lambda, invoke)
    template = {"tasks": [{"url": "https://example.invalid"}]}
    result = aws_lambda.invoke_lambda_workers("f", 2, template, invocation_type="Event")
    assert result == [{"status": "accepted", "worker_index": 0, "StatusCode": 202},
                      {"status": "accepted", "worker_index": 1, "StatusCode": 202}]
    assert all(call["FunctionName"] == "f" and call["InvocationType"] == "Event" for call in calls)
    assert sorted(json.loads(call["Payload"])["worker_index"] for call in calls) == [0, 1]
    assert all(json.loads(call["Payload"])["worker_count"] == 2 for call in calls)
    assert template == {"tasks": [{"url": "https://example.invalid"}]}


def test_lambda_partial_failure_collects_other_results_and_closes_streams(monkeypatch):
    streams = []
    calls = []
    def invoke(**kwargs):
        index = json.loads(kwargs["Payload"])["worker_index"]
        calls.append(index)
        stream = io.BytesIO(json.dumps({"worker": index}).encode())
        streams.append(stream)
        response = {"StatusCode": 200, "Payload": stream}
        if index == 1:
            response["FunctionError"] = "Handled"
        return response
    aws_stub(monkeypatch, aws_lambda, invoke)
    with pytest.raises(RuntimeError) as caught:
        aws_lambda.invoke_lambda_workers("f", 3, {})
    assert caught.value.responses == [{"worker": 0}, {"worker": 2}]
    assert caught.value.failed_workers == [1]
    assert caught.value.response["worker_payload"] == {"worker": 1}
    assert sorted(calls) == [0, 1, 2]
    assert all(stream.closed for stream in streams)


def test_lambda_stream_timeout_retains_other_results_and_closes_payload(monkeypatch):
    error = ServiceFailure("read timeout")
    class Stream(io.BytesIO):
        def read(self):
            raise error
    stream = Stream()
    def invoke(**kwargs):
        index = json.loads(kwargs["Payload"])["worker_index"]
        return {"StatusCode": 200, "Payload": stream if index else b'{"worker":0}'}
    aws_stub(monkeypatch, aws_lambda, invoke)
    with pytest.raises(RuntimeError) as caught:
        aws_lambda.invoke_lambda_workers("f", 2, {})
    assert caught.value.responses == [{"worker": 0}]
    assert caught.value.failed_workers == [1]
    assert caught.value.__cause__ is error
    assert stream.closed


@pytest.mark.parametrize("invocation,status", [("RequestResponse", 200), ("Event", 202), ("DryRun", 204)])
@pytest.mark.parametrize("malformed_attribute", ["read", "close"])
def test_lambda_noncallable_payload_methods_retain_all_other_worker_results(
        monkeypatch, invocation, status, malformed_attribute):
    calls = []
    successful_streams = []
    malformed_closed = []
    bad = SimpleNamespace(read=lambda: b"{}", close=lambda: malformed_closed.append(True))
    setattr(bad, malformed_attribute, 123)
    def invoke(**kwargs):
        index = json.loads(kwargs["Payload"])["worker_index"]
        calls.append(index)
        if index == 1:
            return {"StatusCode": status, "Payload": bad}
        body = json.dumps({"worker": index}).encode() if invocation == "RequestResponse" else b""
        stream = io.BytesIO(body)
        successful_streams.append(stream)
        return {"StatusCode": status, "Payload": stream}
    aws_stub(monkeypatch, aws_lambda, invoke)
    with pytest.raises(RuntimeError) as caught:
        aws_lambda.invoke_lambda_workers("f", 3, {}, invocation_type=invocation)
    if invocation == "RequestResponse":
        assert caught.value.responses == [{"worker": 0}, {"worker": 2}]
    else:
        state = "accepted" if invocation == "Event" else "validated"
        assert caught.value.responses == [{"status": state, "worker_index": 0, "StatusCode": status},
                                          {"status": state, "worker_index": 2, "StatusCode": status}]
    assert caught.value.failed_workers == [1]
    assert isinstance(caught.value.__cause__, ValueError)
    assert sorted(calls) == [0, 1, 2]
    assert all(stream.closed for stream in successful_streams)
    assert malformed_closed == ([True] if malformed_attribute == "read" else [])


def test_lambda_sdk_internal_type_error_propagates_without_reclassification(monkeypatch):
    error = TypeError("controlled SDK internal defect")
    calls = []
    def invoke(**kwargs):
        calls.append(kwargs)
        raise error
    aws_stub(monkeypatch, aws_lambda, invoke)
    with pytest.raises(TypeError) as caught:
        aws_lambda.invoke_lambda_workers("f", 1, {})
    assert caught.value is error
    assert len(calls) == 1


@pytest.mark.parametrize("invocation,status", [("Event", 200), ("DryRun", 200)])
def test_lambda_acceptance_modes_reject_wrong_status(monkeypatch, invocation, status):
    aws_stub(monkeypatch, aws_lambda, lambda **kwargs: {"StatusCode": status})
    with pytest.raises(RuntimeError) as caught:
        aws_lambda.invoke_lambda_workers("f", 1, {}, invocation_type=invocation)
    assert caught.value.failed_workers == [0]


def test_lambda_dry_run_reports_validation(monkeypatch):
    aws_stub(monkeypatch, aws_lambda, lambda **kwargs: {"StatusCode": 204})
    assert aws_lambda.invoke_lambda_workers("f", 1, {}, invocation_type="DryRun") == [
        {"status": "validated", "worker_index": 0, "StatusCode": 204}]


@pytest.mark.parametrize("kwargs", [
    {"invocation_type": "invalid"}, {"payload_template": []}, {"function_name": ""},
])
def test_lambda_invalid_configuration_fails_before_sdk(monkeypatch, kwargs):
    monkeypatch.setattr(aws_lambda, "_import_boto3", lambda: pytest.fail("SDK reached"))
    arguments = dict(function_name="f", workers=1, payload_template={})
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        aws_lambda.invoke_lambda_workers(**arguments)


@pytest.mark.parametrize("kwargs", [
    {"parallelism": 2}, {"task_count": 0}, {"task_count": True}, {"task_count": 1.5},
    {"timeout": 0}, {"timeout": float("nan")}, {"timeout": float("inf")},
    {"container_overrides": [{}]}, {"container_overrides": [{"name": "c", "parallelism": 2}]},
    {"container_overrides": [{"name": "c", "args": [1]}]}, {"project": ""},
    {"container_overrides": [{"env": [{"name": "N", "value": "x", "valueSource": {}}]}]},
    {"container_overrides": [{"env": [{"name": "N", "valueSource": "invalid"}]}]},
    {"container_overrides": [{"env": [{"name": "N", "valueSource": {"unknown": "bad"}}]}]},
])
def test_cloud_run_invalid_configuration_fails_before_auth(monkeypatch, kwargs):
    monkeypatch.setattr(gcp_cloud_run, "_bearer_token", lambda scopes: pytest.fail("auth reached"))
    arguments = dict(project="p", region="r", job_name="j")
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        gcp_cloud_run.run_cloud_run_job(**arguments)


@pytest.mark.parametrize("body", [b'[]', b'null', b'{}', b'not json', b'\xff',
                                  b'{"name":"operations/x","error":{"code":13}}'])
def test_cloud_run_bad_operation_is_failure(monkeypatch, body):
    monkeypatch.setattr(gcp_cloud_run, "_bearer_token", lambda scopes: "token")
    monkeypatch.setattr(gcp_cloud_run.urllib.request, "urlopen", lambda req, timeout: io.BytesIO(body))
    with pytest.raises(RuntimeError):
        gcp_cloud_run.run_cloud_run_job("p", "r", "j")


def test_cloud_run_refreshes_credentials_for_each_run(monkeypatch):
    refreshed = []
    credentials = SimpleNamespace(token=None)
    def refresh(request):
        refreshed.append(request)
        credentials.token = "token-" + str(len(refreshed))
    credentials.refresh = refresh
    auth = SimpleNamespace(default=lambda scopes: (credentials, "project"))
    transport = SimpleNamespace(Request=lambda: "refresh-request")
    monkeypatch.setattr(gcp_cloud_run, "_import_google_auth", lambda: (auth, transport))
    headers = []
    def open_response(request, timeout):
        headers.append(request.get_header("Authorization"))
        assert timeout == 30.0
        assert json.loads(request.data) == {"overrides": {"taskCount": 3}}
        return io.BytesIO(b'{"name":"operations/x"}')
    monkeypatch.setattr(gcp_cloud_run.urllib.request, "urlopen", open_response)
    gcp_cloud_run.run_cloud_run_job("p", "r", "j", task_count=3)
    gcp_cloud_run.run_cloud_run_job("p", "r", "j", task_count=3)
    assert headers == ["Bearer token-1", "Bearer token-2"]
    assert refreshed == ["refresh-request", "refresh-request"]


def test_cloud_run_empty_refreshed_token_fails_before_http(monkeypatch):
    credentials = SimpleNamespace(token=None, refresh=lambda request: None)
    monkeypatch.setattr(gcp_cloud_run, "_import_google_auth", lambda: (
        SimpleNamespace(default=lambda scopes: (credentials, "p")), SimpleNamespace(Request=lambda: None)))
    monkeypatch.setattr(gcp_cloud_run.urllib.request, "urlopen", lambda *args, **kwargs: pytest.fail("HTTP reached"))
    with pytest.raises(RuntimeError, match="token"):
        gcp_cloud_run.run_cloud_run_job("p", "r", "j")


@pytest.mark.parametrize("stage", ["default", "refresh", "http"])
def test_cloud_run_credentials_and_timeout_errors_propagate_once(monkeypatch, stage):
    error = ServiceFailure(stage)
    calls = []
    def fail(*args, **kwargs):
        calls.append(stage)
        raise error
    credentials = SimpleNamespace(token="token", refresh=fail if stage == "refresh" else lambda req: None)
    auth = SimpleNamespace(default=fail if stage == "default" else lambda scopes: (credentials, "p"))
    monkeypatch.setattr(gcp_cloud_run, "_import_google_auth", lambda: (auth, SimpleNamespace(Request=lambda: None)))
    monkeypatch.setattr(gcp_cloud_run.urllib.request, "urlopen", fail if stage == "http" else
                        lambda *args, **kwargs: pytest.fail("authentication failure reached HTTP"))
    with pytest.raises(ServiceFailure) as caught:
        gcp_cloud_run.run_cloud_run_job("p", "r", "j")
    assert caught.value is error
    assert calls == [stage]


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_cloud_run_real_local_http_errors_propagate_without_retry(monkeypatch, status):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append((self.path, self.headers["Authorization"],
                             json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            self.send_response(status)
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"denied"}}')
        def log_message(self, *args):
            pass
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original_open = gcp_cloud_run.urllib.request.urlopen
    def local_open(request, timeout):
        request.full_url = f"http://127.0.0.1:{server.server_port}/job:run"
        return original_open(request, timeout=timeout)
    monkeypatch.setattr(gcp_cloud_run, "_bearer_token", lambda scopes: "local-token")
    monkeypatch.setattr(gcp_cloud_run.urllib.request, "urlopen", local_open)
    try:
        with pytest.raises(HTTPError) as caught:
            gcp_cloud_run.run_cloud_run_job("p", "r", "j", task_count=2)
        assert caught.value.code == status
        caught.value.close()
        assert requests == [("/job:run", "Bearer local-token", {"overrides": {"taskCount": 2}})]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class Model:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def aci_stub(monkeypatch, create):
    models = {name: Model for name in ["Container", "ContainerGroup", "EnvironmentVariable",
                                      "ResourceRequests", "ResourceRequirements"]}
    models.update(DefaultAzureCredential=lambda: "credential",
                  Client=lambda credential, subscription: SimpleNamespace(
                      container_groups=SimpleNamespace(begin_create_or_update=create)),
                  RestartPolicy=SimpleNamespace(never="Never"), OSType=SimpleNamespace(linux="Linux"))
    monkeypatch.setattr(azure_aci, "_import_azure", lambda: models)


@pytest.mark.parametrize("kwargs", [
    {"cpu": 0}, {"cpu": True}, {"cpu": float("inf")}, {"memory_gb": -1},
    {"memory_gb": float("nan")}, {"name_prefix": "Bad Prefix"}, {"name_prefix": "x" * 64},
    {"overrides_env": {"LD_WORKER_COUNT": "9"}}, {"image": ""},
    {"overrides_env": {"BAD NAME": "x"}}, {"overrides_env": {"NAME_": "x"}},
    {"overrides_env": {"N" * 64: "x"}},
])
def test_aci_invalid_resource_parameters_fail_before_sdk(monkeypatch, kwargs):
    monkeypatch.setattr(azure_aci, "_import_azure", lambda: pytest.fail("SDK reached"))
    with pytest.raises(ValueError):
        azure_aci.launch_aci_workers("sub", "rg", "region", kwargs.pop("image", "image"), 1, **kwargs)


def test_aci_names_are_unique_across_launches_and_provisioning_is_checked(monkeypatch):
    calls = []
    polled = []
    def create(**kwargs):
        calls.append(kwargs)
        def result():
            polled.append(kwargs["container_group_name"])
            return SimpleNamespace(id="resource/" + kwargs["container_group_name"], provisioning_state="Succeeded")
        return SimpleNamespace(result=result)
    aci_stub(monkeypatch, create)
    first = azure_aci.launch_aci_workers("sub", "rg", "region", "image", 2, cpu=2, memory_gb=4)
    second = azure_aci.launch_aci_workers("sub", "rg", "region", "image", 2)
    names = [entry["name"] for entry in first + second]
    assert len(set(names)) == 4
    assert polled == names
    assert all(entry["status"] == "Succeeded" and entry["resource_id"] for entry in first + second)
    group = calls[1]["container_group"]
    assert group.containers[0].resources.requests.cpu == 2
    assert group.containers[0].resources.requests.memory_in_gb == 4
    assert group.location == "region" and group.restart_policy == "Never"
    assert calls[1]["resource_group_name"] == "rg"
    assert {item.name: item.value for item in group.containers[0].environment_variables} == {
        "LD_WORKER_INDEX": "1", "LD_WORKER_COUNT": "2"}


def test_aci_prefix_allows_internal_consecutive_hyphens(monkeypatch):
    aci_stub(monkeypatch, lambda **kwargs: SimpleNamespace(result=lambda: SimpleNamespace(
        id="id", provisioning_state="Succeeded")))
    responses = azure_aci.launch_aci_workers("sub", "rg", "region", "image", 1, name_prefix="a--b")
    assert responses[0]["name"].startswith("a--b-")


@pytest.mark.parametrize("reason", ["credentials", "permission", "timeout", "throttle", "service"])
def test_aci_poller_failure_retains_prior_success_and_never_resubmits(monkeypatch, reason):
    calls = []
    error = ServiceFailure(reason)
    def create(**kwargs):
        calls.append(kwargs)
        index = len(calls) - 1
        def result():
            if index == 1:
                raise error
            return SimpleNamespace(id="id/first", provisioning_state="Succeeded")
        return SimpleNamespace(result=result)
    aci_stub(monkeypatch, create)
    with pytest.raises(RuntimeError) as caught:
        azure_aci.launch_aci_workers("sub", "rg", "region", "image", 3)
    assert caught.value.__cause__ is error
    assert caught.value.failed_workers == [1]
    assert caught.value.responses[0]["resource_id"] == "id/first"
    assert len(calls) == 2


@pytest.mark.parametrize("result", [None, SimpleNamespace(id="id", provisioning_state="Failed"),
                                    SimpleNamespace(id=None, provisioning_state="Succeeded")])
def test_aci_malformed_or_failed_provisioning_is_not_success(monkeypatch, result):
    aci_stub(monkeypatch, lambda **kwargs: SimpleNamespace(result=lambda: result))
    with pytest.raises(RuntimeError) as caught:
        azure_aci.launch_aci_workers("sub", "rg", "region", "image", 1)
    assert caught.value.failed_workers == [0]


def test_aci_malformed_poller_retains_attempted_resource_name(monkeypatch):
    calls = []
    aci_stub(monkeypatch, lambda **kwargs: calls.append(kwargs) or None)
    with pytest.raises(RuntimeError) as caught:
        azure_aci.launch_aci_workers("sub", "rg", "region", "image", 1)
    assert caught.value.response["name"] == calls[0]["container_group_name"]
    assert len(calls) == 1
