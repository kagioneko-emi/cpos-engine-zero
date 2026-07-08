from flask import Flask, request, jsonify
from engine_zero_agent import EngineZeroAgent
from ait_firewall.runtime import AITFirewallRuntime
import hmac
import hashlib
import os
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

# Configure module-level logger compatible with stdout parsing
logger = logging.getLogger("EngineZeroServer")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("ENGINE_ZERO_MAX_BODY_BYTES", "1048576"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
target_dir = "/app/target_app" if os.path.exists("/app/target_app") else os.path.join(BASE_DIR, "target_app")
agent = EngineZeroAgent(target_dir)
firewall = AITFirewallRuntime()

# ThreadPoolExecutor to prevent Fork Bomb / resource exhaustion under load
executor = ThreadPoolExecutor(max_workers=2)

def verify_github_signature(raw_body: bytes) -> bool:
    """Verify GitHub's X-Hub-Signature-256 when a webhook secret is configured.

    Set GITHUB_WEBHOOK_SECRET from Vault/secret manager at runtime. If the secret
    is unset, the server remains usable for local hackathon demos but logs that it
    is running in reduced-authentication mode.
    """
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    require_signature = os.environ.get("ENGINE_ZERO_REQUIRE_SIGNATURE") == "1"
    if not secret:
        if require_signature:
            logger.error("[!] ENGINE_ZERO_REQUIRE_SIGNATURE=1 but GITHUB_WEBHOOK_SECRET is not set; rejecting webhook.")
            return False
        logger.warning("[!] GITHUB_WEBHOOK_SECRET is not set; accepting webhook in demo mode.")
        return True

    header = request.headers.get("X-Hub-Signature-256", "")
    if not header.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, header)

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "CPOS Engine-Zero",
        "status": "online",
        "mode": "zero-trust-devops-runtime",
        "endpoints": ["/health", "/webhook"],
        "cloud_run_note": "Docker sandbox validation is fail-closed unless explicitly configured for reduced-isolation demos.",
    }), 200

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    raw_body = request.get_data(cache=True)
    if not verify_github_signature(raw_body):
        logger.warning("[!] Webhook rejected: invalid or missing GitHub signature.")
        return jsonify({"status": "error", "message": "Invalid webhook signature"}), 401

    try:
        data = request.get_json(silent=True)
    except Exception as e:
        logger.error(f"[!] Webhook error: Failed to parse request JSON: {e}")
        return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

    if not data:
        return jsonify({"status": "error", "message": "No JSON payload provided"}), 400
    
    # Check if it's a GitHub Issue event
    if 'issue' in data and data.get('action') == 'opened':
        issue_data = data.get('issue', {})
        issue_title = issue_data.get('title')
        issue_body = issue_data.get('body', '')
        
        if not issue_title:
            return jsonify({"status": "error", "message": "Issue title is missing"}), 400
            
        logger.info(f"[*] Webhook Received (Async Task Submitted): {issue_title}")

        try:
            # --- AIT Firewall Protection Layer ---
            # Treat Title as USER instruction, Body as untrusted WEB data
            protected_title = firewall.process_input(issue_title, "USER")
            protected_body = firewall.process_input(issue_body, "WEB")
            
            instruction = f"{protected_title}\n\n{protected_body}"
            # -------------------------------------
            
            # Trigger the autonomous cycle via thread pool executor
            executor.submit(agent.run_devops_cycle, instruction)
            
            return jsonify({"status": "cycle_initiated_async", "issue": issue_title}), 202
        except Exception as e:
            logger.error(f"[!] Error processing task through firewall: {e}")
            return jsonify({"status": "error", "message": "Error processing instruction safety layer"}), 500
    
    return jsonify({"status": "ignored"}), 200

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
