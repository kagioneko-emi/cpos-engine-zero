from flask import Flask, request, jsonify, g, render_template
import os
import sys
import threading
import traceback
import logging
import subprocess
import hmac
import hashlib
import time
import ipaddress

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Ensure current directory is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.main_agent import MainAgent
from agents.github_reporter import GitHubReporter
from cpos.pointer_os import RetrievalPolicy
from cpos.security_audit import SecurityAuditLog
from cpos.hash_chain import verify_hash_chain
from cpos.mcp_registry import MCPRegistry
from cpos.nonce_store import NonceStore
from cpos.key_registry import HMACKeyRegistry
from cpos.rate_limit import FileBackedRateLimiter, InMemoryRateLimiter, RedisRateLimiter
from cpos.security_profile import apply_security_profile_defaults, effective_security_profile
from cpos.security_validation import validate_security_posture
from cpos.secret_inventory import latest_records
from cpos.footprint import build_footprint
from cpos.handoff_graph import build_handoff_graph
from cpos.handoff_inbox import handoff_inbox, approve_handoff, reject_handoff
from cpos.handoff_promotion import build_promotion_plan, create_promotion_pointer
from cpos.promotion_executor import create_execution_review, pending_execution_reviews, approve_execution_review, reject_execution_review
from cpos.resume_planner import build_next_action_proposals, create_resume_proposal_review, pending_resume_reviews, approve_resume_review, reject_resume_review
from cpos.mcp_execution import request_mcp_execution, pending_mcp_execution_reviews, approve_mcp_execution_review, reject_mcp_execution_review
from cpos.mcp_probe import request_mcp_capability_probe, pending_mcp_probe_reviews, approve_mcp_probe_review, reject_mcp_probe_review
from cpos.github_pr_flow import create_github_pr_dry_run, pending_github_pr_reviews, approve_github_pr_dry_run, reject_github_pr_dry_run
from cpos.github_diff_review import create_github_diff_review, pending_github_diff_reviews, approve_github_diff_review, reject_github_diff_review

apply_security_profile_defaults()

app = Flask(__name__, template_folder='templates', static_folder='static')
# Initialize MainAgent (it will handle its own sub-agents and sandbox)
agent = MainAgent()
github_reporter = GitHubReporter()
rate_limiter = InMemoryRateLimiter()
_file_rate_limiters = {}
_redis_rate_limiters = {}


def rate_limit_backend_summary():
    backend = os.environ.get('CPOS_RATE_LIMIT_BACKEND', 'memory').lower()
    root = getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__)))
    file_path = os.environ.get('CPOS_RATE_LIMIT_STORE_PATH') or os.path.join(root, 'cpos', 'rate_limit_state.json')
    redis_url_file = os.environ.get('CPOS_RATE_LIMIT_REDIS_URL_FILE')
    return {
        'enabled': os.environ.get('CPOS_RATE_LIMIT_ENABLED', 'false').lower() in {'1', 'true', 'yes'},
        'backend': backend,
        'file_store_path': file_path if backend == 'file' else None,
        'redis_url_file': redis_url_file if backend == 'redis' else None,
        'redis_configured': bool(redis_url_file) if backend == 'redis' else False,
    }


def _read_rate_limit_redis_url():
    url_file = os.environ.get('CPOS_RATE_LIMIT_REDIS_URL_FILE')
    if not url_file:
        return None
    try:
        value = open(url_file, encoding='utf-8').read().strip()
    except OSError:
        return None
    return value or None


def rate_limiter_for_request():
    backend = os.environ.get('CPOS_RATE_LIMIT_BACKEND', 'memory').lower()
    if backend == 'file':
        root = getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__)))
        path = os.environ.get('CPOS_RATE_LIMIT_STORE_PATH') or os.path.join(root, 'cpos', 'rate_limit_state.json')
        limiter = _file_rate_limiters.get(path)
        if limiter is None:
            limiter = FileBackedRateLimiter(path)
            _file_rate_limiters[path] = limiter
        return limiter, 'file', path
    if backend == 'redis':
        redis_url = _read_rate_limit_redis_url()
        if not redis_url:
            raise RuntimeError('rate_limit_redis_url_not_configured')
        key = (redis_url, os.environ.get('CPOS_RATE_LIMIT_REDIS_KEY_PREFIX', 'cpos:rate_limit'))
        limiter = _redis_rate_limiters.get(key)
        if limiter is None:
            limiter = RedisRateLimiter(redis_url, key_prefix=key[1])
            _redis_rate_limiters[key] = limiter
        return limiter, 'redis', None
    return rate_limiter, 'memory', None


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



def protected_request_path():
    return request.path != '/health' and request.path.startswith(('/pointers', '/tasks', '/handoff-inbox', '/handoff-graph', '/handoff-executions', '/resume-reviews', '/mcp', '/github', '/footprint', '/webhook', '/integrity', '/security-profile', '/dashboard'))


def client_ip():
    if os.environ.get('CPOS_TRUST_PROXY_HEADERS', 'false').lower() in {'1', 'true', 'yes'}:
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        if forwarded_for:
            return forwarded_for.split(',', 1)[0].strip()
    return request.remote_addr or 'unknown'


def parse_ip_allowlist():
    raw = os.environ.get('CPOS_IP_ALLOWLIST', '').strip()
    if not raw:
        return []
    networks = []
    for item in raw.replace('\n', ',').split(','):
        value = item.strip()
        if not value:
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            continue
    return networks


def ip_allowed(ip_value, networks):
    if not networks:
        return True
    try:
        address = ipaddress.ip_address(ip_value)
    except ValueError:
        return False
    return any(address in network for network in networks)


