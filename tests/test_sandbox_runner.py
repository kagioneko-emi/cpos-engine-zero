import subprocess

from sandbox.runner import SandboxRunner


class FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_strict_mode_fails_closed_when_docker_unavailable(monkeypatch, tmp_path):
    runner = SandboxRunner("sandbox/Dockerfile.python", mode="strict")
    monkeypatch.setattr(runner, "docker_available", lambda: False)

    result = runner.run_command(str(tmp_path), "echo hello")

    assert result["exit_code"] == 125
    assert result["sandbox"]["backend"] == "none"
    assert result["sandbox"]["error"] == "docker_unavailable"
    assert result["sandbox"]["fallback_used"] is False


def test_permissive_mode_uses_local_fallback_with_metadata(monkeypatch, tmp_path):
    runner = SandboxRunner("sandbox/Dockerfile.python", mode="permissive")
    monkeypatch.setattr(runner, "docker_available", lambda: False)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeResult(returncode=0, stdout="ok\n"))

    result = runner.run_command(str(tmp_path), "echo ok")

    assert result["exit_code"] == 0
    assert result["stdout"] == "ok\n"
    assert result["sandbox"]["backend"] == "local"
    assert result["sandbox"]["fallback_used"] is True
    assert result["sandbox"]["reason"] == "docker_unavailable"


def test_docker_command_contains_hardening_flags(tmp_path):
    runner = SandboxRunner("sandbox/Dockerfile.python", mode="strict")

    cmd = runner.docker_command(str(tmp_path), "pytest")

    assert "--read-only" in cmd
    assert "--cap-drop" in cmd and "ALL" in cmd
    assert "--security-opt" in cmd and "no-new-privileges" in cmd
    assert "--network" in cmd and "none" in cmd
    assert "--pids-limit" in cmd
    assert any(item.startswith(f"{tmp_path}:/app:ro") for item in cmd)


def test_local_dev_mode_skips_docker(monkeypatch, tmp_path):
    runner = SandboxRunner("sandbox/Dockerfile.python", mode="local-dev")
    monkeypatch.setattr(runner, "docker_available", lambda: (_ for _ in ()).throw(AssertionError("docker should not be checked")))
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeResult(returncode=0, stdout="dev\n"))

    result = runner.run_command(str(tmp_path), "echo dev")

    assert result["sandbox"]["backend"] == "local"
    assert result["sandbox"]["mode"] == "local-dev"
    assert result["sandbox"]["reason"] == "explicit_local_dev"
