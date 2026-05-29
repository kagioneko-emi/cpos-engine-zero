import os
import shlex
import subprocess


class SandboxRunner:
    """Run verification commands in a hardened Docker sandbox.

    Modes:
    - strict: Docker required. No local fallback.
    - permissive: Docker preferred, local fallback allowed with metadata warning.
    - local-dev: Always run locally. Development only.
    """

    VALID_MODES = {"strict", "permissive", "local-dev"}

    def __init__(self, dockerfile_path, image_name="cpos-python-sandbox", mode=None):
        self.dockerfile_path = dockerfile_path
        self.image_name = image_name
        self.mode = self._resolve_mode(mode)

    def _resolve_mode(self, mode):
        value = (mode or os.environ.get("CPOS_SANDBOX_MODE", "strict")).lower()
        return value if value in self.VALID_MODES else "strict"

    def build_image(self):
        print(f"Building sandbox image: {self.image_name}...")
        cmd = ["docker", "build", "-t", self.image_name, "-f", self.dockerfile_path, os.path.dirname(self.dockerfile_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Build failed: {result.stderr}")
            return False
        return True

    def docker_available(self):
        try:
            subprocess.run(["docker", "info"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def docker_command(self, abs_target_dir, command):
        return [
            "docker", "run", "--rm",
            "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--network", "none",
            "--memory", os.environ.get("CPOS_SANDBOX_MEMORY", "256m"),
            "--cpus", os.environ.get("CPOS_SANDBOX_CPUS", "0.5"),
            "--pids-limit", os.environ.get("CPOS_SANDBOX_PIDS_LIMIT", "128"),
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
            "-v", f"{abs_target_dir}:/app:ro",
            "--workdir", "/app",
            self.image_name,
            "bash", "-lc", command,
        ]

    def run_command(self, target_dir, command):
        abs_target_dir = os.path.abspath(target_dir)
        print(f"Running command: {command}")
        mode = self._resolve_mode(self.mode)

        if mode == "local-dev":
            return self._run_local(abs_target_dir, command, mode=mode, reason="explicit_local_dev")

        if self.docker_available():
            print("Using hardened Docker sandbox...")
            result = subprocess.run(self.docker_command(abs_target_dir, command), capture_output=True, text=True)
            return self._payload(result, backend="docker", mode=mode, isolated=True)

        if mode == "strict":
            stderr = "Docker sandbox unavailable and CPOS_SANDBOX_MODE=strict forbids local fallback."
            print(f"[!] {stderr}")
            return {
                "stdout": "",
                "stderr": stderr,
                "exit_code": 125,
                "sandbox": {
                    "backend": "none",
                    "mode": mode,
                    "isolated": False,
                    "fallback_used": False,
                    "error": "docker_unavailable",
                },
            }

        return self._run_local(abs_target_dir, command, mode=mode, reason="docker_unavailable")

    def _run_local(self, abs_target_dir, command, *, mode, reason):
        print("Using local execution fallback (Caution: no isolation)...")
        result = subprocess.run(["bash", "-lc", f"cd {shlex.quote(abs_target_dir)} && {command}"], capture_output=True, text=True)
        return self._payload(result, backend="local", mode=mode, isolated=False, fallback_used=True, reason=reason)

    @staticmethod
    def _payload(result, *, backend, mode, isolated, fallback_used=False, reason=None):
        sandbox = {
            "backend": backend,
            "mode": mode,
            "isolated": isolated,
            "fallback_used": fallback_used,
        }
        if reason:
            sandbox["reason"] = reason
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "sandbox": sandbox,
        }


if __name__ == "__main__":
    runner = SandboxRunner("cpos_defensive_agent/sandbox/Dockerfile.python")
    # runner.build_image()
    # print(runner.run_command(".", "ls -l"))