def mutation_request():
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        return True
    return False


def rate_limit_config():
    if os.environ.get('CPOS_RATE_LIMIT_ENABLED', 'false').lower() not in {'1', 'true', 'yes'}:
        return None
    try:
        window = int(os.environ.get('CPOS_RATE_LIMIT_WINDOW_SECONDS', '60'))
    except ValueError:
        window = 60
    try:
        default_limit = int(os.environ.get('CPOS_RATE_LIMIT_REQUESTS', '60'))
    except ValueError:
        default_limit = 60
    try:
        mutation_limit = int(os.environ.get('CPOS_MUTATION_RATE_LIMIT_REQUESTS', '10'))
    except ValueError:
        mutation_limit = 10
    return {
        'window': max(1, window),
        'limit': max(1, mutation_limit if mutation_request() else default_limit),
        'kind': 'mutation' if mutation_request() else 'default',
    }


def client_cert_required():
    return os.environ.get('CPOS_REQUIRE_CLIENT_CERT', 'false').lower() in {'1', 'true', 'yes'}


def client_cert_policy_mode():
    mode = os.environ.get('CPOS_CLIENT_CERT_POLICY_MODE', 'enforce').lower()
    return mode if mode in {'enforce', 'audit'} else 'enforce'


def client_cert_header_name():
    return os.environ.get('CPOS_CLIENT_CERT_FINGERPRINT_HEADER', 'X-SSL-Client-SHA256')


def load_client_cert_fingerprints():
    path = os.environ.get('CPOS_CLIENT_CERT_FINGERPRINTS_FILE')
    if not path:
        return None
    try:
        raw = open(path, encoding='utf-8').read()
    except OSError:
        return None
    fingerprints = set()
    for item in raw.replace('\n', ',').split(','):
        value = item.strip().lower().replace(':', '')
        if value:
            fingerprints.add(value)
    return fingerprints


def normalize_fingerprint(value):
    return value.strip().lower().replace(':', '')


def fingerprint_prefix(value):
    normalized = normalize_fingerprint(value)
    return normalized[:16] if normalized else ''

def security_audit_path():
    configured = os.environ.get('CPOS_SECURITY_AUDIT_PATH')
    if configured:
        return configured
    root = getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'cpos', 'security_audit.jsonl')


def security_audit_log():
    return SecurityAuditLog(security_audit_path())


def mcp_registry_path():
    configured = os.environ.get('CPOS_MCP_REGISTRY_PATH')
    if configured:
        return configured
    root = getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'cpos', 'mcp_connectors.json')


def mcp_audit_path():
    configured = os.environ.get('CPOS_MCP_AUDIT_PATH')
    if configured:
        return configured
    root = getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'cpos', 'mcp_audit.jsonl')


def mcp_review_path():
    configured = os.environ.get('CPOS_MCP_REVIEW_PATH')
    if configured:
        return configured
    root = getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'cpos', 'mcp_reviews.jsonl')


def mcp_registry():
    return MCPRegistry(mcp_registry_path(), mcp_audit_path(), mcp_review_path())


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
    return request.path.startswith(('/pointers', '/tasks', '/handoff-inbox', '/handoff-graph', '/handoff-executions', '/resume-reviews', '/mcp', '/github', '/footprint', '/webhook', '/integrity', '/security-profile'))


def required_scope_for_request():
    if request.path.startswith('/integrity') or request.path.startswith('/security-profile') or request.path.startswith('/footprint'):
        return 'read:integrity'
    if request.path == '/webhook':
        return 'webhook:github'
    if request.path.startswith('/pointers'):
        return 'read:pointers' if request.method == 'GET' else 'write:pointers'
    if request.path.startswith('/mcp'):
        return 'read:mcp' if request.method == 'GET' else 'write:mcp'
    if request.path.startswith('/github'):
        return 'read:github' if request.method == 'GET' else 'write:github'
    if request.path.startswith('/handoff-inbox') or request.path.startswith('/handoff-graph') or request.path.startswith('/handoff-executions') or request.path.startswith('/resume-reviews'):
        return 'read:reviews' if request.method == 'GET' else 'write:reviews'
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
def enforce_https_always():
    # Force redirects to https for all requests in production mode
    # For now, we strictly block non-https if the env says so.
    if os.environ.get('CPOS_ENFORCE_HTTPS', 'false').lower() in {'1', 'true', 'yes'}:
        forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
        if not (request.is_secure or forwarded_proto == 'https'):
            return jsonify({'ok': False, 'error': 'https_required'}), 403





@app.before_request
def enforce_client_cert_when_configured():
    if not protected_request_path() or not client_cert_required():
        return None
    required_scope = required_scope_for_request()
    mode = client_cert_policy_mode()
    fingerprints = load_client_cert_fingerprints()
    if not fingerprints:
        audit_security_event('network_policy', 'client_cert_fingerprints_not_configured', 503, required_scope)
        if mode == 'audit':
            return None
        return jsonify({'ok': False, 'error': 'client_cert_fingerprints_not_configured'}), 503
    header_name = client_cert_header_name()
    supplied = request.headers.get(header_name, '')
    if not supplied:
        audit_security_event('network_policy', 'client_cert_required', 401, required_scope, {'header': header_name})
        if mode == 'audit':
            return None
        return jsonify({'ok': False, 'error': 'client_cert_required'}), 401
    normalized = normalize_fingerprint(supplied)
    if normalized not in fingerprints:
        audit_security_event('network_policy', 'client_cert_denied', 403, required_scope, {'fingerprint_prefix': fingerprint_prefix(supplied)})
        if mode == 'audit':
            return None
        return jsonify({'ok': False, 'error': 'client_cert_denied'}), 403
    g.client_cert = {'verified': True, 'fingerprint_prefix': fingerprint_prefix(supplied)}
    audit_security_event('network_policy', 'client_cert_allowed', 200, required_scope, {'fingerprint_prefix': fingerprint_prefix(supplied)})
    return None

