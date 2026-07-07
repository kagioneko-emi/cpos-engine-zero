from flask import Flask, request, jsonify
from engine_zero_agent import EngineZeroAgent
from ait_firewall.runtime import AITFirewallRuntime
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
target_dir = "/app/target_app" if os.path.exists("/app/target_app") else "/home/mayutama/target_app"
agent = EngineZeroAgent(target_dir)
firewall = AITFirewallRuntime()

# ThreadPoolExecutor to prevent Fork Bomb / resource exhaustion under load
executor = ThreadPoolExecutor(max_workers=2)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
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
