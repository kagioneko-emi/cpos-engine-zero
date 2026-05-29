from agents.main_agent import MainAgent
from cpos.pointer_os import PointerManager
from cpos.task_tape import TaskTapeStore
import server


def configure_task_test_agent(tmp_path):
    test_agent = MainAgent()
    test_agent.project_root = str(tmp_path)
    test_agent.audit_log_path = str(tmp_path / "cpos" / "audit_log.jsonl")
    test_agent.pointers_path = str(tmp_path / "cpos" / "pointers.jsonl")
    test_agent.pointer_manager = PointerManager(test_agent.pointers_path, test_agent.audit_log_path)
    test_agent.task_tape_path = str(tmp_path / "tapes" / "task_runs.jsonl")
    test_agent.task_checkpoint_path = str(tmp_path / "tapes" / "task_checkpoints.jsonl")
    test_agent.task_tape = TaskTapeStore(test_agent.task_tape_path, test_agent.task_checkpoint_path)
    server.agent = test_agent
    return test_agent


def test_task_api_summary_events_checkpoints_and_rollback(tmp_path):
    test_agent = configure_task_test_agent(tmp_path)
    target = tmp_path / "workspace" / "app.py"
    target.parent.mkdir()
    target.write_text("old\n", encoding="utf-8")
    task_id = test_agent.task_tape.create_task(target=str(target), action="unit_test")
    checkpoint = test_agent.task_tape.create_checkpoint(task_id=task_id, target=str(target), content="old\n")
    test_agent.task_tape.append_event(task_id=task_id, event="verification_completed", target=str(target), checkpoint_id=checkpoint.checkpoint_id, status="success")
    target.write_text("new\n", encoding="utf-8")

    client = server.app.test_client()

    summary = client.get("/tasks")
    assert summary.status_code == 200
    assert summary.get_json()["summary"]["task_count"] == 1
    assert summary.get_json()["summary"]["checkpoint_count"] == 1

    events = client.get(f"/tasks/events?task_id={task_id}")
    assert events.status_code == 200
    events_payload = events.get_json()
    assert events_payload["count"] == 3
    assert [row["event"] for row in events_payload["events"]] == ["task_started", "checkpoint_created", "verification_completed"]

    checkpoints = client.get(f"/tasks/checkpoints?target={str(target)}")
    assert checkpoints.status_code == 200
    checkpoints_payload = checkpoints.get_json()
    assert checkpoints_payload["count"] == 1
    assert checkpoints_payload["checkpoints"][0]["checkpoint_id"] == checkpoint.checkpoint_id
    assert checkpoints_payload["checkpoints"][0]["content_size"] == len("old\n")
    assert "content" not in checkpoints_payload["checkpoints"][0]

    rollback = client.post("/tasks/rollback-latest", json={"target": str(target), "confirm": True})
    assert rollback.status_code == 200
    rollback_payload = rollback.get_json()
    assert rollback_payload["ok"] is True
    assert rollback_payload["checkpoint"]["checkpoint_id"] == checkpoint.checkpoint_id
    assert "content" not in rollback_payload["checkpoint"]
    assert target.read_text(encoding="utf-8") == "old\n"


def test_task_api_rollback_requires_confirm_and_target_or_task(tmp_path):
    configure_task_test_agent(tmp_path)
    client = server.app.test_client()

    no_confirm = client.post("/tasks/rollback-latest", json={"target": str(tmp_path / "app.py")})
    assert no_confirm.status_code == 400
    assert no_confirm.get_json()["error"] == "confirm_required"

    no_target = client.post("/tasks/rollback-latest", json={"confirm": True})
    assert no_target.status_code == 400
    assert no_target.get_json()["error"] == "task_id_or_target_required"

    missing = client.post("/tasks/rollback-latest", json={"target": str(tmp_path / "missing.py"), "confirm": True})
    assert missing.status_code == 404
    assert missing.get_json()["error"] == "checkpoint_not_found"


class FakeArchitect:
    def __init__(self, fixed_code):
        self.fixed_code = fixed_code

    def propose_fix(self, target_file, content, finding, sandbox_output=None):
        return self.fixed_code


class FakeSandbox:
    def run_command(self, target_dir, command):
        return {"exit_code": 0, "stdout": "ok\n", "stderr": ""}