@app.before_request
def enforce_ip_allowlist_when_configured():
    if not protected_request_path():
        return None
    networks = parse_ip_allowlist()
    if not networks:
        return None
    ip_value = client_ip()
    if not ip_allowed(ip_value, networks):
        audit_security_event('network_policy', 'ip_denied', 403, required_scope_for_request(), {'ip': ip_value})
        return jsonify({'ok': False, 'error': 'ip_denied'}), 403
    return None


@app.before_request
def enforce_rate_limit_when_configured():
    if not protected_request_path():
        return None
    config = rate_limit_config()
    if config is None:
        return None
    ip_value = client_ip()
    key = f"{ip_value}:{config['kind']}"
    try:
        limiter, backend, store_path = rate_limiter_for_request()
        allowed, remaining, reset_after = limiter.allow(key, limit=config['limit'], window_seconds=config['window'])
    except RuntimeError as exc:
        audit_security_event('network_policy', str(exc), 503, required_scope_for_request(), {'kind': config['kind']})
        return jsonify({'ok': False, 'error': str(exc)}), 503
    if not allowed:
        audit_security_event('network_policy', 'rate_limited', 429, required_scope_for_request(), {'ip': ip_value, 'kind': config['kind'], 'backend': backend})
        response = jsonify({'ok': False, 'error': 'rate_limited', 'retry_after_seconds': int(reset_after)})
        response.headers['Retry-After'] = str(int(reset_after))
        response.headers['X-RateLimit-Limit'] = str(config['limit'])
        response.headers['X-RateLimit-Remaining'] = str(remaining)
        return response, 429
    g.rate_limit = {'limit': config['limit'], 'remaining': remaining, 'reset_after': reset_after, 'kind': config['kind'], 'backend': backend}
    return None

@app.before_request
def enforce_api_auth_when_configured():
    if request_needs_api_auth():
        return validate_api_auth_header()


@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';"
    rate_state = getattr(g, 'rate_limit', None)
    if rate_state:
        response.headers['X-RateLimit-Limit'] = str(rate_state['limit'])
        response.headers['X-RateLimit-Remaining'] = str(rate_state['remaining'])
    return response


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON data received"}), 400

    repo_name = data.get('repository', {}).get('full_name', 'demo/repo')
    
    # CASE 1: New Issue Opened (Initial Fix or Creation)
    if data.get('action') == 'opened' and 'issue' in data:
        issue = data['issue']
        issue_title = issue['title']
        issue_body = issue.get('body', '')
        issue_num = issue.get('number', 0)
        
        target_file = None
        match = re.search(r'(?:Fix|Target|File|Create):\s*([^\s,;]+)', issue_title + " " + issue_body, re.I)
        if match:
            target_file = match.group(1).strip()
        
        if "[CREATE]" in issue_title.upper() or "Create:" in (issue_title + " " + issue_body):
            try:
                parts = issue_title.split(":", 1)
                target_file = target_file or parts[0].replace("[CREATE]", "").strip()
                spec_title = parts[1].strip() if len(parts) > 1 else "New Module"
                
                logger.info(f"[*] Autonomous Creation Triggered: {target_file}")
                github_reporter.notify_analysis_started(repo_name, issue_num, target_file)
                thread = threading.Thread(target=run_tdd_thread, args=(target_file, spec_title, issue_body, repo_name, issue_num))
                thread.start()
                return jsonify({"status": "accepted", "mode": "creation", "target": target_file}), 202
            except Exception as e:
                logger.error(f"Error parsing creation request: {e}")
                return jsonify({"status": "error", "message": str(e)}), 400
        else:
            target_file = target_file or "workspace/test_app.py"
            logger.info(f"[*] Autonomous Fix Cycle Triggered for {target_file}: {issue_title}")
            github_reporter.notify_analysis_started(repo_name, issue_num, target_file)
            thread = threading.Thread(target=run_autonomous_cycle, args=(target_file, repo_name, issue_num))
            thread.start()
            return jsonify({"status": "accepted", "mode": "fix", "issue": issue_title, "target": target_file}), 202

    # CASE 2: Issue Comment Added (Follow-up Fix/Refinement)
    elif data.get('action') == 'created' and 'comment' in data and 'issue' in data:
        comment_body = data['comment'].get('body', '')
        issue = data['issue']
        issue_num = issue.get('number', 0)
        issue_title = issue.get('title', '')
        
        # Only respond if the comment mentions Engine-Zero or is a follow-up instruction
        if "Engine-Zero" in comment_body or "[RETRY]" in comment_body.upper() or "fix" in comment_body.lower():
            target_file = None
            # Try to find target file in comment or original issue
            match = re.search(r'(?:Fix|Target|File):\s*([^\s,;]+)', comment_body + " " + issue_title, re.I)
            if match:
                target_file = match.group(1).strip()
            
            target_file = target_file or "workspace/test_app.py"
            logger.info(f"[*] Iterative Fix Triggered by Comment on {repo_name}#{issue_num}: {target_file}")
            github_reporter.post_comment(repo_name, issue_num, f"🔄 **Follow-up Received**\n\nI am re-analyzing `{target_file}` based on your feedback: \"{comment_body[:100]}...\"")
            thread = threading.Thread(target=run_autonomous_cycle, args=(target_file, repo_name, issue_num))
            thread.start()
            return jsonify({"status": "accepted", "mode": "iteration", "target": target_file}), 202

    return jsonify({"status": "ignored", "message": "Event type not supported"}), 200

