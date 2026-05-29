import json

from cpos.rate_limit import FileBackedRateLimiter
from agents.main_agent import MainAgent
from cpos.pointer_os import PointerManager
from cpos.task_tape import TaskTapeStore
import server


def test_file_backed_rate_limiter_persists_between_instances(tmp_path):
    store = tmp_path / "rate_limit.json"
    one = FileBackedRateLimiter(store)
    two = FileBackedRateLimiter(store)

    allowed1 = one.allow("client:default", limit=2, window_seconds=60, now=1000)
    allowed2 = two.allow("client:default", limit=2, window_seconds=60, now=1001)
    blocked = one.allow("client:default", limit=2, window_seconds=60, now=1002)

    assert allowed1[0] is True
    assert allowed2[0] is True
    assert blocked[0] is False
    assert blocked[1] == 0
    raw = json.loads(store.read_text(encoding="utf-8"))
    assert "client:default" in raw["buckets"]


def test_file_backed_rate_limiter_prunes_after_window(tmp_path):
    store = tmp_path / "rate_limit.json"
    limiter = FileBackedRateLimiter(store)

    assert limiter.allow("client:default", limit=1, window_seconds=10, now=100)[0] is True
    assert limiter.allow("client:default", limit=1, window_seconds=10, now=105)[0] is False
    assert limiter.allow("client:default", limit=1, window_seconds=10, now=111)[0] is True


def configure_agent(tmp_path):
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


def test_server_file_rate_limit_backend_blocks_and_writes_store(tmp_path, monkeypatch):
    configure_agent(tmp_path)
    store = tmp_path / "cpos" / "rate_limit_state.json"
    server._file_rate_limiters.clear()
    monkeypatch.setenv("CPOS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("CPOS_RATE_LIMIT_BACKEND", "file")
    monkeypatch.setenv("CPOS_RATE_LIMIT_STORE_PATH", str(store))
    monkeypatch.setenv("CPOS_RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("CPOS_RATE_LIMIT_WINDOW_SECONDS", "60")
    client = server.app.test_client()

    allowed = client.get("/tasks")
    limited = client.get("/tasks")

    assert allowed.status_code == 200
    assert limited.status_code == 429
    assert limited.get_json()["error"] == "rate_limited"
    assert store.exists()
    assert json.loads(store.read_text(encoding="utf-8"))["buckets"]


def test_security_profile_reports_rate_limit_backend(tmp_path, monkeypatch):
    configure_agent(tmp_path)
    store = tmp_path / "cpos" / "rate_limit_state.json"
    monkeypatch.setenv("CPOS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("CPOS_RATE_LIMIT_BACKEND", "file")
    monkeypatch.setenv("CPOS_RATE_LIMIT_STORE_PATH", str(store))

    res = server.app.test_client().get("/security-profile")

    assert res.status_code == 200
    payload = res.get_json()
    assert payload["rate_limit"]["enabled"] is True
    assert payload["rate_limit"]["backend"] == "file"
    assert payload["rate_limit"]["file_store_path"] == str(store)


def test_redis_rate_limit_backend_requires_vault_rendered_url_file(tmp_path, monkeypatch):
    configure_agent(tmp_path)
    server._redis_rate_limiters.clear()
    monkeypatch.setenv("CPOS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("CPOS_RATE_LIMIT_BACKEND", "redis")
    monkeypatch.delenv("CPOS_RATE_LIMIT_REDIS_URL_FILE", raising=False)

    res = server.app.test_client().get("/tasks")

    assert res.status_code == 503
    assert res.get_json()["error"] == "rate_limit_redis_url_not_configured"