def test_task_review_api_lists_approves_and_rejects_pending_fix(tmp_path):
    test_agent = configure_task_test_agent(tmp_path)
    target = tmp_path / "workspace" / "app.py"
    target.parent.mkdir()
    original = "bad = eval('1+1')\n"
    target.write_text(original, encoding="utf-8")
    test_agent.architect = FakeArchitect("good = 2\n")
    test_agent.sandbox = FakeSandbox()
    pending = test_agent.apply_autonomous_fix(str(target), original, [{"rule_id": "PY-MISTAKE-0002", "severity": "high"}], "")
    client = server.app.test_client()

    reviews = client.get("/tasks/reviews")
    assert reviews.status_code == 200
    reviews_payload = reviews.get_json()
    assert reviews_payload["count"] == 1
    assert reviews_payload["reviews"][0]["task_id"] == pending["task_id"]
    assert "proposed_code" not in reviews_payload["reviews"][0]["payload"]

    denied = client.post(f"/tasks/{pending['task_id']}/approve-fix", json={})
    assert denied.status_code == 400
    assert denied.get_json()["error"] == "confirm_required"
    assert target.read_text(encoding="utf-8") == original

    approved = client.post(f"/tasks/{pending['task_id']}/approve-fix", json={"confirm": True})
    assert approved.status_code == 200
    assert approved.get_json()["ok"] is True
    assert target.read_text(encoding="utf-8") == "good = 2\n"

    reviews_after = client.get("/tasks/reviews")
    assert reviews_after.get_json()["count"] == 0


def test_task_review_api_rejects_pending_fix(tmp_path):
    test_agent = configure_task_test_agent(tmp_path)
    target = tmp_path / "workspace" / "app.py"
    target.parent.mkdir()
    original = "bad = eval('1+1')\n"
    target.write_text(original, encoding="utf-8")
    test_agent.architect = FakeArchitect("good = 2\n")
    test_agent.sandbox = FakeSandbox()
    pending = test_agent.apply_autonomous_fix(str(target), original, [{"rule_id": "PY-MISTAKE-0002", "severity": "high"}], "")
    client = server.app.test_client()

    rejected = client.post(f"/tasks/{pending['task_id']}/reject-fix", json={"reason": "unsafe_change"})

    assert rejected.status_code == 200
    assert rejected.get_json()["status"] == "rejected"
    assert target.read_text(encoding="utf-8") == original
    assert client.get("/tasks/reviews").get_json()["count"] == 0


