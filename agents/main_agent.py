import os
import json
import datetime
import subprocess
from agents.subagent_python import PythonSubagent
from agents.fixer_agent import FixerAgent
from agents.architect_gemini import GeminiArchitect
from sandbox.runner import SandboxRunner
from cpos.pointer_os import ContextPointer, PointerManager, stable_token, utc_now
from cpos.task_tape import TaskTapeStore

class MainAgent:
    def __init__(self):
        # Determine project root based on this file's location
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.audit_log_path = os.path.join(self.project_root, "cpos/audit_log.jsonl")
        self.pointers_path = os.path.join(self.project_root, "cpos/pointers.jsonl")
        self.pointer_manager = PointerManager(self.pointers_path, self.audit_log_path)
        self.task_tape_path = os.path.join(self.project_root, "tapes/task_runs.jsonl")
        self.task_checkpoint_path = os.path.join(self.project_root, "tapes/task_checkpoints.jsonl")
        self.task_tape = TaskTapeStore(self.task_tape_path, self.task_checkpoint_path)
        self.sandbox = SandboxRunner(os.path.join(self.project_root, "sandbox/Dockerfile.python"))
        self.fixer = FixerAgent(os.path.join(self.project_root, "memory/python/fix_patterns.yaml"))
        self.architect = GeminiArchitect()
        self.require_fix_approval = os.environ.get("CPOS_REQUIRE_FIX_APPROVAL", "true").lower() not in {"0", "false", "no"}

    def log_audit(self, entry):
        entry["timestamp"] = datetime.datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
        with open(self.audit_log_path, 'a') as f:
            f.write(json.dumps(entry) + "\n")

    def update_pointer(self, target_file, findings):
        """Persist static-analysis findings as CPOS Context Pointers.

        The pointer file used to contain only {file, line, rule_id}.  New entries
        follow the Context Pointer OS schema so downstream agents can retrieve,
        govern, invalidate, and exchange references without loading full context.
        """
        abs_target = os.path.abspath(target_file)
        pointers = []
        for finding in findings:
            rule_id = finding.get("rule_id", "unknown")
            line = finding.get("line", 0)
            severity = finding.get("severity", "medium")
            priority = self._severity_priority(severity)
            pointer_id = f"ptr://finding/python/{stable_token(rule_id)}/{stable_token(abs_target)}:{line}"
            pointers.append(ContextPointer(
                pointer_id=pointer_id,
                context_type="finding",
                summary=f"{finding.get('title', rule_id)} in {os.path.basename(abs_target)}:{line}",
                source="python_subagent",
                location=f"{abs_target}:{line}",
                priority=priority,
                trust_score=0.82,
                sensitivity_level="internal",
                retrieval_rule="line_context",
                created_at=utc_now(),
                status="active",
                metadata={
                    "file": abs_target,
                    "line": line,
                    "rule_id": rule_id,
                    "title": finding.get("title"),
                    "severity": severity,
                    "content": finding.get("content"),
                    "fix": finding.get("fix"),
                },
            ))

        self.pointer_manager.replace_for_location(abs_target, pointers)

    @staticmethod
    def _severity_priority(severity):
        return {
            "critical": 1.0,
            "high": 0.9,
            "medium": 0.7,
            "low": 0.4,
        }.get(str(severity).lower(), 0.5)

    def apply_autonomous_fix(self, target_file, content, findings, sandbox_output, require_review=None):
        print(f"[*] CPOS Architect initiating autonomous fix for {target_file}...")
        task_id = self.task_tape.create_task(
            target=target_file,
            action="autonomous_fix",
            payload={"finding_count": len(findings)},
        )
        checkpoint = self.task_tape.create_checkpoint(task_id=task_id, target=target_file, content=content)

        # We take the highest severity finding first, or we could pass all
        primary_finding = sorted(findings, key=lambda x: (x['severity'] == 'high', x['severity'] == 'medium'), reverse=True)[0]
        self.task_tape.append_event(
            task_id=task_id,
            event="fix_requested",
            target=target_file,
            checkpoint_id=checkpoint.checkpoint_id,
            status="running",
            payload={"primary_rule_id": primary_finding.get("rule_id"), "primary_severity": primary_finding.get("severity")},
        )

        fixed_code = self.architect.propose_fix(target_file, content, primary_finding, sandbox_output)

        if fixed_code:
            review_required = self.require_fix_approval if require_review is None else require_review
            if review_required:
                self.task_tape.append_event(
                    task_id=task_id,
                    event="review_required",
                    target=target_file,
                    checkpoint_id=checkpoint.checkpoint_id,
                    status="pending_review",
                    payload={
                        "proposed_code": fixed_code,
                        "proposed_size": len(fixed_code),
                        "primary_rule_id": primary_finding.get("rule_id"),
                        "primary_severity": primary_finding.get("severity"),
                    },
                )
                print("[!] Fix generated but not written. Review approval required.")
                return {
                    "exit_code": 2,
                    "stdout": "Review required before writing fix.",
                    "task_id": task_id,
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "status": "pending_review",
                    "review_required": True,
                }
            return self._write_and_verify_fix(task_id, target_file, fixed_code, checkpoint.checkpoint_id)

        failure = {"exit_code": 1, "stdout": "Gemini failed to generate a fix.", "task_id": task_id, "checkpoint_id": checkpoint.checkpoint_id}
        self.task_tape.append_event(
            task_id=task_id,
            event="fix_failed",
            target=target_file,
            checkpoint_id=checkpoint.checkpoint_id,
            status="failed",
            payload={"reason": "architect_returned_empty"},
        )
        return failure


    def pending_fix_reviews(self):
        reviews = []
        for review in self.task_tape.pending_reviews():
            safe_review = dict(review)
            payload = dict(safe_review.get("payload", {}))
            if payload.get("review_type") not in {None, "fix"}:
                continue
            payload.pop("proposed_code", None)
            safe_review["payload"] = payload
            reviews.append(safe_review)
        return reviews

    def approve_pending_fix(self, task_id, confirm=False):
        if confirm is not True:
            return {"ok": False, "error": "confirm_required", "task_id": task_id}
        review = self.task_tape.latest_pending_review(task_id)
        if review is None:
            return {"ok": False, "error": "pending_review_not_found", "task_id": task_id}
        proposed_code = review.payload.get("proposed_code")
        if not proposed_code:
            return {"ok": False, "error": "proposed_code_missing", "task_id": task_id}
        self.task_tape.append_event(
            task_id=task_id,
            event="review_approved",
            target=review.target,
            checkpoint_id=review.checkpoint_id,
            status="approved",
            payload={"approved_by": "api_or_internal", "proposed_size": len(proposed_code)},
        )
        verification = self._write_and_verify_fix(task_id, review.target, proposed_code, review.checkpoint_id)
        return {"ok": verification.get("exit_code") == 0, "verification": verification}

    def reject_pending_fix(self, task_id, reason="manual_reject"):
        review = self.task_tape.latest_pending_review(task_id)
        if review is None:
            return {"ok": False, "error": "pending_review_not_found", "task_id": task_id}
        self.task_tape.append_event(
            task_id=task_id,
            event="review_rejected",
            target=review.target,
            checkpoint_id=review.checkpoint_id,
            status="rejected",
            payload={"reason": reason},
        )
        return {"ok": True, "task_id": task_id, "status": "rejected"}

    def _write_and_verify_fix(self, task_id, target_file, fixed_code, checkpoint_id):
        with open(target_file, 'w') as f:
            f.write(fixed_code)
        self.task_tape.append_event(
            task_id=task_id,
            event="fix_written",
            target=target_file,
            checkpoint_id=checkpoint_id,
            status="written",
            payload={"fixed_size": len(fixed_code)},
        )
        print("[+] Fix applied. Re-verifying in sandbox...")

        workspace_dir = os.path.dirname(target_file)
        filename = os.path.basename(target_file)
        verification = self.sandbox.run_command(workspace_dir, f"ruff check --no-cache {filename}")
        self.task_tape.append_event(
            task_id=task_id,
            event="verification_completed",
            target=target_file,
            checkpoint_id=checkpoint_id,
            status="success" if verification.get("exit_code") == 0 else "failed",
            payload={"exit_code": verification.get("exit_code"), "stdout": verification.get("stdout"), "stderr": verification.get("stderr")},
        )
        verification["task_id"] = task_id
        verification["checkpoint_id"] = checkpoint_id
        return verification

    def git_deliver(self, target_file, branch_name, commit_message):
        print(f"[*] CPOS Deliver: Pushing changes to branch {branch_name}...")
        workspace_dir = os.path.dirname(os.path.abspath(target_file))
        
        # Get auth from environment
        user = os.environ.get("GITHUB_USER", "kagioneko")
        repo_owner = "kagioneko-emi" # The actual owner of the repository
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPO", "cpos-engine-zero")
        
        if not token:
            print("[!] GITHUB_TOKEN not found. Skipping push.")
            return "Error: No token"

        # Construct authenticated URL pointing to the correct repository owner
        remote_url = f"https://{user}:{token}@github.com/{repo_owner}/{repo}.git"
        
        # Git commands sequence - Add user/email and handle branch properly
        commands = [
            "git init", # Ensure it's a git repo just in case
            "git config --global user.email 'engine-zero@example.com'",
            "git config --global user.name 'Engine-Zero Agent'",
            f"git remote set-url origin {remote_url} || git remote add origin {remote_url}",
            f"git checkout -b {branch_name} || git checkout {branch_name}",
            f"git add {os.path.basename(target_file)}",
            f"git commit -m \"{commit_message}\"",
            f"git push -u origin {branch_name}"
        ]

        
        results = []
        for cmd in commands:
            # We don't want to print the token in logs, so be careful
            safe_cmd = cmd.replace(token, "****") if token else cmd
            print(f"Executing: {safe_cmd}")
            # Ensure we capture both stdout and stderr together for proper logging
            res = subprocess.run(["bash", "-c", f"cd {workspace_dir} && {cmd}"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output = res.stdout.strip()
            safe_output = output.replace(token, "****") if token else output
            if safe_output:
                print(f"Output: {safe_output}")
            results.append(safe_output)
            
            if res.returncode != 0 and "git commit" not in cmd: # Ignore empty commits
                print(f"[!] Command failed with exit code {res.returncode}")
            
        print("[+] Delivery commands executed.")
        return "\n".join(results)

    def run_tdd_creation(self, target_file, spec_title, spec_body):
        print(f"[*] CPOS Architect: Starting Autonomous TDD Cycle for {target_file}...")
        
        # ... (previous logic for TDD)
        module_name = os.path.basename(target_file).replace(".py", "")
        test_file = os.path.join(os.path.dirname(target_file), f"test_{module_name}.py")
        print(f"[1/3] Generating Test Suite: {test_file}")
        test_code = self.architect.create_test_from_spec(spec_title, spec_body, module_name)
        if not test_code: return {"exit_code": 1, "stdout": "Failed to generate tests"}
        
        with open(test_file, 'w') as f: f.write(test_code)

        print(f"[2/3] Generating Initial Implementation: {target_file}")
        impl_code = self.architect.create_from_spec(spec_title, spec_body)
        if not impl_code: return {"exit_code": 1, "stdout": "Failed to generate implementation"}
        
        with open(target_file, 'w') as f: f.write(impl_code)

        print("[3/3] Starting Verification Loop...")
        workspace_dir = os.path.dirname(os.path.abspath(target_file))
        success = False
        for attempt in range(1, 4):
            print(f"--- Attempt {attempt} ---")
            test_result = self.sandbox.run_command(workspace_dir, f"pytest {os.path.basename(test_file)}")
            
            if test_result["exit_code"] == 0:
                print("✨ TDD Cycle Success: All tests passed!")
                success = True
                break
            
            print(f"❌ Tests failed. Feedback loop initiating...")
            impl_code = self.architect.propose_fix_from_test(target_file, impl_code, test_code, test_result["stdout"])
            if impl_code:
                with open(target_file, 'w') as f: f.write(impl_code)
            else:
                break
        
        if success:
            branch = f"auto-create-{module_name}-{datetime.datetime.now().strftime('%m%d%H%M')}"
            self.git_deliver(target_file, branch, f"feat: autonomous creation of {module_name} based on spec")
            self.log_audit({"target": target_file, "type": "tdd_creation", "status": "success", "branch": branch})
            return {"exit_code": 0, "stdout": f"Created and pushed to {branch}"}
            
        return {"exit_code": 1, "stdout": "TDD Cycle failed"}

    def run_analysis(self, target_file, auto_fix=False):
        abs_target_file = os.path.abspath(target_file)
        print(f"Starting analysis for: {abs_target_file}")
        
        if not abs_target_file.endswith(".py"):
            print("Unsupported file type.")
            return

        with open(abs_target_file, 'r') as f:
            original_content = f.read()

        subagent = PythonSubagent(
            os.path.join(self.project_root, "tapes/python/base.tape"),
            os.path.join(self.project_root, "memory/python/mistakes.jsonl")
        )
        subagent.load_tape()
        subagent.load_mistakes()

        findings = subagent.analyze_file(abs_target_file)
        
        # Update CPOS Pointers
        self.update_pointer(abs_target_file, findings)

        # Sandbox check
        workspace_dir = os.path.dirname(abs_target_file)
        filename = os.path.basename(abs_target_file)
        sandbox_result = self.sandbox.run_command(workspace_dir, f"ruff check --no-cache {filename}")
        
        if auto_fix and findings:
            sandbox_output = sandbox_result.get("stdout", "")
            verification_result = self.apply_autonomous_fix(abs_target_file, original_content, findings, sandbox_output)
            
            if verification_result["exit_code"] == 0:
                 self.update_pointer(abs_target_file, [])
                 print("✨ All issues resolved and verified autonomously!")
                 sandbox_result = verification_result
            else:
                 print(f"❌ Autonomous fix failed verification: {verification_result.get('stdout')}")

        report = {
            "target": abs_target_file,
            "rule_findings": findings,
            "sandbox_lint": sandbox_result
        }
        self.log_audit(report)
        
        print(f"Analysis complete. Found {len(findings)} issues.")
        for f in findings:
            print(f"[{f['severity']}] Line {f['line']}: {f['title']}")
        
        return report

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="File to analyze")
    parser.add_argument("--fix", action="store_true", help="Apply learned fixes automatically")
    args = parser.parse_args()

    agent = MainAgent()
    agent.run_analysis(args.file, auto_fix=args.fix)