def run_autonomous_cycle(target_file, repo_name=None, issue_num=None):
    try:
        logger.info(f"[*] Starting background analysis for {target_file}...")
        result = agent.run_analysis(target_file, auto_fix=True)
        logger.info(f"[+] Background cycle completed for {target_file}.")
        
        if repo_name and issue_num and result:
            task_id = result.get('task_id')
            dashboard_url = os.environ.get('CPOS_DASHBOARD_URL', 'https://your-cpos-node:8080/dashboard')
            github_reporter.notify_fix_proposed(repo_name, issue_num, task_id, dashboard_url)
            
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



@app.route('/github/pr-dry-runs', methods=['GET'])
def github_pr_dry_run_reviews():
    reviews = pending_github_pr_reviews(agent.task_tape)
    return jsonify({'ok': True, 'count': len(reviews), 'reviews': reviews}), 200


@app.route('/github/pr-dry-runs', methods=['POST'])
def github_pr_dry_run_create():
    data = request.get_json(silent=True) or {}
    result = create_github_pr_dry_run(
        agent.task_tape,
        repo=data.get('repo') or 'kagioneko/cpos-engine-zero',
        title=data.get('title') or '',
        issue_url=data.get('issue_url'),
        issue_number=data.get('issue_number'),
        summary=data.get('summary'),
        files=data.get('files') if isinstance(data.get('files'), list) else [],
        metadata=data.get('metadata') if isinstance(data.get('metadata'), dict) else {},
        actor=request_actor(),
        base_branch=data.get('base_branch') or 'main',
        dry_run=data.get('dry_run', True) is not False,
    )
    status = 200 if result.get('ok') else 400
    audit_security_event('security_mutation', 'github_pr_dry_run_created' if result.get('ok') else result.get('error', 'github_pr_dry_run_denied'), status, required_scope_for_request(), {'task_id': result.get('task_id'), 'repo': data.get('repo'), 'issue_number': data.get('issue_number')})
    return jsonify(result), status


@app.route('/github/pr-dry-runs/<task_id>/approve', methods=['POST'])
def github_pr_dry_run_approve(task_id):
    data = request.get_json(silent=True) or {}
    result = approve_github_pr_dry_run(agent.task_tape, task_id, approver=request_actor(), reason=data.get('reason'), confirm=data.get('confirm') is True)
    status = 200 if result.get('ok') else (404 if result.get('error') == 'pending_github_pr_review_not_found' else 400)
    audit_security_event('security_mutation', 'github_pr_dry_run_approved' if result.get('ok') else result.get('error', 'github_pr_dry_run_approve_denied'), status, required_scope_for_request(), {'task_id': task_id})
    return jsonify(result), status


@app.route('/github/pr-dry-runs/<task_id>/reject', methods=['POST'])
def github_pr_dry_run_reject(task_id):
    data = request.get_json(silent=True) or {}
    result = reject_github_pr_dry_run(agent.task_tape, task_id, reason=data.get('reason') or 'manual_reject')
    status = 200 if result.get('ok') else 404
    audit_security_event('security_mutation', 'github_pr_dry_run_rejected' if result.get('ok') else result.get('error', 'github_pr_dry_run_reject_denied'), status, required_scope_for_request(), {'task_id': task_id, 'reason': data.get('reason')})
    return jsonify(result), status


@app.route('/github/diff-reviews', methods=['GET'])
def github_diff_review_reviews():
    reviews = pending_github_diff_reviews(agent.task_tape)
    return jsonify({'ok': True, 'count': len(reviews), 'reviews': reviews}), 200


@app.route('/github/pr-dry-runs/<source_task_id>/create-diff-review', methods=['POST'])
def github_diff_review_create(source_task_id):
    data = request.get_json(silent=True) or {}
    result = create_github_diff_review(
        agent.task_tape,
        source_task_id=source_task_id,
        diff_text=data.get('diff_text') or '',
        changed_files=data.get('changed_files') if isinstance(data.get('changed_files'), list) else [],
        validation_commands=data.get('validation_commands') if isinstance(data.get('validation_commands'), list) else [],
        actor=request_actor(),
        dry_run=data.get('dry_run', True) is not False,
    )
    status = 200 if result.get('ok') else 400
    audit_security_event('security_mutation', 'github_diff_review_created' if result.get('ok') else result.get('error', 'github_diff_review_denied'), status, required_scope_for_request(), {'task_id': result.get('task_id'), 'source_task_id': source_task_id})
    return jsonify(result), status


@app.route('/github/diff-reviews/<task_id>/approve', methods=['POST'])
def github_diff_review_approve(task_id):
    data = request.get_json(silent=True) or {}
    result = approve_github_diff_review(agent.task_tape, task_id, approver=request_actor(), reason=data.get('reason'), confirm=data.get('confirm') is True)
    status = 200 if result.get('ok') else (404 if result.get('error') == 'pending_github_diff_review_not_found' else 400)
    audit_security_event('security_mutation', 'github_diff_review_approved' if result.get('ok') else result.get('error', 'github_diff_review_approve_denied'), status, required_scope_for_request(), {'task_id': task_id})
    return jsonify(result), status


