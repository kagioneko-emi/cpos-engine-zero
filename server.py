from flask import Flask, request, jsonify, g
import os
import sys
import threading
import traceback
import logging
import subprocess
import hmac
import hashlib
import time

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Ensure current directory is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.main_agent import MainAgent
from cpos.pointer_os import RetrievalPolicy
from cpos.security_audit import SecurityAuditLog
from cpos.hash_chain import verify_hash_chain
from cpos.nonce_store import NonceStore
from cpos.key_registry import HMACKeyRegistry

app = Flask(__name__)
# Initialize MainAgent (it will handle its own sub-agents and sandbox)
agent = MainAgent()


def https_required():
    if os.environ.get('CPOS_ENFORCE_HTTPS', 'false').lower() not in {'1', 'true', 'yes'}:
        return False
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    return not (request.is_secure or forwarded_proto == 'https')


def api_auth_enabled():
    return os.environ.get('CPOS_REQUIRE_API_AUTH', 'false').lower() in {'1', 'true', 'yes'}


def hmac_auth_enabled():
    return os.environ.get('CPOS_REQUIRE_HMAC_AUTH', 'false').lower() in {'1', 'true', 'yes'}


def load_api_bearer_token():
    """Load API bearer token from a runtime secret file only.

    Do not hardcode tokens in code, .env, crontab, or docs. In production,
    populate this file from Vault or a secret volume with restricted permissions.
    """
    token_file = os.environ.get('CPOS_API_BEARER_TOKEN_FILE')
    if not token_file:
        return None
    try:
        with open(token_file, encoding='utf-8') as fh:
            token = fh.read().strip()
    except OSError:
        return None
    return token or None


def load_api_hmac_secret():
    """Load HMAC shared secret from a runtime secret file only."""
    secret_file = os.environ.get('CPOS_API_HMAC_SECRET_FILE')
    if not secret_file:
        return None
    try:
        with open(secret_file, encoding='utf-8') as fh:
            secret = fh.read().strip()
    except OSError:
        return None
    return secret or None


def hmac_key_registry_path():
    return os.environ.get('CPOS_API_HMAC_KEY_REGISTRY_FILE')


def load_hmac_key_record(key_id):
    registry_path = hmac_key_registry_path()
    if not registry_path:
        return None
    return HMACKeyRegistry(registry_path).get(key_id)


def load_api_scopes():
    """Load authorization scopes from a non-logged runtime secret/config file.

    The file may contain comma-separated scopes or one scope per line. If absent,
    authenticated tokens keep legacy full access. Set the file in production to
    narrow privileges by route.
    """
    scopes_file = os.environ.get('CPOS_API_SCOPES_FILE') or os.environ.get('CPOS_API_BEARER_TOKEN_SCOPES_FILE')
    if not scopes_file:
        return {'*'}
    try:
        raw = open(scopes_file, encoding='utf-8').read()
    except OSError:
        return set()
    scopes = set()
    for chunk in raw.replace('\n', ',').split(','):
        scope = chunk.strip()
        if scope:
            scopes.add(scope)
    return scopes


def security_audit_path():
    configured = os.environ.get('CPOS_SECURITY_AUDIT_PATH')
    if configured:
        return configured
    root = getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'cpos', 'security_audit.jsonl')


def security_audit_log():
    return SecurityAuditLog(security_audit_path())


def request_actor():
    return request.headers.get('X-Agent-Id', 'HTTPClient')


def audit_security_event(event, decision, status_code=None, required_scope=None, metadata=None):
    # Never record Authorization headers, bearer tokens, secrets, or request bodies.
    security_audit_log().append(
        event=event,
        actor=request_actor(),
        method=request.method,
        path=request.path,
        decision=decision,
        status_code=status_code,
        required_scope=required_scope,
        metadata=metadata or {},
    )



def nonce_store_path():
    configured = os.environ.get('CPOS_API_NONCE_STORE_PATH')
    if configured:
        return configured
    root = getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'cpos', 'nonce_seen.jsonl')


def hmac_timestamp_window_seconds():
    try:
        return int(os.environ.get('CPOS_HMAC_TIMESTAMP_WINDOW_SECONDS', '300'))
    except ValueError:
        return 300


def hmac_message(timestamp, nonce, body_bytes):
    body_sha256 = hashlib.sha256(body_bytes).hexdigest()
    return "\n".join([
        request.method.upper(),
        request.path,
        request.query_string.decode('utf-8'),
        body_sha256,
        str(timestamp),
        nonce,
    ])


