"""Optional extra-specific contracts against official SDK serializers/stubs.

The dependency-free cloud contracts run on every installation. These tests also
run when the relevant cloud extra is installed; no SDK request reaches a cloud.
"""

import io
import json
from types import SimpleNamespace

import pytest

from je_load_density.cloud import aws_fargate, aws_lambda, azure_aci, gcp_cloud_run


def aws_client(service):
    boto3 = pytest.importorskip("boto3", reason="official AWS contract requires aws/cloud extra")
    return boto3.client(service, region_name="us-east-1", aws_access_key_id="test-key",
                        aws_secret_access_key="test-secret", endpoint_url="https://aws.invalid")


def test_official_ecs_stubber_validates_payload_and_reports_failures(monkeypatch):
    client = aws_client("ecs")
    from botocore.stub import Stubber
    monkeypatch.setattr(aws_fargate, "_import_boto3", lambda: SimpleNamespace(client=lambda *a, **k: client))
    expected = {
        "cluster": "cluster", "taskDefinition": "definition", "launchType": "FARGATE", "count": 1,
        "networkConfiguration": {"awsvpcConfiguration": {
            "subnets": ["subnet-1"], "securityGroups": ["sg-1"], "assignPublicIp": "ENABLED"}},
        "overrides": {"containerOverrides": [{"name": "worker", "environment": [
            {"name": "TARGET", "value": "https://target.invalid"},
            {"name": "LD_WORKER_INDEX", "value": "0"}, {"name": "LD_WORKER_COUNT", "value": "1"}]}]},
    }
    with Stubber(client) as stub:
        stub.add_response("run_task", {"tasks": [], "failures": [{"reason": "RESOURCE:CPU"}]}, expected)
        with pytest.raises(RuntimeError) as caught:
            aws_fargate.launch_fargate_workers("cluster", "definition", 1, ["subnet-1"], ["sg-1"],
                                               True, container_name="worker",
                                               overrides_env={"TARGET": "https://target.invalid"})
        assert caught.value.failed_workers == [0]
        assert caught.value.response["failures"][0]["reason"] == "RESOURCE:CPU"
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("code", ["AccessDeniedException", "TooManyRequestsException", "ServiceException"])
def test_official_lambda_service_errors_retain_client_error(monkeypatch, code):
    client = aws_client("lambda")
    from botocore.exceptions import ClientError
    from botocore.stub import Stubber
    monkeypatch.setattr(aws_lambda, "_import_boto3", lambda: SimpleNamespace(client=lambda *a, **k: client))
    expected = {"FunctionName": "worker", "InvocationType": "RequestResponse",
                "Payload": b'{"worker_index": 0, "worker_count": 1}'}
    with Stubber(client) as stub:
        stub.add_client_error("invoke", service_error_code=code, service_message="controlled",
                              http_status_code={"AccessDeniedException": 403, "TooManyRequestsException": 429,
                                                "ServiceException": 500}[code], expected_params=expected)
        with pytest.raises(RuntimeError) as caught:
            aws_lambda.invoke_lambda_workers("worker", 1, {})
        assert isinstance(caught.value.__cause__, ClientError)
        assert caught.value.__cause__.response["Error"]["Code"] == code
        assert caught.value.responses == []
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("failure", ["credentials", "timeout"])
def test_official_aws_credential_and_timeout_exceptions_are_chained(monkeypatch, failure):
    client = aws_client("lambda")
    from botocore.exceptions import NoCredentialsError, ReadTimeoutError
    error = NoCredentialsError() if failure == "credentials" else ReadTimeoutError(endpoint_url="https://aws.invalid")
    def fail(**kwargs):
        raise error
    monkeypatch.setattr(client, "invoke", fail)
    monkeypatch.setattr(aws_lambda, "_import_boto3", lambda: SimpleNamespace(client=lambda *a, **k: client))
    with pytest.raises(RuntimeError) as caught:
        aws_lambda.invoke_lambda_workers("worker", 1, {})
    assert caught.value.__cause__ is error
    assert caught.value.failed_workers == [0]


def test_official_lambda_streamingbody_closes_on_function_error(monkeypatch):
    client = aws_client("lambda")
    from botocore.response import StreamingBody
    from botocore.stub import Stubber
    body = b'{"errorMessage":"controlled function error"}'
    raw = io.BytesIO(body)
    stream = StreamingBody(raw, len(body))
    monkeypatch.setattr(aws_lambda, "_import_boto3", lambda: SimpleNamespace(client=lambda *a, **k: client))
    with Stubber(client) as stub:
        stub.add_response("invoke", {"StatusCode": 200, "FunctionError": "Unhandled", "Payload": stream},
                          {"FunctionName": "worker", "InvocationType": "RequestResponse",
                           "Payload": b'{"worker_index": 0, "worker_count": 1}'})
        with pytest.raises(RuntimeError) as caught:
            aws_lambda.invoke_lambda_workers("worker", 1, {})
        assert caught.value.response["FunctionError"] == "Unhandled"
        assert raw.closed
        stub.assert_no_pending_responses()


