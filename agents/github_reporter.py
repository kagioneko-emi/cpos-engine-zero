import requests
import os
import logging

logger = logging.getLogger(__name__)

class GitHubReporter:
    """Handles communication back to GitHub (comments, status)."""
    def __init__(self, token=None):
        self.token = token or self._load_token_from_vault()
        self.base_url = "https://api.github.com"

    def _load_token_from_vault(self):
        # In this environment, we'd use 'vault kv get' or an env var
        # For the demo, we check CPOS_GITHUB_TOKEN
        return os.environ.get('CPOS_GITHUB_TOKEN')

    def post_comment(self, repo_full_name, issue_number, body):
        if not self.token:
            logger.warning("[!] GitHub Token not configured. Skipping comment.")
            return False
        
        url = f"{self.base_url}/repos/{repo_full_name}/issues/{issue_number}/comments"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        try:
            res = requests.post(url, json={"body": body}, headers=headers)
            res.raise_for_status()
            logger.info(f"[+] Posted comment to {repo_full_name}#{issue_number}")
            return True
        except Exception as e:
            logger.error(f"[!] Failed to post GitHub comment: {e}")
            return False

    def notify_analysis_started(self, repo, issue_num, target_file):
        msg = f"🛡️ **CPOS Engine-Zero Analysis Started**\n\nTarget: `{target_file}`\nI am currently analyzing the codebase and verifying potential fixes in a secure sandbox."
        return self.post_comment(repo, issue_num, msg)

    def notify_fix_proposed(self, repo, issue_num, task_id, dashboard_url):
        msg = f"✅ **Fix Proposed & Verified**\n\nThe autonomous cycle has generated a verified fix for this issue.\n\n- **Task ID**: `{task_id}`\n- **Review Required**: Please approve the fix via the [Command Center Dashboard]({dashboard_url})."
        return self.post_comment(repo, issue_num, msg)