def validate_scopes(required_scope):
    scopes = load_api_scopes()
    if not scopes:
        audit_security_event('auth_decision', 'api_scopes_not_configured', 503, required_scope)
        return None, (jsonify({'ok': False, 'error': 'api_scopes_not_configured'}), 503)
    if not scope_allowed(scopes, required_scope):
        audit_security_event('auth_decision', 'scope_denied', 403, required_scope)
        return None, (jsonify({'ok': False, 'error': 'scope_denied', 'required_scope': required_scope}), 403)
    return scopes, None


def validate_hmac_auth_header(required_scope):
    key_id = request.headers.get('X-CPOS-Key-Id', '')
    key_record = None
    registry_path = hmac_key_registry_path()
    if registry_path:
        if not key_id:
            audit_security_event('auth_decision', 'hmac_key_id_required', 401, required_scope)
            return jsonify({'ok': False, 'error': 'hmac_key_id_required'}), 401
        key_record = load_hmac_key_record(key_id)
        if key_record is None:
            audit_security_event('auth_decision', 'hmac_key_unknown', 403, required_scope, {'key_id': key_id})
            return jsonify({'ok': False, 'error': 'hmac_key_unknown'}), 403
        usable, unusable_reason = key_record.is_usable()
        if not usable:
            audit_security_event('auth_decision', unusable_reason, 403, required_scope, {'key_id': key_id})
            return jsonify({'ok': False, 'error': unusable_reason}), 403
        secret = key_record.load_secret()
    else:
        secret = load_api_hmac_secret()

    if not secret:
        audit_security_event('auth_decision', 'hmac_secret_not_configured', 503, required_scope, {'key_id': key_id} if key_id else {})
        return jsonify({'ok': False, 'error': 'hmac_secret_not_configured'}), 503

    timestamp_raw = request.headers.get('X-CPOS-Timestamp', '')
    nonce = request.headers.get('X-CPOS-Nonce', '')
    signature = request.headers.get('X-CPOS-Signature', '')
    if not timestamp_raw or not nonce or not signature:
        audit_security_event('auth_decision', 'hmac_required', 401, required_scope)
        return jsonify({'ok': False, 'error': 'hmac_required'}), 401
    try:
        timestamp = int(timestamp_raw)
    except ValueError:
        audit_security_event('auth_decision', 'hmac_bad_timestamp', 401, required_scope)
        return jsonify({'ok': False, 'error': 'hmac_bad_timestamp'}), 401

    now = int(time.time())
    window = hmac_timestamp_window_seconds()
    if abs(now - timestamp) > window:
        audit_security_event('auth_decision', 'hmac_timestamp_expired', 401, required_scope)
        return jsonify({'ok': False, 'error': 'hmac_timestamp_expired'}), 401
    store = NonceStore(nonce_store_path())
    if store.seen(nonce, now=now, ttl_seconds=window):
        audit_security_event('auth_decision', 'hmac_nonce_replay', 409, required_scope)
        return jsonify({'ok': False, 'error': 'hmac_nonce_replay'}), 409

    body = request.get_data(cache=True) or b''
    expected = hmac.new(secret.encode('utf-8'), hmac_message(timestamp, nonce, body).encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        audit_security_event('auth_decision', 'hmac_invalid', 403, required_scope)
        return jsonify({'ok': False, 'error': 'hmac_invalid'}), 403

    if key_record is not None:
        scopes = key_record.scopes
        if not scope_allowed(scopes, required_scope):
            audit_security_event('auth_decision', 'scope_denied', 403, required_scope, {'key_id': key_id})
            return jsonify({'ok': False, 'error': 'scope_denied', 'required_scope': required_scope}), 403
    else:
        scopes, error_response = validate_scopes(required_scope)
        if error_response is not None:
            return error_response
    store.remember(nonce, timestamp=timestamp)
    g.api_auth = {
        'agent_id': request_actor(),
        'required_scope': required_scope,
        'scopes': sorted(scopes),
        'auth_type': 'hmac-sha256',
        'key_id': key_id or None,
    }
    metadata = {'auth_type': 'hmac-sha256'}
    if key_id:
        metadata['key_id'] = key_id
        if key_record is not None:
            metadata['key_status'] = key_record.status
    audit_security_event('auth_decision', 'allowed', 200, required_scope, metadata)
    return None

def request_needs_api_auth():
    if not api_auth_enabled():
        return False
    # Health stays unauthenticated for load balancers / Cloud Run probes.
    if request.path == '/health':
        return False
    return request.path.startswith(('/pointers', '/tasks', '/webhook', '/integrity'))


def required_scope_for_request():
    if request.path.startswith('/integrity'):
        return 'read:integrity'
    if request.path == '/webhook':
        return 'webhook:github'
    if request.path.startswith('/pointers'):
        return 'read:pointers' if request.method == 'GET' else 'write:pointers'
    if request.path.startswith('/tasks'):
        if request.method == 'GET':
            return 'read:reviews' if request.path == '/tasks/reviews' else 'read:tasks'
        if request.path == '/tasks/rollback-latest':
            return 'write:rollback'
        if request.path.endswith('/approve-fix') or request.path.endswith('/reject-fix'):
            return 'write:reviews'
        return 'write:tasks'
    return None


def scope_allowed(scopes, required):
    if required is None:
        return True
    family = required.split(':', 1)[0]
    return '*' in scopes or required in scopes or f'{family}:*' in scopes


def validate_api_auth_header():
    required_scope = required_scope_for_request()
    if hmac_auth_enabled():
        return validate_hmac_auth_header(required_scope)

    expected = load_api_bearer_token()
    if not expected:
        audit_security_event('auth_decision', 'api_token_not_configured', 503, required_scope)
        return jsonify({'ok': False, 'error': 'api_token_not_configured'}), 503
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer '):
        audit_security_event('auth_decision', 'auth_required', 401, required_scope)
        return jsonify({'ok': False, 'error': 'auth_required'}), 401
    provided = header.removeprefix('Bearer ').strip()
    if not hmac.compare_digest(provided, expected):
        audit_security_event('auth_decision', 'auth_invalid', 403, required_scope)
        return jsonify({'ok': False, 'error': 'auth_invalid'}), 403

    scopes, error_response = validate_scopes(required_scope)
    if error_response is not None:
        return error_response

    g.api_auth = {
        'agent_id': request_actor(),
        'required_scope': required_scope,
        'scopes': sorted(scopes),
        'auth_type': 'bearer',
    }
    audit_security_event('auth_decision', 'allowed', 200, required_scope, {'auth_type': 'bearer'})
    return None


@app.before_request
def enforce_https_when_configured():
    if https_required():
        return jsonify({'ok': False, 'error': 'https_required'}), 403


@app.before_request
def enforce_api_auth_when_configured():
    if request_needs_api_auth():
        return validate_api_auth_header()


def run_tdd_thread(target_file, spec_title, issue_body):
    try:
        logger.info(f"[*] Starting background TDD creation for {target_file}...")
        agent.run_tdd_creation(target_file, spec_title, issue_body)
        logger.info(f"[+] Background TDD creation completed for {target_file}.")
    except Exception as e:
        logger.error(f"[!] Background TDD creation failed: {e}")
        logger.error(traceback.format_exc())

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON data received"}), 400

    # Handle GitHub Issue Event
    if data.get('action') == 'opened' and 'issue' in data:
        issue_title = data['issue']['title']
        issue_body = data['issue'].get('body', '')
        
        # Branch logic: Create vs Fix
        if "[CREATE]" in issue_title.upper():
            # Example title: "[CREATE] workspace/new_tool.py: Data processing utility"
            try:
                parts = issue_title.split(":", 1)
                target_file = parts[0].replace("[CREATE]", "").strip()
                spec_title = parts[1].strip() if len(parts) > 1 else "New Module"
                
                logger.info(f"[*] Autonomous Creation Triggered: {target_file}")
                thread = threading.Thread(target=run_tdd_thread, args=(target_file, spec_title, issue_body))
                thread.start()
                
                return jsonify({"status": "accepted", "mode": "creation", "target": target_file}), 202
            except Exception as e:
                logger.error(f"Error parsing issue title: {e}")
                return jsonify({"status": "error", "message": str(e)}), 400
        else:
            target_file = "workspace/test_app.py" # Default for demo
            logger.info(f"[*] Autonomous Fix Cycle Triggered: {issue_title}")
            thread = threading.Thread(target=run_autonomous_cycle, args=(target_file,))
            thread.start()
            
            return jsonify({"status": "accepted", "mode": "fix", "issue": issue_title}), 202

    return jsonify({"status": "ignored", "message": "Event type not supported"}), 200

def run_autonomous_cycle(target_file):
    try:
        logger.info(f"[*] Starting background analysis for {target_file}...")
        agent.run_analysis(target_file, auto_fix=True)
        logger.info(f"[+] Background cycle completed for {target_file}.")
    except Exception as e:
        logger.error(f"[!] Background cycle failed: {e}")
        logger.error(traceback.format_exc())


def pointer_policy_from_request():
    include_restricted = request.args.get('include_restricted', '').lower() in {'1', 'true', 'yes'}
    levels = ['public', 'internal', 'private', 'restricted'] if include_restricted else ['public', 'internal']
    minimum_trust_score = float(request.args.get('minimum_trust_score', 0.0))
    return RetrievalPolicy(
        allowed_context_types=request.args.getlist('allowed_context_type'),
        minimum_trust_score=minimum_trust_score,
        allowed_sensitivity_levels=levels,
    )


@app.route('/pointers', methods=['GET'])
def list_pointers():
    limit_arg = request.args.get('limit')
    try:
        limit = int(limit_arg) if limit_arg else None
        policy = pointer_policy_from_request()
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

    pointers = agent.pointer_manager.search(
        context_type=request.args.get('context_type'),
        query=request.args.get('query'),
        policy=policy,
        limit=limit,
    )
    return jsonify({
        'ok': True,
        'count': len(pointers),
        'pointers': [pointer.to_dict() for pointer in pointers],
    }), 200


@app.route('/pointers/<path:pointer_id>', methods=['GET'])
def retrieve_pointer(pointer_id):
    try:
        policy = pointer_policy_from_request()
    except ValueError as e:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': str(e)}), 400

    result = agent.pointer_manager.retrieve_context(
        pointer_id,
        agent_id=request.args.get('agent_id', 'FlaskAPI'),
        purpose=request.args.get('purpose', 'http_retrieval'),
        policy=policy,
    )
    if result is None:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'not_found_or_denied'}), 404
    return jsonify({'ok': True, **result}), 200


