from urllib.parse import quote

from agents.main_agent import MainAgent
from cpos.pointer_os import PointerManager
import server


def configure_test_agent(tmp_path):
    test_agent = MainAgent()
    test_agent.project_root = str(tmp_path)
    test_agent.audit_log_path = str(tmp_path / "cpos" / "audit_log.jsonl")
    test_agent.pointers_path = str(tmp_path / "cpos" / "pointers.jsonl")
    test_agent.pointer_manager = PointerManager(test_agent.pointers_path, test_agent.audit_log_path)
    server.agent = test_agent
    return test_agent


def encode_pointer(pointer_id):
    return quote(pointer_id, safe="")


def test_pointer_api_list_retrieve_and_invalidate(tmp_path):
    test_agent = configure_test_agent(tmp_path)
    source = tmp_path / "app.py"
    source.write_text("VALUE = 42\n", encoding="utf-8")
    pointer = test_agent.pointer_manager.create_pointer(
        context_type="code",
        summary="important app source",
        source="unit_test",
        location=str(source),
        priority=0.8,
        trust_score=0.9,
    )

    client = server.app.test_client()

    listed = client.get("/pointers?query=important")
    assert listed.status_code == 200
    listed_payload = listed.get_json()
    assert listed_payload["ok"] is True
    assert listed_payload["count"] == 1
    assert listed_payload["pointers"][0]["pointer_id"] == pointer.pointer_id

    retrieved = client.get(f"/pointers/{encode_pointer(pointer.pointer_id)}?purpose=unit_test")
    assert retrieved.status_code == 200
    retrieved_payload = retrieved.get_json()
    assert retrieved_payload["ok"] is True
    assert retrieved_payload["context"] == "VALUE = 42\n"
    assert retrieved_payload["snippet"] == "VALUE = 42\n"
    assert retrieved_payload["reconstruction"]["mode"] == "full_file"
    assert retrieved_payload["pointer"]["access_count"] == 1

    invalidated = client.post(
        f"/pointers/{encode_pointer(pointer.pointer_id)}/invalidate",
        json={"reason": "outdated"},
    )
    assert invalidated.status_code == 200
    assert invalidated.get_json()["pointer"]["status"] == "invalidated"

    denied = client.get(f"/pointers/{encode_pointer(pointer.pointer_id)}")
    assert denied.status_code == 404
    assert denied.get_json()["error"] == "not_found_or_denied"


def test_pointer_api_blocks_restricted_by_default_and_allows_opt_in(tmp_path):
    test_agent = configure_test_agent(tmp_path)
    pointer = test_agent.pointer_manager.create_pointer(
        context_type="private_credentials",
        summary="credential reference",
        source="vault",
        location="secret/discord",
        trust_score=1.0,
        sensitivity_level="restricted",
    )

    client = server.app.test_client()

    listed = client.get("/pointers")
    assert listed.status_code == 200
    assert listed.get_json()["count"] == 0

    blocked = client.get(f"/pointers/{encode_pointer(pointer.pointer_id)}?include_restricted=true")
    assert blocked.status_code == 404

    allowed = client.get(
        f"/pointers/{encode_pointer(pointer.pointer_id)}?include_restricted=true&allowed_context_type=private_credentials"
    )
    assert allowed.status_code == 404
    # Even explicit sensitivity opt-in does not bypass blocked_context_types.
    assert allowed.get_json()["error"] == "not_found_or_denied"


def test_pointer_api_invalid_invalidate_request(tmp_path):
    configure_test_agent(tmp_path)
    client = server.app.test_client()

    missing_reason = client.post("/pointers/ptr%3A%2F%2Fmissing/invalidate", json={})
    assert missing_reason.status_code == 400
    assert missing_reason.get_json()["error"] == "reason_required"

    bad_reason = client.post(
        "/pointers/ptr%3A%2F%2Fmissing/invalidate",
        json={"reason": "not_a_reason"},
    )
    assert bad_reason.status_code == 400
    assert "invalid invalidation reason" in bad_reason.get_json()["error"]


