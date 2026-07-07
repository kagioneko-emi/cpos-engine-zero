import os
import json
import subprocess
import threading
import re
import shutil
import uuid
import logging
import sys

# Configure module-level logger compatible with stdout parsing
logger = logging.getLogger("EngineZeroAgent")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class EngineZeroAgent:
    def __init__(self, target_dir):
        self.target_dir = os.path.abspath(target_dir)

    def print_banner(self, run_id):
        banner = f"""\033[36m
  /\\_/\\   🛡️  ENGINE-ZERO: SECURE DEVOPS RUNTIME
 ( o.o )  -------------------------------------
  > ^ <   [🔒 RUN_ID: {run_id}]
 /     \\  [🔒 STATUS: ONLINE]
( |   | ) [🔒 FIREWALL: ACTIVE (AIT V12)]
(__d_b__) -------------------------------------\033[0m"""
        logger.info(banner)

    def run_devops_cycle(self, instruction):
        # 0. Create an isolated temporary workspace for parallel execution (No locks needed!)
        run_id = str(uuid.uuid4())[:8]
        temp_workspace = f"{self.target_dir}_tmp_{run_id}"
        
        self.print_banner(run_id)
        logger.info(f"--- [Engine-Zero] [Run: {run_id}] Received Instruction: {instruction} ---")
        
        calc_path = os.path.join(temp_workspace, "src/calc.py")
        test_path = os.path.join(temp_workspace, "tests/test_calc.py")
        
        try:
            logger.info(f"[*] Creating isolated workspace: {temp_workspace}")
            shutil.copytree(self.target_dir, temp_workspace)
            
            # 1. Research (Load Context from temp workspace)
            logger.info(f"[{run_id}] [1/4] Researching context...")
            if not os.path.exists(calc_path):
                logger.error(f"[{run_id}] [!] Error: calc.py not found at {calc_path}")
                return
            if not os.path.exists(test_path):
                logger.error(f"[{run_id}] [!] Error: test_calc.py not found at {test_path}")
                return

            with open(calc_path, 'r', encoding='utf-8') as f:
                calc_code = f.read()
            with open(test_path, 'r', encoding='utf-8') as f:
                test_code = f.read()
            
            # 3. Execution (Speculative Edit in temp workspace)
            logger.info(f"[{run_id}] [2/4] Applying speculative fix...")
            new_code = self.apply_fix(calc_code, instruction)
            
            if new_code == calc_code:
                logger.info(f"[{run_id}] [3/4] No changes applied (Instruction ignored). Skipping validation.")
                logger.info(f"[{run_id}] [4/4] Cycle Complete: Deployment Skipped (Safe).")
                return
                
            # Write speculative fix to temp workspace
            with open(calc_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            
            # 3.5 Malware Signature Scan (New Portable Security Layer)
            is_malicious, malware_type = self.detect_malware(new_code)
            if is_malicious:
                logger.error(f"[{run_id}] [!] MALWARE/BACKDOOR DETECTED: Code contains '{malware_type}'. Discarding change immediately (Safe Rollback).")
                return
            
            # 4. Validation (Test inside temp workspace)
            logger.info(f"[{run_id}] [3/4] Validating changes via Test Suite...")
            success = self.run_tests(temp_workspace, run_id)
            
            if success:
                logger.info(f"[{run_id}] [4/4] Validation Succeeded. Deploying fix to production app...")
                # Atomic Deploy: Write the verified code back to the production target_app
                prod_calc_path = os.path.join(self.target_dir, "src/calc.py")
                os.makedirs(os.path.dirname(prod_calc_path), exist_ok=True)
                with open(prod_calc_path, 'w', encoding='utf-8') as f:
                    f.write(new_code)
                logger.info(f"[{run_id}] [4/4] Cycle Complete: Deployment Ready.")
            else:
                logger.info(f"[{run_id}] [4/4] Cycle Failed: Discarding changes (Safe Rollback).")
                
        except OSError as e:
            logger.error(f"[{run_id}] [!] OS/Filesystem error during DevOps cycle: {e}")
        except Exception as e:
            logger.error(f"[{run_id}] [!] Unhandled exception during DevOps cycle: {e}")
        finally:
            # 5. Cleanup temp workspace
            logger.info(f"[*] Cleaning up isolated workspace: {temp_workspace}")
            if os.path.exists(temp_workspace):
                try:
                    def remove_readonly(func, path, excinfo):
                        try:
                            os.chmod(path, 0o777)
                            func(path)
                        except Exception:
                            pass
                    shutil.rmtree(temp_workspace, onerror=remove_readonly)
                except OSError as e:
                    logger.error(f"[!] OS Error during workspace cleanup of {temp_workspace}: {e}")

    def detect_malware(self, code):
        # Static signatures for backdoors, obfuscated shells, and exfiltration attempts
        signatures = {
            r"\b(eval|exec)\b\s*\(": "Dynamic Code Execution (eval/exec backdoor)",
            r"__import__\s*\(\s*['\"]os['\"]\s*\)\s*\.system": "Obfuscated OS shell execution",
            r"\bos\.system\b": "Direct OS shell execution",
            r"\bsubprocess\.(Popen|call|run)\b": "Process spawning",
            r"\bbase64\.b64decode\b": "Obfuscated Base64 payload decoding",
            r"\bzlib\.decompress\b": "Obfuscated compressed payload execution",
            r"\bsocket\.socket\b": "Low-level socket socket connection",
            r"urllib\.request\.urlopen": "Outbound network request",
            r"\bgetattr\b\s*\(\s*os\b": "Dynamic OS attribute access (obfuscated shell bypass)",
            r"\b(importlib|sys\.modules)\b": "Dynamic module loading (import bypass)",
            r"\b(compile|globals|locals)\b\s*\(": "Dynamic code compilation & context manipulation"
        }
        for pattern, desc in signatures.items():
            if re.search(pattern, code):
                return True, desc
        return False, ""

    def apply_fix(self, code, instruction):
        # Split by [AIT] header prefix to isolate segments and prevent cross-boundary greedy regex matches
        segments = instruction.split("[AIT]")
        user_instructions = []
        
        for seg in segments:
            if not seg.strip():
                continue
            # Only process high-trust USER instructions
            if "SRC:USER" in seg:
                match = re.search(r"\[DATA\]\n(.*?)\n\[/DATA\]", seg, re.DOTALL)
                if match:
                    user_instructions.append(match.group(1))
                else:
                    # If it's a plain instruction without [DATA] wrappers, take content below headers
                    lines = seg.strip().split("\n")
                    if len(lines) > 1:
                        user_instructions.append("\n".join(lines[1:]))
                        
        if user_instructions:
            instruction_to_check = "\n".join(user_instructions)
        else:
            # Fallback if no structured AIT tags are present
            instruction_to_check = instruction

        # Use word boundary regex to prevent false positives (e.g., matching 'information' or 'infinite')
        if re.search(r"\b(inf|infinity)\b", instruction_to_check, re.IGNORECASE):
            if "if b == 0:" in code:
                logger.info("[*] Fix already applied. Skipping duplicate rewrite.")
                return code
            return code.replace(
                "return a / b",
                "if b == 0:\n        print('Logging: Division by zero')\n        return float('inf')\n    return a / b"
            )
        return code

    def run_tests(self, workspace_path, run_id):
        # Update test to match new requirement in temp workspace
        test_path = os.path.join(workspace_path, "tests/test_calc.py")
        try:
            with open(test_path, 'r', encoding='utf-8') as f:
                test_content = f.read()
            
            new_test = test_content.replace(
                "with pytest.raises(ZeroDivisionError):\n        divide(10, 0)",
                "assert divide(10, 0) == float('inf')"
            )
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(new_test)
        except OSError as e:
            logger.error(f"[!] OS Error while preparing test file in workspace: {e}")
            return False
        
        # Docker Sandbox Execution with Unique Container Name for strict isolation
        container_name = f"engine-zero-sandbox-{run_id}"
        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--network", "none",            # Disable all network access (prevents reverse shells & credential leaks)
            "--cap-drop", "ALL",            # Drop all kernel privileges (mitigates host escape exploits)
            "--memory", "512m",             # Limit memory (prevents memory exhaustion DoS)
            "--cpus", "0.5",                # Limit CPU (prevents CPU exhaustion DoS)
            "--pids-limit", "50",           # Limit process creation (prevents thread/fork-bomb attacks)
            "-v", f"{os.path.abspath(workspace_path)}:/app/target_app:ro",
            "engine-zero-sandbox:latest",
            "bash", "-c", "cd /app/target_app && PYTHONPATH=. pytest -s tests/test_calc.py"
        ]
        
        logger.info(f"[*] [Docker Sandbox: {container_name}] Running pytest inside container...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.stdout:
                logger.info(result.stdout.strip())
            if result.stderr:
                logger.warning(f"Stderr: {result.stderr.strip()}")
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.error(f"[!] Docker Sandbox TIMEOUT (30s). Force killing container: {container_name}")
            try:
                subprocess.run(["docker", "kill", container_name], capture_output=True)
            except Exception as kill_err:
                logger.error(f"[!] Failed to kill container {container_name}: {kill_err}")
            return False
        except FileNotFoundError:
            logger.warning("[!] Docker executable not found. Falling back to local process execution with timeout limit (30s)...")
            try:
                # Fallback: Run pytest locally in the isolated workspace path with timeout
                local_cmd = ["bash", "-c", f"cd {workspace_path} && PYTHONPATH=. pytest -s tests/test_calc.py"]
                result = subprocess.run(local_cmd, capture_output=True, text=True, timeout=30)
                if result.stdout:
                    logger.info(result.stdout.strip())
                if result.stderr:
                    logger.warning(f"Stderr: {result.stderr.strip()}")
                return result.returncode == 0
            except subprocess.TimeoutExpired:
                logger.error(f"[!] Local Execution TIMEOUT (30s) for workspace: {workspace_path}")
                return False
            except Exception as local_err:
                logger.error(f"[!] Local Execution failed: {local_err}")
                return False
        except Exception as e:
            logger.error(f"[!] Unexpected error during sandbox test execution: {e}")
            return False

if __name__ == "__main__":
    agent = EngineZeroAgent("/home/mayutama/target_app")
    agent.run_devops_cycle("Feature Request: Handle division by zero by returning float('inf') and log the event.")