@app.route('/pointers/<path:pointer_id>/invalidate', methods=['POST'])
def invalidate_pointer(pointer_id):
    data = request.get_json(silent=True) or {}
    reason = data.get('reason')
    if not reason:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'reason_required'}), 400
    try:
        pointer = agent.pointer_manager.invalidate_pointer(
            pointer_id,
            reason=reason,
            replacement_pointer=data.get('replacement_pointer'),
        )
    except ValueError as e:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': str(e)}), 400
    if pointer is None:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'not_found'}), 404
    audit_security_event('security_mutation', 'pointer_invalidated', 200, required_scope_for_request(), {'pointer_id': pointer_id, 'reason': reason})
    return jsonify({'ok': True, 'pointer': pointer.to_dict()}), 200


@app.route('/pointers/<path:pointer_id>/trust-update', methods=['POST'])
def update_pointer_trust(pointer_id):
    data = request.get_json(silent=True) or {}
    if 'score' not in data:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'score_required'}), 400
    reason = data.get('reason')
    if not reason:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'reason_required'}), 400
    try:
        score = float(data.get('score'))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'invalid_score'}), 400

    pointer = agent.pointer_manager.update_trust_score(pointer_id, score, reason=reason)
    if pointer is None:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'not_found'}), 404
    audit_security_event('security_mutation', 'pointer_trust_updated', 200, required_scope_for_request(), {'pointer_id': pointer_id, 'score': score, 'reason': reason})
    return jsonify({'ok': True, 'pointer': pointer.to_dict()}), 200