@app.route('/github/diff-reviews/<task_id>/reject', methods=['POST'])
def github_diff_review_reject(task_id):
    data = request.get_json(silent=True) or {}
    result = reject_github_diff_review(agent.task_tape, task_id, reason=data.get('reason') or 'manual_reject')
    status = 200 if result.get('ok') else 404
    audit_security_event('security_mutation', 'github_diff_review_rejected' if result.get('ok') else result.get('error', 'github_diff_review_reject_denied'), status, required_scope_for_request(), {'task_id': task_id, 'reason': data.get('reason')})
    return jsonify(result), status


@app.route('/mcp/probes', methods=['GET'])
def mcp_probe_reviews():
    reviews = pending_mcp_probe_reviews(agent.task_tape)
    return jsonify({'ok': True, 'count': len(reviews), 'reviews': reviews}), 200


@app.route('/mcp/probes/dry-run', methods=['POST'])
def mcp_probe_dry_run():
    data = request.get_json(silent=True) or {}
    connector_id = data.get('connector_id')
    if not connector_id:
        return jsonify({'ok': False, 'error': 'connector_id_required'}), 400
    result = request_mcp_capability_probe(
        mcp_registry(),
        agent.task_tape,
        connector_id=str(connector_id),
        actor=request_actor(),
        purpose=data.get('purpose') or 'http_mcp_capability_probe',
        dry_run=data.get('dry_run', True) is not False,
    )
    status = 200 if result.get('ok') else 400
    audit_security_event('security_mutation', 'mcp_probe_dry_run_requested' if result.get('ok') else result.get('error', 'mcp_probe_denied'), status, required_scope_for_request(), {'connector_id': connector_id, 'task_id': result.get('task_id')})
    return jsonify(result), status


@app.route('/mcp/probes/<task_id>/approve', methods=['POST'])
def mcp_probe_approve(task_id):
    data = request.get_json(silent=True) or {}
    result = approve_mcp_probe_review(agent.task_tape, task_id, approver=request_actor(), reason=data.get('reason'), confirm=data.get('confirm') is True)
    status = 200 if result.get('ok') else (404 if result.get('error') == 'pending_mcp_probe_review_not_found' else 400)
    audit_security_event('security_mutation', 'mcp_probe_approved' if result.get('ok') else result.get('error', 'mcp_probe_approve_denied'), status, required_scope_for_request(), {'task_id': task_id})
    return jsonify(result), status


@app.route('/mcp/probes/<task_id>/reject', methods=['POST'])
def mcp_probe_reject(task_id):
    data = request.get_json(silent=True) or {}
    result = reject_mcp_probe_review(agent.task_tape, task_id, reason=data.get('reason') or 'manual_reject')
    status = 200 if result.get('ok') else 404
    audit_security_event('security_mutation', 'mcp_probe_rejected' if result.get('ok') else result.get('error', 'mcp_probe_reject_denied'), status, required_scope_for_request(), {'task_id': task_id, 'reason': data.get('reason')})
    return jsonify(result), status


@app.route('/mcp/executions', methods=['GET'])
def mcp_execution_reviews():
    reviews = pending_mcp_execution_reviews(agent.task_tape)
    return jsonify({'ok': True, 'count': len(reviews), 'reviews': reviews}), 200


@app.route('/mcp/executions/dry-run', methods=['POST'])
def mcp_execution_dry_run():
    data = request.get_json(silent=True) or {}
    connector_id = data.get('connector_id')
    tool_name = data.get('tool_name')
    if not connector_id or not tool_name:
        return jsonify({'ok': False, 'error': 'connector_id_and_tool_name_required'}), 400
    result = request_mcp_execution(
        mcp_registry(),
        agent.task_tape,
        connector_id=str(connector_id),
        tool_name=str(tool_name),
        arguments=data.get('arguments') or {},
        actor=request_actor(),
        purpose=data.get('purpose') or 'http_mcp_dry_run',
        dry_run=data.get('dry_run', True) is not False,
    )
    status = 200 if result.get('ok') else 400
    audit_security_event('security_mutation', 'mcp_execution_dry_run_requested' if result.get('ok') else result.get('error', 'mcp_execution_dry_run_denied'), status, required_scope_for_request(), {'connector_id': connector_id, 'tool_name': tool_name, 'task_id': result.get('task_id'), 'decision': (result.get('decision') or {}).get('decision')})
    return jsonify(result), status


@app.route('/mcp/executions/<task_id>/approve', methods=['POST'])
def mcp_execution_approve(task_id):
    data = request.get_json(silent=True) or {}
    result = approve_mcp_execution_review(agent.task_tape, task_id, approver=request_actor(), reason=data.get('reason'), confirm=data.get('confirm') is True)
    status = 200 if result.get('ok') else (404 if result.get('error') == 'pending_mcp_execution_review_not_found' else 400)
    audit_security_event('security_mutation', 'mcp_execution_approved' if result.get('ok') else result.get('error', 'mcp_execution_approve_denied'), status, required_scope_for_request(), {'task_id': task_id})
    return jsonify(result), status


@app.route('/mcp/executions/<task_id>/reject', methods=['POST'])
def mcp_execution_reject(task_id):
    data = request.get_json(silent=True) or {}
    result = reject_mcp_execution_review(agent.task_tape, task_id, reason=data.get('reason') or 'manual_reject')
    status = 200 if result.get('ok') else 404
    audit_security_event('security_mutation', 'mcp_execution_rejected' if result.get('ok') else result.get('error', 'mcp_execution_reject_denied'), status, required_scope_for_request(), {'task_id': task_id, 'reason': data.get('reason')})
    return jsonify(result), status


