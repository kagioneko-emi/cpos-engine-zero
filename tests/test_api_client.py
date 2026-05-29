import json

import pytest

from cpos.api_client import CPOSClient, CPOSClientError


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {"ok": True}
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


class FakeSession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, data=None, headers=None, timeout=None):
        self.calls.append({"method": method, "url": url, "data": data, "headers": headers or {}, "timeout": timeout})
        return FakeResponse({"ok": True, "method": method})


def test_client_requires_https(tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("client-secret\n", encoding="utf-8")

    with pytest.raises(CPOSClientError, match="https_required"):
        CPOSClient("http://example.test", secret_file=str(secret))


def test_client_signs_get_with_secret_file_without_exposing_secret(tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("client-secret\n", encoding="utf-8")
    session = FakeSession()
    client = CPOSClient("https://example.test", secret_file=str(secret), agent_id="UnitClient", session=session)

    response = client.get("/tasks?limit=1")

    assert response.json()["ok"] is True
    call = session.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "https://example.test/tasks?limit=1"
    assert call["headers"]["X-Agent-Id"] == "UnitClient"
    assert call["headers"]["X-CPOS-Signature"]
    assert "client-secret" not in json.dumps(call)


def test_client_signs_post_json_with_registry_key_id(tmp_path):
    secret = tmp_path / "secret"
    registry = tmp_path / "registry.json"
    secret.write_text("registry-secret\n", encoding="utf-8")
    registry.write_text(
        json.dumps({"keys": {"active": {"secret_file": str(secret), "status": "active", "scopes": ["write:rollback"]}}}),
        encoding="utf-8",
    )
    session = FakeSession()
    client = CPOSClient("https://example.test/api", registry_file=str(registry), key_id="active", session=session)

    client.post("/tasks/rollback-latest", json={"target": "workspace/app.py", "confirm": True})

    call = session.calls[0]
    assert call["url"] == "https://example.test/api/tasks/rollback-latest"
    assert call["headers"]["X-CPOS-Key-Id"] == "active"
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["data"] == b'{"target":"workspace/app.py","confirm":true}'
    assert "registry-secret" not in str(call)


def test_client_rejects_params_because_signature_needs_exact_query(tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("client-secret\n", encoding="utf-8")
    client = CPOSClient("https://example.test", secret_file=str(secret), session=FakeSession())

    with pytest.raises(CPOSClientError, match="params_not_supported"):
        client.get("/tasks", params={"limit": 1})