def test_https_enforcement_when_configured(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_ENFORCE_HTTPS", "true")

    blocked = client.get("/health")
    allowed = client.get("/health", headers={"X-Forwarded-Proto": "https"})

    assert blocked.status_code == 403
    assert blocked.get_json()["error"] == "https_required"
    assert allowed.status_code == 200


def test_api_auth_when_configured_requires_runtime_secret_file(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.delenv("CPOS_API_BEARER_TOKEN_FILE", raising=False)

    blocked = client.get("/tasks")
    health = client.get("/health")

    assert blocked.status_code == 503
    assert blocked.get_json()["error"] == "api_token_not_configured"
    assert health.status_code == 200


def test_api_auth_when_configured_validates_bearer_token_file(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    token_file = tmp_path / "cpos_api_token"
    token_file.write_text("unit-test-token\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_FILE", str(token_file))

    missing = client.get("/tasks")
    wrong = client.get("/tasks", headers={"Authorization": "Bearer wrong"})
    allowed = client.get("/tasks", headers={"Authorization": "Bearer unit-test-token"})

    assert missing.status_code == 401
    assert missing.get_json()["error"] == "auth_required"
    assert wrong.status_code == 403
    assert wrong.get_json()["error"] == "auth_invalid"
    assert allowed.status_code == 200
    assert allowed.get_json()["ok"] is True


def test_api_auth_scopes_limit_task_routes(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    token_file = tmp_path / "cpos_api_token"
    scopes_file = tmp_path / "cpos_api_scopes"
    token_file.write_text("scoped-token\n", encoding="utf-8")
    scopes_file.write_text("read:tasks\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_SCOPES_FILE", str(scopes_file))
    headers = {"Authorization": "Bearer scoped-token"}

    allowed = client.get("/tasks", headers=headers)
    denied = client.post("/tasks/rollback-latest", json={"target": str(tmp_path / "app.py"), "confirm": True}, headers=headers)

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.get_json()["error"] == "scope_denied"
    assert denied.get_json()["required_scope"] == "write:rollback"


def test_api_auth_scopes_file_missing_fails_closed(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    token_file = tmp_path / "cpos_api_token"
    token_file.write_text("scoped-token\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_SCOPES_FILE", str(tmp_path / "missing_scopes"))

    blocked = client.get("/tasks", headers={"Authorization": "Bearer scoped-token"})

    assert blocked.status_code == 503
    assert blocked.get_json()["error"] == "api_scopes_not_configured"


def test_security_audit_records_auth_decisions_without_tokens(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    token_file = tmp_path / "cpos_api_token"
    scopes_file = tmp_path / "cpos_api_scopes"
    token_file.write_text("super-secret-value\n", encoding="utf-8")
    scopes_file.write_text("read:tasks\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_SCOPES_FILE", str(scopes_file))

    allowed = client.get("/tasks", headers={"Authorization": "Bearer super-secret-value", "X-Agent-Id": "AuditTester"})
    denied = client.get("/tasks", headers={"Authorization": "Bearer wrong", "X-Agent-Id": "AuditTester"})

    assert allowed.status_code == 200
    assert denied.status_code == 403
    raw = (tmp_path / "cpos" / "security_audit.jsonl").read_text(encoding="utf-8")
    assert "super-secret-value" not in raw
    assert "wrong" not in raw
    assert "AuditTester" in raw
    assert "allowed" in raw
    assert "auth_invalid" in raw
    assert "read:tasks" in raw


def test_security_audit_records_rollback_mutation(tmp_path, monkeypatch):
    test_agent = configure_task_test_agent(tmp_path)
    target = tmp_path / "workspace" / "app.py"
    target.parent.mkdir()
    target.write_text("old\n", encoding="utf-8")
    task_id = test_agent.task_tape.create_task(target=str(target), action="unit_test")
    checkpoint = test_agent.task_tape.create_checkpoint(task_id=task_id, target=str(target), content="old\n")
    target.write_text("new\n", encoding="utf-8")
    token_file = tmp_path / "cpos_api_token"
    scopes_file = tmp_path / "cpos_api_scopes"
    token_file.write_text("rollback-token\n", encoding="utf-8")
    scopes_file.write_text("write:rollback\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_SCOPES_FILE", str(scopes_file))

    response = client.post(
        "/tasks/rollback-latest",
        json={"target": str(target), "confirm": True},
        headers={"Authorization": "Bearer rollback-token", "X-Agent-Id": "RollbackBot"},
    )

    assert response.status_code == 200
    raw = (tmp_path / "cpos" / "security_audit.jsonl").read_text(encoding="utf-8")
    assert "rollback-token" not in raw
    assert "RollbackBot" in raw
    assert "rollback_applied" in raw
    assert checkpoint.checkpoint_id in raw
    assert str(target) in raw


def test_integrity_api_reports_hash_chained_ledgers(tmp_path, monkeypatch):
    test_agent = configure_task_test_agent(tmp_path)
    task_id = test_agent.task_tape.create_task(target="workspace/app.py", action="unit_test")
    test_agent.task_tape.create_checkpoint(task_id=task_id, target="workspace/app.py", content="old\n")
    test_agent.pointer_manager.create_pointer(context_type="spec", summary="spec", source="unit", location="docs/spec.md")
    token_file = tmp_path / "cpos_api_token"
    scopes_file = tmp_path / "cpos_api_scopes"
    token_file.write_text("integrity-token\n", encoding="utf-8")
    scopes_file.write_text("read:integrity\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_SCOPES_FILE", str(scopes_file))

    response = client.get("/integrity", headers={"Authorization": "Bearer integrity-token"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["ledgers"]["task_events"]["ok"] is True
    assert payload["ledgers"]["task_checkpoints"]["ok"] is True
    assert payload["ledgers"]["pointer_audit"]["ok"] is True
    assert payload["ledgers"]["security_audit"]["ok"] is True


def test_integrity_api_requires_integrity_scope(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    token_file = tmp_path / "cpos_api_token"
    scopes_file = tmp_path / "cpos_api_scopes"
    token_file.write_text("integrity-token\n", encoding="utf-8")
    scopes_file.write_text("read:tasks\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_SCOPES_FILE", str(scopes_file))

    response = client.get("/integrity", headers={"Authorization": "Bearer integrity-token"})

    assert response.status_code == 403
    assert response.get_json()["required_scope"] == "read:integrity"


def hmac_headers(method, path, query_string, body, secret, nonce="nonce-1", timestamp=None, agent_id="HMACTester", key_id=None):
    import hashlib
    import hmac as py_hmac
    import time as py_time

    timestamp = int(timestamp if timestamp is not None else py_time.time())
    body = body or b""
    message = "\n".join([
        method.upper(),
        path,
        query_string,
        hashlib.sha256(body).hexdigest(),
        str(timestamp),
        nonce,
    ])
    signature = py_hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {
        "X-CPOS-Timestamp": str(timestamp),
        "X-CPOS-Nonce": nonce,
        "X-CPOS-Signature": signature,
        "X-Agent-Id": agent_id,
    }
    if key_id is not None:
        headers["X-CPOS-Key-Id"] = key_id
    return headers


def test_hmac_auth_validates_signed_request_and_rejects_replay(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    secret_file = tmp_path / "cpos_hmac_secret"
    scopes_file = tmp_path / "cpos_api_scopes"
    secret_file.write_text("hmac-secret\n", encoding="utf-8")
    scopes_file.write_text("read:tasks\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_REQUIRE_HMAC_AUTH", "true")
    monkeypatch.setenv("CPOS_API_HMAC_SECRET_FILE", str(secret_file))
    monkeypatch.setenv("CPOS_API_SCOPES_FILE", str(scopes_file))

    headers = hmac_headers("GET", "/tasks", "", b"", "hmac-secret", nonce="valid-nonce")
    allowed = client.get("/tasks", headers=headers)
    replay = client.get("/tasks", headers=headers)

    assert allowed.status_code == 200
    assert replay.status_code == 409
    assert replay.get_json()["error"] == "hmac_nonce_replay"
    raw = (tmp_path / "cpos" / "security_audit.jsonl").read_text(encoding="utf-8")
    assert "hmac-secret" not in raw
    assert "hmac-sha256" in raw
    assert "hmac_nonce_replay" in raw


def test_hmac_auth_rejects_missing_secret_bad_signature_and_expired_timestamp(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_REQUIRE_HMAC_AUTH", "true")
    monkeypatch.delenv("CPOS_API_HMAC_SECRET_FILE", raising=False)

    missing_secret = client.get("/tasks")
    assert missing_secret.status_code == 503
    assert missing_secret.get_json()["error"] == "hmac_secret_not_configured"

    secret_file = tmp_path / "cpos_hmac_secret"
    secret_file.write_text("hmac-secret\n", encoding="utf-8")
    monkeypatch.setenv("CPOS_API_HMAC_SECRET_FILE", str(secret_file))
    bad = hmac_headers("GET", "/tasks", "", b"", "wrong-secret", nonce="bad-sig")
    bad_signature = client.get("/tasks", headers=bad)
    assert bad_signature.status_code == 403
    assert bad_signature.get_json()["error"] == "hmac_invalid"

    expired = hmac_headers("GET", "/tasks", "", b"", "hmac-secret", nonce="expired", timestamp=1)
    expired_response = client.get("/tasks", headers=expired)
    assert expired_response.status_code == 401
    assert expired_response.get_json()["error"] == "hmac_timestamp_expired"


def test_hmac_auth_enforces_scopes(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    secret_file = tmp_path / "cpos_hmac_secret"
    scopes_file = tmp_path / "cpos_api_scopes"
    secret_file.write_text("hmac-secret\n", encoding="utf-8")
    scopes_file.write_text("read:tasks\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_REQUIRE_HMAC_AUTH", "true")
    monkeypatch.setenv("CPOS_API_HMAC_SECRET_FILE", str(secret_file))
    monkeypatch.setenv("CPOS_API_SCOPES_FILE", str(scopes_file))

    headers = hmac_headers("GET", "/integrity", "", b"", "hmac-secret", nonce="integrity-denied")
    denied = client.get("/integrity", headers=headers)

    assert denied.status_code == 403
    assert denied.get_json()["error"] == "scope_denied"
    assert denied.get_json()["required_scope"] == "read:integrity"


def test_hmac_key_registry_allows_active_and_deprecated_keys(tmp_path, monkeypatch):
    import json
    configure_task_test_agent(tmp_path)
    active_secret = tmp_path / "active_secret"
    old_secret = tmp_path / "old_secret"
    registry = tmp_path / "hmac_keys.json"
    active_secret.write_text("active-secret\n", encoding="utf-8")
    old_secret.write_text("old-secret\n", encoding="utf-8")
    registry.write_text(
        json.dumps(
            {
                "keys": {
                    "2026-05-active": {"secret_file": str(active_secret), "status": "active", "scopes": ["read:tasks"]},
                    "2026-04-old": {"secret_file": str(old_secret), "status": "deprecated", "scopes": ["read:tasks"]},
                }
            }
        ),
        encoding="utf-8",
    )
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_REQUIRE_HMAC_AUTH", "true")
    monkeypatch.setenv("CPOS_API_HMAC_KEY_REGISTRY_FILE", str(registry))

    active = client.get("/tasks", headers=hmac_headers("GET", "/tasks", "", b"", "active-secret", nonce="active-key", key_id="2026-05-active"))
    deprecated = client.get("/tasks", headers=hmac_headers("GET", "/tasks", "", b"", "old-secret", nonce="old-key", key_id="2026-04-old"))

    assert active.status_code == 200
    assert deprecated.status_code == 200
    raw = (tmp_path / "cpos" / "security_audit.jsonl").read_text(encoding="utf-8")
    assert "active-secret" not in raw
    assert "old-secret" not in raw
    assert "2026-05-active" in raw
    assert "2026-04-old" in raw


def test_hmac_key_registry_rejects_missing_unknown_revoked_and_key_scope(tmp_path, monkeypatch):
    import json
    configure_task_test_agent(tmp_path)
    read_secret = tmp_path / "read_secret"
    revoked_secret = tmp_path / "revoked_secret"
    registry = tmp_path / "hmac_keys.json"
    read_secret.write_text("read-secret\n", encoding="utf-8")
    revoked_secret.write_text("revoked-secret\n", encoding="utf-8")
    registry.write_text(
        json.dumps(
            {
                "keys": {
                    "read-only": {"secret_file": str(read_secret), "status": "active", "scopes": ["read:tasks"]},
                    "revoked": {"secret_file": str(revoked_secret), "status": "revoked", "scopes": ["*"]},
                }
            }
        ),
        encoding="utf-8",
    )
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_REQUIRE_HMAC_AUTH", "true")
    monkeypatch.setenv("CPOS_API_HMAC_KEY_REGISTRY_FILE", str(registry))

    missing_key_id = client.get("/tasks", headers=hmac_headers("GET", "/tasks", "", b"", "read-secret", nonce="missing-key-id"))
    unknown = client.get("/tasks", headers=hmac_headers("GET", "/tasks", "", b"", "read-secret", nonce="unknown-key", key_id="unknown"))
    revoked = client.get("/tasks", headers=hmac_headers("GET", "/tasks", "", b"", "revoked-secret", nonce="revoked-key", key_id="revoked"))
    denied_scope = client.get("/integrity", headers=hmac_headers("GET", "/integrity", "", b"", "read-secret", nonce="key-scope-denied", key_id="read-only"))

    assert missing_key_id.status_code == 401
    assert missing_key_id.get_json()["error"] == "hmac_key_id_required"
    assert unknown.status_code == 403
    assert unknown.get_json()["error"] == "hmac_key_unknown"
    assert revoked.status_code == 403
    assert revoked.get_json()["error"] == "key_status_revoked"
    assert denied_scope.status_code == 403
    assert denied_scope.get_json()["error"] == "scope_denied"
    assert denied_scope.get_json()["required_scope"] == "read:integrity"


def test_hmac_key_registry_enforces_validity_window(tmp_path, monkeypatch):
    import json
    import time
    configure_task_test_agent(tmp_path)
    future_secret = tmp_path / "future_secret"
    expired_secret = tmp_path / "expired_secret"
    registry = tmp_path / "hmac_keys.json"
    future_secret.write_text("future-secret\n", encoding="utf-8")
    expired_secret.write_text("expired-secret\n", encoding="utf-8")
    now = int(time.time())
    registry.write_text(
        json.dumps(
            {
                "keys": {
                    "future": {"secret_file": str(future_secret), "status": "active", "scopes": ["read:tasks"], "not_before": now + 3600},
                    "expired": {"secret_file": str(expired_secret), "status": "active", "scopes": ["read:tasks"], "not_after": now - 3600},
                }
            }
        ),
        encoding="utf-8",
    )
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_REQUIRE_HMAC_AUTH", "true")
    monkeypatch.setenv("CPOS_API_HMAC_KEY_REGISTRY_FILE", str(registry))

    future = client.get("/tasks", headers=hmac_headers("GET", "/tasks", "", b"", "future-secret", nonce="future", key_id="future"))
    expired = client.get("/tasks", headers=hmac_headers("GET", "/tasks", "", b"", "expired-secret", nonce="expired-window", key_id="expired"))

    assert future.status_code == 403
    assert future.get_json()["error"] == "key_not_yet_valid"
    assert expired.status_code == 403
    assert expired.get_json()["error"] == "key_expired"


def test_ip_allowlist_blocks_untrusted_forwarded_ip(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_IP_ALLOWLIST", "203.0.113.0/24")
    monkeypatch.setenv("CPOS_TRUST_PROXY_HEADERS", "true")

    blocked = client.get("/tasks", headers={"X-Forwarded-For": "198.51.100.10"})
    allowed = client.get("/tasks", headers={"X-Forwarded-For": "203.0.113.9"})

    assert blocked.status_code == 403
    assert blocked.get_json()["error"] == "ip_denied"
    assert allowed.status_code == 200
    raw = (tmp_path / "cpos" / "security_audit.jsonl").read_text(encoding="utf-8")
    assert "ip_denied" in raw
    assert "198.51.100.10" in raw


def test_rate_limit_blocks_after_threshold_and_sets_headers(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    server.rate_limiter.clear()
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("CPOS_RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("CPOS_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("CPOS_TRUST_PROXY_HEADERS", "true")
    headers = {"X-Forwarded-For": "203.0.113.20"}

    first = client.get("/tasks", headers=headers)
    second = client.get("/tasks", headers=headers)
    limited = client.get("/tasks", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert limited.status_code == 429
    assert limited.get_json()["error"] == "rate_limited"
    assert limited.headers["Retry-After"]
    assert first.headers["X-RateLimit-Limit"] == "2"
    raw = (tmp_path / "cpos" / "security_audit.jsonl").read_text(encoding="utf-8")
    assert "rate_limited" in raw


def test_mutation_rate_limit_uses_stricter_bucket(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    server.rate_limiter.clear()
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("CPOS_RATE_LIMIT_REQUESTS", "100")
    monkeypatch.setenv("CPOS_MUTATION_RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("CPOS_TRUST_PROXY_HEADERS", "true")
    headers = {"X-Forwarded-For": "203.0.113.21"}

    first = client.post("/tasks/rollback-latest", json={"confirm": True}, headers=headers)
    limited = client.post("/tasks/rollback-latest", json={"confirm": True}, headers=headers)

    assert first.status_code == 400
    assert first.get_json()["error"] == "task_id_or_target_required"
    assert limited.status_code == 429
    assert limited.get_json()["error"] == "rate_limited"


def test_client_cert_fingerprint_required_and_allowed(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    fingerprints = tmp_path / "client_fingerprints.txt"
    good = "AA:BB:CC:DD"
    fingerprints.write_text(good + "\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_CLIENT_CERT", "true")
    monkeypatch.setenv("CPOS_CLIENT_CERT_FINGERPRINTS_FILE", str(fingerprints))

    missing = client.get("/tasks")
    denied = client.get("/tasks", headers={"X-SSL-Client-SHA256": "11:22:33:44"})
    allowed = client.get("/tasks", headers={"X-SSL-Client-SHA256": good})

    assert missing.status_code == 401
    assert missing.get_json()["error"] == "client_cert_required"
    assert denied.status_code == 403
    assert denied.get_json()["error"] == "client_cert_denied"
    assert allowed.status_code == 200
    raw = (tmp_path / "cpos" / "security_audit.jsonl").read_text(encoding="utf-8")
    assert "client_cert_required" in raw
    assert "client_cert_denied" in raw
    assert "client_cert_allowed" in raw
    assert "aabbccdd" in raw


def test_client_cert_missing_fingerprint_file_fails_closed(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_CLIENT_CERT", "true")
    monkeypatch.setenv("CPOS_CLIENT_CERT_FINGERPRINTS_FILE", str(tmp_path / "missing.txt"))

    response = client.get("/tasks")

    assert response.status_code == 503
    assert response.get_json()["error"] == "client_cert_fingerprints_not_configured"


def test_client_cert_audit_mode_logs_but_does_not_block(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    fingerprints = tmp_path / "client_fingerprints.txt"
    fingerprints.write_text("aabbccdd\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_CLIENT_CERT", "true")
    monkeypatch.setenv("CPOS_CLIENT_CERT_FINGERPRINTS_FILE", str(fingerprints))
    monkeypatch.setenv("CPOS_CLIENT_CERT_POLICY_MODE", "audit")

    response = client.get("/tasks", headers={"X-SSL-Client-SHA256": "11223344"})

    assert response.status_code == 200
    raw = (tmp_path / "cpos" / "security_audit.jsonl").read_text(encoding="utf-8")
    assert "client_cert_denied" in raw


def test_security_profile_endpoint_reports_effective_profile(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_SECURITY_PROFILE", "dev")
    monkeypatch.setenv("CPOS_SANDBOX_MODE", "strict")

    response = client.get("/security-profile")

    assert response.status_code == 200
    payload = response.get_json()["security_profile"]
    assert payload["profile"] == "dev"
    assert payload["values"]["CPOS_SANDBOX_MODE"] == "strict"


def test_security_profile_endpoint_includes_secret_inventory_summary(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    from cpos.secret_inventory import add_artifact
    inventory_path = tmp_path / "cpos" / "secret_inventory.jsonl"
    add_artifact(inventory_path, artifact_path="certs/key.pem", artifact_type="tls_private_key", vault_path="secret/cpos/tls", field="private_key")
    monkeypatch.setenv("CPOS_SECRET_INVENTORY_PATH", str(inventory_path))
    client = server.app.test_client()

    response = client.get("/security-profile")

    assert response.status_code == 200
    payload = response.get_json()["secret_inventory"]
    assert payload["count"] == 1
    assert payload["by_status"]["review"] == 1
    assert payload["records"][0]["artifact_path"] == "certs/key.pem"


def create_handoff_pointer_for_api(pointer_id="ptr://handoff/api"):
    return server.agent.pointer_manager.create_pointer(
        pointer_id=pointer_id,
        context_type="handoff_summary",
        summary="Imported CPOS handoff",
        source="handoff:AgentA",
        location="handoff://api",
        priority=0.55,
        trust_score=0.35,
        retrieval_rule="handoff_review_required",
        metadata={"bundle_sha256": "api", "counts": {"tasks": 1}, "signature": {"ok": True}},
    )


def test_handoff_inbox_api_lists_approves_and_rejects(tmp_path):
    configure_task_test_agent(tmp_path)
    pointer = create_handoff_pointer_for_api()
    client = server.app.test_client()

    listed = client.get('/handoff-inbox')
    assert listed.status_code == 200
    assert listed.get_json()['count'] == 1
    assert listed.get_json()['handoffs'][0]['review_status'] == 'pending'

    no_confirm = client.post(f'/handoff-inbox/{pointer.pointer_id}/approve', json={})
    assert no_confirm.status_code == 400
    assert no_confirm.get_json()['error'] == 'confirm_required'

    approved = client.post(f'/handoff-inbox/{pointer.pointer_id}/approve', json={'confirm': True, 'reason': 'ok'})
    assert approved.status_code == 200
    assert approved.get_json()['pointer']['retrieval_rule'] == 'handoff_approved'
    assert client.get('/handoff-inbox').get_json()['count'] == 0
    assert client.get('/handoff-inbox?status=approved').get_json()['count'] == 1

    rejected_pointer = create_handoff_pointer_for_api('ptr://handoff/api2')
    rejected = client.post(f'/handoff-inbox/{rejected_pointer.pointer_id}/reject', json={'reason': 'stale'})
    assert rejected.status_code == 200
    assert rejected.get_json()['pointer']['retrieval_rule'] == 'handoff_rejected'
    assert client.get('/handoff-inbox?status=rejected').get_json()['count'] == 1


def test_handoff_inbox_auth_scope(tmp_path, monkeypatch):
    configure_task_test_agent(tmp_path)
    create_handoff_pointer_for_api()
    token_file = tmp_path / 'token'
    scopes_file = tmp_path / 'scopes'
    token_file.write_text('review-token\n', encoding='utf-8')
    scopes_file.write_text('read:reviews\n', encoding='utf-8')
    monkeypatch.setenv('CPOS_REQUIRE_API_AUTH', 'true')
    monkeypatch.setenv('CPOS_API_BEARER_TOKEN_FILE', str(token_file))
    monkeypatch.setenv('CPOS_API_BEARER_TOKEN_SCOPES_FILE', str(scopes_file))
    client = server.app.test_client()
    headers = {'Authorization': 'Bearer review-token'}

    allowed = client.get('/handoff-inbox', headers=headers)
    denied = client.post('/handoff-inbox/ptr://handoff/api/approve', json={'confirm': True}, headers=headers)

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.get_json()['required_scope'] == 'write:reviews'


def test_handoff_promotion_api_requires_approved_and_promotes(tmp_path):
    configure_task_test_agent(tmp_path)
    pointer = create_handoff_pointer_for_api()
    client = server.app.test_client()

    not_approved = client.get(f'/handoff-inbox/{pointer.pointer_id}/promotion-plan')
    assert not_approved.status_code == 400
    assert not_approved.get_json()['error'] == 'handoff_not_approved'

    client.post(f'/handoff-inbox/{pointer.pointer_id}/approve', json={'confirm': True})
    plan = client.get(f'/handoff-inbox/{pointer.pointer_id}/promotion-plan')
    assert plan.status_code == 200
    assert plan.get_json()['plan']['source_pointer_id'] == pointer.pointer_id

    no_confirm = client.post(f'/handoff-inbox/{pointer.pointer_id}/promote', json={})
    assert no_confirm.status_code == 400
    assert no_confirm.get_json()['error'] == 'confirm_required'

    promoted = client.post(f'/handoff-inbox/{pointer.pointer_id}/promote', json={'confirm': True, 'reason': 'continue'})
    assert promoted.status_code == 200
    payload = promoted.get_json()
    assert payload['pointer']['context_type'] == 'handoff_promotion_plan'
    assert payload['pointer']['retrieval_rule'] == 'handoff_promotion_review_required'
    assert payload['pointer']['dependencies'] == [pointer.pointer_id]


def test_promotion_executor_api_creates_and_approves_review(tmp_path):
    configure_task_test_agent(tmp_path)
    handoff = create_handoff_pointer_for_api()
    client = server.app.test_client()
    client.post(f'/handoff-inbox/{handoff.pointer_id}/approve', json={'confirm': True})
    promoted = client.post(f'/handoff-inbox/{handoff.pointer_id}/promote', json={'confirm': True})
    promotion_id = promoted.get_json()['pointer']['pointer_id']

    no_confirm = client.post(f'/handoff-inbox/{promotion_id}/execute-plan', json={})
    assert no_confirm.status_code == 400
    assert no_confirm.get_json()['error'] == 'confirm_required'

    created = client.post(f'/handoff-inbox/{promotion_id}/execute-plan', json={'confirm': True, 'reason': 'resume'})
    assert created.status_code == 200
    task_id = created.get_json()['task_id']
    assert created.get_json()['review']['payload']['review_type'] == 'handoff_promotion_execution'

    # Fix review endpoint stays clean; handoff execution has its own queue.
    assert client.get('/tasks/reviews').get_json()['count'] == 0
    executions = client.get('/handoff-executions')
    assert executions.status_code == 200
    assert executions.get_json()['count'] == 1
    assert executions.get_json()['reviews'][0]['task_id'] == task_id

    approve_missing_confirm = client.post(f'/handoff-executions/{task_id}/approve', json={})
    assert approve_missing_confirm.status_code == 400
    approved = client.post(f'/handoff-executions/{task_id}/approve', json={'confirm': True})
    assert approved.status_code == 200
    assert approved.get_json()['status'] == 'approved'
    assert client.get('/handoff-executions').get_json()['count'] == 0


def test_resume_planner_api_creates_and_approves_resume_review(tmp_path):
    configure_task_test_agent(tmp_path)
    handoff = create_handoff_pointer_for_api()
    client = server.app.test_client()
    client.post(f'/handoff-inbox/{handoff.pointer_id}/approve', json={'confirm': True})
    promoted = client.post(f'/handoff-inbox/{handoff.pointer_id}/promote', json={'confirm': True})
    promotion_id = promoted.get_json()['pointer']['pointer_id']
    created = client.post(f'/handoff-inbox/{promotion_id}/execute-plan', json={'confirm': True})
    task_id = created.get_json()['task_id']
    client.post(f'/handoff-executions/{task_id}/approve', json={'confirm': True})

    plan = client.get(f'/handoff-executions/{task_id}/resume-plan')
    assert plan.status_code == 200
    assert plan.get_json()['proposal']['execute_automatically'] is False

    no_confirm = client.post(f'/handoff-executions/{task_id}/create-resume-review', json={})
    assert no_confirm.status_code == 400
    created_review = client.post(f'/handoff-executions/{task_id}/create-resume-review', json={'confirm': True})
    assert created_review.status_code == 200
    assert client.get('/resume-reviews').get_json()['count'] == 1
    approved = client.post(f'/resume-reviews/{task_id}/approve', json={'confirm': True, 'action_id': 'inspect_promotion_plan'})
    assert approved.status_code == 200
    assert approved.get_json()['approved_action_id'] == 'inspect_promotion_plan'


def test_handoff_graph_api_links_flow(tmp_path):
    configure_task_test_agent(tmp_path)
    handoff = create_handoff_pointer_for_api()
    client = server.app.test_client()
    client.post(f'/handoff-inbox/{handoff.pointer_id}/approve', json={'confirm': True})
    promoted = client.post(f'/handoff-inbox/{handoff.pointer_id}/promote', json={'confirm': True})
    promotion_id = promoted.get_json()['pointer']['pointer_id']
    execution = client.post(f'/handoff-inbox/{promotion_id}/execute-plan', json={'confirm': True})
    task_id = execution.get_json()['task_id']
    client.post(f'/handoff-executions/{task_id}/approve', json={'confirm': True})
    client.post(f'/handoff-executions/{task_id}/create-resume-review', json={'confirm': True})

    graph = client.get('/handoff-graph')
    assert graph.status_code == 200
    payload = graph.get_json()
    assert payload['counts']['handoffs'] == 1
    assert payload['counts']['promotions'] == 1
    assert payload['counts']['execution_reviews'] == 1
    assert payload['counts']['resume_reviews'] == 1
    assert payload['handoffs'][0]['pointer_id'] == handoff.pointer_id
    assert payload['execution_reviews'][0]['promotion_pointer_id'] == promotion_id
    assert payload['resume_reviews'][0]['task_id'] == task_id