@app.route('/mcp/reviews', methods=['GET'])
def mcp_review_list():
    status = request.args.get('status')
    reviews = mcp_registry().reviews(status=status)
    return jsonify({'ok': True, 'count': len(reviews), 'reviews': reviews}), 200


@app.route('/mcp/reviews', methods=['POST'])
def mcp_review_submit():
    data = request.get_json(silent=True) or {}
    result = mcp_registry().submit_review(data, actor=request_actor())
    status = 200 if result.get('ok') else 400
    audit_security_event('security_mutation', 'mcp_review_submitted' if result.get('ok') else result.get('error', 'mcp_review_submit_denied'), status, required_scope_for_request(), {'review_id': (result.get('review') or {}).get('review_id'), 'connector_id': (result.get('review') or {}).get('connector_id'), 'finding_codes': [f.get('code') for f in result.get('findings', [])]})
    return jsonify(result), status


@app.route('/mcp/reviews/<review_id>/approve', methods=['POST'])
def mcp_review_approve(review_id):
    data = request.get_json(silent=True) or {}
    result = mcp_registry().approve_review(review_id, actor=request_actor(), reason=data.get('reason'), confirm=data.get('confirm') is True)
    status = 200 if result.get('ok') else (404 if result.get('error') == 'review_not_found' else 400)
    audit_security_event('security_mutation', 'mcp_review_approved' if result.get('ok') else result.get('error', 'mcp_review_approve_denied'), status, required_scope_for_request(), {'review_id': review_id})
    return jsonify(result), status


@app.route('/mcp/reviews/<review_id>/reject', methods=['POST'])
def mcp_review_reject(review_id):
    data = request.get_json(silent=True) or {}
    reason = data.get('reason') or 'manual_reject'
    result = mcp_registry().reject_review(review_id, actor=request_actor(), reason=reason)
    status = 200 if result.get('ok') else (404 if result.get('error') == 'review_not_found' else 400)
    audit_security_event('security_mutation', 'mcp_review_rejected' if result.get('ok') else result.get('error', 'mcp_review_reject_denied'), status, required_scope_for_request(), {'review_id': review_id, 'reason': reason})
    return jsonify(result), status


@app.route('/mcp/connectors/check', methods=['POST'])
def mcp_connector_check():
    data = request.get_json(silent=True) or {}
    result = mcp_registry().check_definition(data, actor=request_actor())
    status = 200 if result.get('ok') else 400
    audit_security_event('security_mutation', 'mcp_definition_check_passed' if result.get('ok') else 'mcp_definition_check_failed', status, required_scope_for_request(), {'finding_codes': [f.get('code') for f in result.get('findings', [])]})
    return jsonify(result), status


@app.route('/mcp/connectors', methods=['GET'])
def mcp_connector_list():
    connectors = [connector.to_dict() for connector in mcp_registry().load()]
    return jsonify({'ok': True, 'count': len(connectors), 'connectors': connectors}), 200


@app.route('/mcp/connectors', methods=['POST'])
def mcp_connector_register():
    data = request.get_json(silent=True) or {}
    result = mcp_registry().register(data, actor=request_actor(), confirm=data.get('confirm') is True)
    status = 200 if result.get('ok') else 400
    audit_security_event('security_mutation', 'mcp_connector_registered' if result.get('ok') else result.get('error', 'mcp_registration_denied'), status, required_scope_for_request(), {'connector_id': (result.get('connector') or {}).get('connector_id')})
    return jsonify(result), status


@app.route('/mcp/connectors/<path:connector_id>/disable', methods=['POST'])
def mcp_connector_disable(connector_id):
    data = request.get_json(silent=True) or {}
    result = mcp_registry().disable(connector_id, actor=request_actor(), reason=data.get('reason') or 'manual_disable')
    status = 200 if result.get('ok') else 404
    audit_security_event('security_mutation', 'mcp_connector_disabled' if result.get('ok') else 'mcp_connector_disable_failed', status, required_scope_for_request(), {'connector_id': connector_id, 'reason': data.get('reason')})
    return jsonify(result), status


@app.route('/mcp/connectors/<path:connector_id>/check-tool', methods=['POST'])
def mcp_connector_check_tool(connector_id):
    data = request.get_json(silent=True) or {}
    tool_name = data.get('tool_name')
    if not tool_name:
        return jsonify({'ok': False, 'error': 'tool_name_required'}), 400
    result = mcp_registry().evaluate_tool_call(connector_id, str(tool_name), actor=request_actor(), purpose=data.get('purpose') or 'http_tool_check')
    status = 200 if result.get('ok') else 404
    audit_security_event('security_mutation', 'mcp_tool_call_evaluated', status, required_scope_for_request(), {'connector_id': connector_id, 'tool_name': tool_name, 'decision': result.get('decision')})
    return jsonify(result), status

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


@app.route('/handoff-graph', methods=['GET'])
def handoff_graph_summary():
    return jsonify(build_handoff_graph(
        agent.pointer_manager,
        agent.task_tape,
        source_pointer_id=request.args.get('source_pointer_id'),
        review_status=request.args.get('review_status'),
        limit=int(request.args.get('limit', '50')),
    )), 200


@app.route('/handoff-inbox', methods=['GET'])
def handoff_inbox_list():
    status = request.args.get('status', 'pending')
    limit_arg = request.args.get('limit')
    try:
        limit = int(limit_arg) if limit_arg else None
        handoffs = handoff_inbox(agent.pointer_manager, status=status, limit=limit)
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    return jsonify({'ok': True, 'count': len(handoffs), 'handoffs': handoffs}), 200


