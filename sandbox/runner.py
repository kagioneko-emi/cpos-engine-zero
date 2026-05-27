import subprocess
import os

class SandboxRunner:
    def __init__(self, dockerfile_path, image_name="cpos-python-sandbox"):
        self.dockerfile_path = dockerfile_path
        self.image_name = image_name

    def build_image(self):
        print(f"Building sandbox image: {self.image_name}...")
        cmd = ["docker", "build", "-t", self.image_name, "-f", self.dockerfile_path, os.path.dirname(self.dockerfile_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Build failed: {result.stderr}")
            return False
        return True

    def run_command(self, target_dir, command):
        # target_dir should be absolute path
        abs_target_dir = os.path.abspath(target_dir)
        print(f"Running command: {command}")
        
        # Check if docker is available and daemon is running
        docker_available = False
        try:
            # check if docker command exists and can connect to daemon
            subprocess.run(["docker", "info"], capture_output=True, check=True)
            docker_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[!] Docker not available or daemon not running. Falling back to local execution.")

        if docker_available:
            print("Using Docker sandbox...")
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{abs_target_dir}:/app:ro", # Read-only mount for safety
                "--network", "none",              # No network
                "--memory", "256m",               # Memory limit
                "--cpus", "0.5",                  # CPU limit
                self.image_name,
                "bash", "-c", command
            ]
            result = subprocess.run(docker_cmd, capture_output=True, text=True)
        else:
            print("Using local execution fallback (Caution: no isolation)...")
            # Local execution fallback
            # We use bash -c to be consistent with docker's bash -c
            result = subprocess.run(["bash", "-c", f"cd {abs_target_dir} && {command}"], capture_output=True, text=True)
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }

if __name__ == "__main__":
    runner = SandboxRunner("cpos_defensive_agent/sandbox/Dockerfile.python")
    # runner.build_image()
    # print(runner.run_command(".", "ls -l"))