@app.route('/pointers/<path:pointer_id>/exchange', methods=['POST'])
def exchange_pointer(pointer_id):
    data = request.get_json(silent=True) or {}
    missing = [field for field in ['from_agent', 'to_agent', 'purpose'] if not data.get(field)]
    if missing:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'missing_required_fields', 'missing': missing}), 400
    if not any(pointer.pointer_id == pointer_id for pointer in agent.pointer_manager.load()):
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'not_found'}), 404

    event = agent.pointer_manager.exchange_pointer(
        from_agent=data['from_agent'],
        to_agent=data['to_agent'],
        pointer_id=pointer_id,
        purpose=data['purpose'],
        access_level=data.get('access_level', 'internal'),
    )
    audit_security_event('security_mutation', 'pointer_exchanged', 200, required_scope_for_request(), {'pointer_id': pointer_id, 'from_agent': data['from_agent'], 'to_agent': data['to_agent'], 'purpose': data['purpose']})
    return jsonify({'ok': True, 'exchange': event}), 200


@app.route('/tasks', methods=['GET'])
def task_summary():
    return jsonify({'ok': True, 'summary': agent.task_tape.summary()}), 200


@app.route('/tasks/events', methods=['GET'])
def task_events():
    rows = [event.to_dict() for event in agent.task_tape.events()]
    task_id = request.args.get('task_id')
    target = request.args.get('target')
    if task_id:
        rows = [row for row in rows if row.get('task_id') == task_id]
    if target:
        rows = [row for row in rows if row.get('target') == target]
    return jsonify({'ok': True, 'count': len(rows), 'events': rows}), 200