@app.route('/handoff-inbox/<path:pointer_id>/approve', methods=['POST'])
def handoff_inbox_approve(pointer_id):
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is not True:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'confirm_required'}), 400
    try:
        pointer = approve_handoff(
            agent.pointer_manager,
            pointer_id,
            reviewer=data.get('reviewer') or request_actor(),
            reason=data.get('reason'),
        )
    except ValueError as e:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': str(e)}), 400
    if pointer is None:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'not_found'}), 404
    audit_security_event('security_mutation', 'handoff_approved', 200, required_scope_for_request(), {'pointer_id': pointer_id, 'reason': data.get('reason')})
    return jsonify({'ok': True, 'pointer': pointer.to_dict()}), 200


@app.route('/handoff-inbox/<path:pointer_id>/reject', methods=['POST'])
def handoff_inbox_reject(pointer_id):
    data = request.get_json(silent=True) or {}
    reason = data.get('reason') or 'manual_reject'
    try:
        pointer = reject_handoff(
            agent.pointer_manager,
            pointer_id,
            reviewer=data.get('reviewer') or request_actor(),
            reason=reason,
        )
    except ValueError as e:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': str(e)}), 400
    if pointer is None:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'not_found'}), 404
    audit_security_event('security_mutation', 'handoff_rejected', 200, required_scope_for_request(), {'pointer_id': pointer_id, 'reason': reason})
    return jsonify({'ok': True, 'pointer': pointer.to_dict()}), 200


@app.route('/handoff-inbox/<path:pointer_id>/promotion-plan', methods=['GET'])
def handoff_inbox_promotion_plan(pointer_id):
    pointer = next((p for p in agent.pointer_manager.load() if p.pointer_id == pointer_id), None)
    if pointer is None:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'not_found'}), 404
    try:
        plan = build_promotion_plan(pointer)
    except ValueError as e:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': str(e)}), 400
    return jsonify({'ok': True, 'plan': plan}), 200


@app.route('/handoff-inbox/<path:pointer_id>/promote', methods=['POST'])
def handoff_inbox_promote(pointer_id):
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is not True:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'confirm_required'}), 400
    try:
        pointer = create_promotion_pointer(
            agent.pointer_manager,
            pointer_id,
            reviewer=data.get('reviewer') or request_actor(),
            reason=data.get('reason'),
        )
    except ValueError as e:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': str(e)}), 400
    if pointer is None:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'not_found'}), 404
    audit_security_event('security_mutation', 'handoff_promotion_planned', 200, required_scope_for_request(), {'pointer_id': pointer_id, 'promotion_pointer_id': pointer.pointer_id, 'reason': data.get('reason')})
    return jsonify({'ok': True, 'pointer': pointer.to_dict()}), 200


@app.route('/handoff-inbox/<path:pointer_id>/execute-plan', methods=['POST'])
def handoff_inbox_execute_plan(pointer_id):
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is not True:
        return jsonify({'ok': False, 'pointer_id': pointer_id, 'error': 'confirm_required'}), 400
    result = create_execution_review(
        agent.pointer_manager,
        agent.task_tape,
        pointer_id,
        requester=data.get('requester') or request_actor(),
        reason=data.get('reason'),
    )
    if not result.get('ok'):
        return jsonify(result), 404 if result.get('error') == 'promotion_pointer_not_found' else 400
    audit_security_event('security_mutation', 'handoff_promotion_execution_review_created', 200, required_scope_for_request(), {'pointer_id': pointer_id, 'task_id': result.get('task_id'), 'reason': data.get('reason')})
    return jsonify(result), 200


@app.route('/handoff-executions', methods=['GET'])
def handoff_execution_reviews():
    reviews = pending_execution_reviews(agent.task_tape)
    return jsonify({'ok': True, 'count': len(reviews), 'reviews': reviews}), 200


@app.route('/handoff-executions/<task_id>/approve', methods=['POST'])
def handoff_execution_approve(task_id):
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is not True:
        return jsonify({'ok': False, 'task_id': task_id, 'error': 'confirm_required'}), 400
    result = approve_execution_review(agent.task_tape, task_id, approver=data.get('approver') or request_actor(), reason=data.get('reason'))
    if not result.get('ok'):
        return jsonify(result), 404
    audit_security_event('security_mutation', 'handoff_promotion_execution_approved', 200, required_scope_for_request(), {'task_id': task_id, 'reason': data.get('reason')})
    return jsonify(result), 200


@app.route('/handoff-executions/<task_id>/reject', methods=['POST'])
def handoff_execution_reject(task_id):
    data = request.get_json(silent=True) or {}
    result = reject_execution_review(agent.task_tape, task_id, reason=data.get('reason') or 'manual_reject')
    if not result.get('ok'):
        return jsonify(result), 404
    audit_security_event('security_mutation', 'handoff_promotion_execution_rejected', 200, required_scope_for_request(), {'task_id': task_id, 'reason': data.get('reason')})
    return jsonify(result), 200


@app.route('/handoff-executions/<task_id>/resume-plan', methods=['GET'])
def handoff_execution_resume_plan(task_id):
    result = build_next_action_proposals(agent.task_tape, task_id)
    if not result.get('ok'):
        return jsonify(result), 404 if result.get('error') == 'execution_review_not_ready' else 400
    return jsonify(result), 200


@app.route('/handoff-executions/<task_id>/create-resume-review', methods=['POST'])
def handoff_execution_create_resume_review(task_id):
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is not True:
        return jsonify({'ok': False, 'task_id': task_id, 'error': 'confirm_required'}), 400
    result = create_resume_proposal_review(agent.task_tape, task_id, proposer=data.get('proposer') or request_actor(), reason=data.get('reason'))
    if not result.get('ok'):
        return jsonify(result), 400
    audit_security_event('security_mutation', 'execution_resume_review_created', 200, required_scope_for_request(), {'task_id': task_id, 'reason': data.get('reason')})
    return jsonify(result), 200