def test_official_azure_serialization_and_poller_result_without_network(monkeypatch):
    pytest.importorskip("azure.identity", reason="official Azure contract requires azure/cloud extra")
    pytest.importorskip("azure.mgmt.containerinstance", reason="official Azure contract requires azure/cloud extra")
    from azure.core.credentials import AccessToken
    from azure.core.pipeline.transport import HttpResponse, HttpTransport
    from azure.mgmt.containerinstance import ContainerInstanceManagementClient

    requests = []
    class Response(HttpResponse):
        def __init__(self, request):
            super().__init__(request, None)
            self.status_code = 201
            self.headers = {"Content-Type": "application/json"}
        def body(self):
            resource_id = self.request.url.split("?")[0].removeprefix("https://management.azure.com")
            return json.dumps({"id": resource_id, "name": resource_id.rsplit("/", 1)[-1], "location": "eastus",
                               "properties": {"provisioningState": "Succeeded", "osType": "Linux",
                                              "containers": []}}).encode()
    class Transport(HttpTransport):
        def open(self):
            pass
        def close(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def send(self, request, **kwargs):
            requests.append(request)
            return Response(request)
    credential = SimpleNamespace(get_token=lambda *args, **kwargs: AccessToken("stub-token", 9999999999))
    official_models = azure_aci._import_azure()
    official_models["DefaultAzureCredential"] = lambda: credential
    official_models["Client"] = lambda cred, sub: ContainerInstanceManagementClient(
        cred, sub, transport=Transport(), retry_total=0)
    monkeypatch.setattr(azure_aci, "_import_azure", lambda: official_models)
    result = azure_aci.launch_aci_workers("sub", "rg", "eastus", "image:v1", 1, cpu=2, memory_gb=3,
                                         overrides_env={"TARGET": "https://target.invalid"})
    assert result[0]["status"] == "Succeeded"
    assert result[0]["resource_id"].endswith("/containerGroups/" + result[0]["name"])
    assert len(requests) == 1 and requests[0].method == "PUT"
    resource_path = f"/resourceGroups/rg/providers/Microsoft.ContainerInstance/containerGroups/{result[0]['name']}?"
    assert resource_path in requests[0].url
    payload = json.loads(requests[0].body)
    assert payload["location"] == "eastus"
    assert payload["properties"]["restartPolicy"] == "Never"
    assert payload["properties"]["containers"][0]["properties"]["resources"]["requests"] == {
        "cpu": 2.0, "memoryInGB": 3.0}
    assert requests[0].headers["Authorization"] == "Bearer stub-token"


@pytest.mark.parametrize("failure", ["credentials", "permission", "timeout"])
def test_official_azure_errors_are_chained(monkeypatch, failure):
    pytest.importorskip("azure.core", reason="official Azure errors require azure/cloud extra")
    from azure.core.exceptions import ClientAuthenticationError, HttpResponseError, ServiceRequestError
    errors = {"credentials": ClientAuthenticationError, "permission": HttpResponseError, "timeout": ServiceRequestError}
    error = errors[failure]("controlled")
    def create(**kwargs):
        return SimpleNamespace(result=lambda: fail())
    def fail():
        raise error
    from test.test_cloud_contracts import aci_stub
    aci_stub(monkeypatch, create)
    with pytest.raises(RuntimeError) as caught:
        azure_aci.launch_aci_workers("sub", "rg", "eastus", "image", 1)
    assert caught.value.__cause__ is error
    assert caught.value.failed_workers == [0]


def test_official_google_refresh_error_prevents_http(monkeypatch):
    pytest.importorskip("google.auth", reason="official Google errors require gcp/cloud extra")
    from google.auth.exceptions import RefreshError
    error = RefreshError("controlled refresh failure")
    def refresh(request):
        raise error
    credentials = SimpleNamespace(token=None, refresh=refresh)
    monkeypatch.setattr(gcp_cloud_run, "_import_google_auth", lambda: (
        SimpleNamespace(default=lambda scopes: (credentials, "p")), SimpleNamespace(Request=lambda: None)))
    monkeypatch.setattr(gcp_cloud_run.urllib.request, "urlopen", lambda *args, **kwargs: pytest.fail("HTTP reached"))
    with pytest.raises(RefreshError) as caught:
        gcp_cloud_run.run_cloud_run_job("p", "r", "j")
    assert caught.value is error