def test_pointer_api_trust_update_and_exchange(tmp_path):
    test_agent = configure_test_agent(tmp_path)
    pointer = test_agent.pointer_manager.create_pointer(
        context_type="finding",
        summary="unsafe eval finding",
        source="unit_test",
        location="workspace/app.py:1",
        priority=0.9,
        trust_score=0.7,
    )
    client = server.app.test_client()

    trusted = client.post(
        f"/pointers/{encode_pointer(pointer.pointer_id)}/trust-update",
        json={"score": 0.95, "reason": "user_confirmed"},
    )
    assert trusted.status_code == 200
    trusted_payload = trusted.get_json()
    assert trusted_payload["ok"] is True
    assert trusted_payload["pointer"]["trust_score"] == 0.95
    assert trusted_payload["pointer"]["metadata"]["trust_history"][-1]["reason"] == "user_confirmed"

    exchanged = client.post(
        f"/pointers/{encode_pointer(pointer.pointer_id)}/exchange",
        json={
            "from_agent": "CodingAgent",
            "to_agent": "AuditAgent",
            "purpose": "audit_required",
            "access_level": "internal",
        },
    )
    assert exchanged.status_code == 200
    exchanged_payload = exchanged.get_json()
    assert exchanged_payload["ok"] is True
    assert exchanged_payload["exchange"]["pointer"] == pointer.pointer_id
    assert exchanged_payload["exchange"]["to_agent"] == "AuditAgent"

    audit_events = [line for line in open(test_agent.audit_log_path, encoding="utf-8").read().splitlines()]
    assert any("trust_score_updated" in line for line in audit_events)
    assert any("pointer_exchanged" in line for line in audit_events)


def test_pointer_api_trust_update_validation(tmp_path):
    configure_test_agent(tmp_path)
    client = server.app.test_client()
    pointer_id = encode_pointer("ptr://missing")

    missing_score = client.post(f"/pointers/{pointer_id}/trust-update", json={"reason": "manual"})
    assert missing_score.status_code == 400
    assert missing_score.get_json()["error"] == "score_required"

    invalid_score = client.post(f"/pointers/{pointer_id}/trust-update", json={"score": "bad", "reason": "manual"})
    assert invalid_score.status_code == 400
    assert invalid_score.get_json()["error"] == "invalid_score"

    not_found = client.post(f"/pointers/{pointer_id}/trust-update", json={"score": 0.5, "reason": "manual"})
    assert not_found.status_code == 404
    assert not_found.get_json()["error"] == "not_found"


def test_pointer_api_exchange_validation(tmp_path):
    configure_test_agent(tmp_path)
    client = server.app.test_client()
    pointer_id = encode_pointer("ptr://missing")

    missing_fields = client.post(f"/pointers/{pointer_id}/exchange", json={"from_agent": "CodingAgent"})
    assert missing_fields.status_code == 400
    assert missing_fields.get_json()["error"] == "missing_required_fields"
    assert missing_fields.get_json()["missing"] == ["to_agent", "purpose"]

    not_found = client.post(
        f"/pointers/{pointer_id}/exchange",
        json={"from_agent": "CodingAgent", "to_agent": "AuditAgent", "purpose": "audit_required"},
    )
    assert not_found.status_code == 404
    assert not_found.get_json()["error"] == "not_found"


def test_api_auth_scopes_limit_pointer_routes(tmp_path, monkeypatch):
    configure_test_agent(tmp_path)
    token_file = tmp_path / "cpos_api_token"
    scopes_file = tmp_path / "cpos_api_scopes"
    token_file.write_text("pointer-token\n", encoding="utf-8")
    scopes_file.write_text("read:pointers\n", encoding="utf-8")
    client = server.app.test_client()
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("CPOS_API_BEARER_TOKEN_SCOPES_FILE", str(scopes_file))
    headers = {"Authorization": "Bearer pointer-token"}

    allowed = client.get("/pointers", headers=headers)
    denied = client.post("/pointers/ptr%3A%2F%2Fmissing/invalidate", json={"reason": "outdated"}, headers=headers)

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.get_json()["error"] == "scope_denied"
    assert denied.get_json()["required_scope"] == "write:pointers"