@app.route('/resume-reviews', methods=['GET'])
def resume_reviews_list():
    reviews = pending_resume_reviews(agent.task_tape)
    return jsonify({'ok': True, 'count': len(reviews), 'reviews': reviews}), 200


@app.route('/resume-reviews/<task_id>/approve', methods=['POST'])
def resume_review_approve(task_id):
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is not True:
        return jsonify({'ok': False, 'task_id': task_id, 'error': 'confirm_required'}), 400
    result = approve_resume_review(agent.task_tape, task_id, approver=data.get('approver') or request_actor(), action_id=data.get('action_id'), reason=data.get('reason'))
    if not result.get('ok'):
        return jsonify(result), 404 if result.get('error') == 'pending_resume_review_not_found' else 400
    audit_security_event('security_mutation', 'execution_resume_action_approved', 200, required_scope_for_request(), {'task_id': task_id, 'action_id': result.get('approved_action_id')})
    return jsonify(result), 200


@app.route('/resume-reviews/<task_id>/reject', methods=['POST'])
def resume_review_reject(task_id):
    data = request.get_json(silent=True) or {}
    result = reject_resume_review(agent.task_tape, task_id, reason=data.get('reason') or 'manual_reject')
    if not result.get('ok'):
        return jsonify(result), 404
    audit_security_event('security_mutation', 'execution_resume_action_rejected', 200, required_scope_for_request(), {'task_id': task_id, 'reason': data.get('reason')})
    return jsonify(result), 200


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
            'mcp_audit': verify_hash_chain(mcp_audit_path()),
            'mcp_reviews': verify_hash_chain(mcp_review_path()),
        },
        'root': root,
    }), 200


def secret_inventory_summary():
    path = default_secret_inventory_path_for_server()
    records = list(latest_records(path).values()) if os.path.exists(path) else []
    by_status = {}
    for record in records:
        status = str(record.get('status', 'unknown'))
        by_status[status] = by_status.get(status, 0) + 1
    return {'count': len(records), 'by_status': by_status, 'records': records[-10:]}


def default_secret_inventory_path_for_server():
    return os.environ.get('CPOS_SECRET_INVENTORY_PATH') or os.path.join(getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__))), 'cpos', 'secret_inventory.jsonl')


@app.route('/footprint', methods=['GET'])
def footprint_summary():
    root = getattr(agent, 'project_root', os.path.dirname(os.path.abspath(__file__)))
    return jsonify(build_footprint(
        pointer_path=getattr(agent, 'pointers_path', os.path.join(root, 'cpos', 'pointers.jsonl')),
        pointer_audit_path=getattr(agent, 'audit_log_path', os.path.join(root, 'cpos', 'audit_log.jsonl')),
        task_tape_path=getattr(agent, 'task_tape_path', os.path.join(root, 'tapes', 'task_runs.jsonl')),
        task_checkpoint_path=getattr(agent, 'task_checkpoint_path', os.path.join(root, 'tapes', 'task_checkpoints.jsonl')),
        security_audit_path=security_audit_path(),
        secret_inventory_path=default_secret_inventory_path_for_server(),
    )), 200


@app.route('/security-profile', methods=['GET'])
def security_profile_summary():
    docker_available = agent.sandbox.docker_available() if hasattr(agent, 'sandbox') else None
    return jsonify({
        'ok': True,
        'security_profile': effective_security_profile(),
        'validation': validate_security_posture(docker_available=docker_available),
        'secret_inventory': secret_inventory_summary(),
        'rate_limit': rate_limit_backend_summary(),
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

def run_tdd_thread(target_file, spec_title, issue_body, repo_name=None, issue_num=None):
    try:
        logger.info(f"[*] Starting background TDD creation for {target_file}...")
        agent.run_tdd_creation(target_file, spec_title, issue_body)
        logger.info(f"[+] Background TDD creation completed for {target_file}.")
        if repo_name and issue_num:
            github_reporter.post_comment(repo_name, issue_num, f"✅ **Autonomous Creation Completed**\n\nTarget: `{target_file}` has been initialized with TDD patterns.")
    except Exception as e:
        logger.error(f"[!] Background TDD creation failed: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    is_cloud_run = os.environ.get('K_SERVICE') is not None
    
    if is_cloud_run:
        logger.info(f"[*] CPOS Engine-Zero starting on Google Cloud Run (Port {port}). SSL handled by Infrastructure.")
        # On Cloud Run, Google handles SSL. We just run HTTP locally, 
        # but our before_request handler still enforces HTTPS via headers.
        app.run(host='0.0.0.0', port=port)
    else:
        logger.info(f"[*] CPOS Engine-Zero Secure Server starting on port {port} (HTTPS)...")
        cert_path = 'certs/cert.pem'
        key_path = 'certs/key.pem'
        script_dir = os.path.dirname(os.path.abspath(__file__))
        abs_cert = os.path.join(script_dir, cert_path)
        abs_key = os.path.join(script_dir, key_path)
        
        if os.path.exists(abs_cert) and os.path.exists(abs_key):
            app.run(host='0.0.0.0', port=port, ssl_context=(abs_cert, abs_key))
        else:
            logger.warning("[!] SSL Certificates not found. Falling back to HTTP (NOT RECOMMENDED).")
            app.run(host='0.0.0.0', port=port)