@app.route('/tasks/checkpoints', methods=['GET'])
def task_checkpoints():
    rows = [checkpoint.to_dict() for checkpoint in agent.task_tape.checkpoints()]
    task_id = request.args.get('task_id')
    target = request.args.get('target')
    if task_id:
        rows = [row for row in rows if row.get('task_id') == task_id]
    if target:
        rows = [row for row in rows if row.get('target') == target]
    sanitized = []
    for row in rows:
        item = dict(row)
        item['content_size'] = len(item.get('content', ''))
        item.pop('content', None)
        sanitized.append(item)
    return jsonify({'ok': True, 'count': len(sanitized), 'checkpoints': sanitized}), 200


@app.route('/tasks/rollback-latest', methods=['POST'])
def task_rollback_latest():
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is not True:
        return jsonify({'ok': False, 'error': 'confirm_required'}), 400
    task_id = data.get('task_id')
    target = data.get('target')
    if not task_id and not target:
        return jsonify({'ok': False, 'error': 'task_id_or_target_required'}), 400
    result = agent.task_tape.rollback_latest(target=target, task_id=task_id)
    if not result.get('ok'):
        return jsonify(result), 404
    checkpoint = dict(result['checkpoint'])
    checkpoint['content_size'] = len(checkpoint.get('content', ''))
    checkpoint.pop('content', None)
    audit_security_event('security_mutation', 'rollback_applied', 200, required_scope_for_request(), {'task_id': checkpoint.get('task_id'), 'target': checkpoint.get('target'), 'checkpoint_id': checkpoint.get('checkpoint_id')})
    return jsonify({'ok': True, 'checkpoint': checkpoint}), 200


@app.route('/tasks/reviews', methods=['GET'])
def task_reviews():
    return jsonify({'ok': True, 'count': len(agent.pending_fix_reviews()), 'reviews': agent.pending_fix_reviews()}), 200


@app.route('/tasks/<task_id>/approve-fix', methods=['POST'])
def task_approve_fix(task_id):
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is not True:
        return jsonify({'ok': False, 'task_id': task_id, 'error': 'confirm_required'}), 400
    result = agent.approve_pending_fix(task_id, confirm=True)
    if not result.get('ok'):
        return jsonify(result), 404 if result.get('error') == 'pending_review_not_found' else 400
    audit_security_event('security_mutation', 'review_approved', 200, required_scope_for_request(), {'task_id': task_id, 'target': result.get('target')})
    return jsonify(result), 200


@app.route('/tasks/<task_id>/reject-fix', methods=['POST'])
def task_reject_fix(task_id):
    data = request.get_json(silent=True) or {}
    reason = data.get('reason') or 'manual_reject'
    result = agent.reject_pending_fix(task_id, reason=reason)
    if not result.get('ok'):
        return jsonify(result), 404
    audit_security_event('security_mutation', 'review_rejected', 200, required_scope_for_request(), {'task_id': task_id, 'reason': reason})
    return jsonify(result), 200


@app.route('/integrity', methods=['GET'])
def integrity_summary():
    root = getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__)))
    task_integrity = agent.task_tape.verify_integrity()
    return jsonify({
        'ok': True,
        'ledgers': {
            'task_events': task_integrity['events'],
            'task_checkpoints': task_integrity['checkpoints'],
            'pointer_audit': agent.pointer_manager.verify_audit_integrity(),
            'security_audit': verify_hash_chain(security_audit_path()),
        },
        'root': root,
    }), 200

@app.route('/health', methods=['GET'])
def health():
    logger.info("Health check requested")
    gemini_version = "Unknown"
    try:
        result = subprocess.run(["gemini", "--version"], capture_output=True, text=True, timeout=5)
        gemini_version = result.stdout.strip()
    except Exception as e:
        gemini_version = f"Error: {e}"
    
    return jsonify({
        "status": "healthy",
        "engine": "CPOS Engine-Zero",
        "gemini_version": gemini_version
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"[*] CPOS Engine-Zero Server starting on port {port}...")
    app.run(host='0.0.0.0', port=port)
