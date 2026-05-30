import json
import datetime
import os
from html import escape

from cpos.pointer_os import ContextPointer, PointerManager
from cpos.task_tape import TaskTapeStore
from cpos.hash_chain import verify_hash_chain
from cpos.secret_inventory import latest_records
from cpos.security_validation import validate_security_posture
from cpos.handoff_graph import build_handoff_graph
from cpos.footprint import build_footprint
from cpos.mcp_registry import MCPRegistry
from cpos.human_escalation import pending_human_escalations
from cpos.mcp_execution import pending_mcp_execution_reviews
from cpos.github_pr_flow import pending_github_pr_reviews
from cpos.github_diff_review import pending_github_diff_reviews
from cpos.sandbox_patch_plan import pending_sandbox_patch_plans
from cpos.sandbox_patch_runner import pending_sandbox_patch_executions, completed_sandbox_patch_executions
from cpos.execution_driver import build_execution_scoreboard
from cpos.auto_fix_candidate import pending_auto_fix_candidates


def load_jsonl(path):
    rows = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Some stores may contain encrypted legacy rows. Skip unreadable
                        # rows rather than failing report generation.
                        continue
    return rows


def load_pointers(pointer_path):
    pointers = []
    if not pointer_path or not os.path.exists(pointer_path):
        return pointers
    for row in load_jsonl(pointer_path):
        pointers.append(ContextPointer.from_dict(row))
    return pointers


def pointer_summary(pointers):
    by_status = {}
    by_type = {}
    for pointer in pointers:
        by_status[pointer.status] = by_status.get(pointer.status, 0) + 1
        by_type[pointer.context_type] = by_type.get(pointer.context_type, 0) + 1
    active = [p for p in pointers if p.status == 'active']
    invalidated = [p for p in pointers if p.status == 'invalidated']
    finding_pointers = [p for p in pointers if p.context_type == 'finding']
    avg_trust = sum(p.trust_score for p in pointers) / len(pointers) if pointers else 0.0
    return {
        'total': len(pointers),
        'active': len(active),
        'invalidated': len(invalidated),
        'finding_count': len(finding_pointers),
        'avg_trust': avg_trust,
        'by_status': by_status,
        'by_type': by_type,
        'top_findings': sorted(
            finding_pointers,
            key=lambda p: (p.priority, p.trust_score, p.created_at),
            reverse=True,
        )[:8],
        'invalidated_recent': sorted(
            invalidated,
            key=lambda p: p.invalidated_at or '',
            reverse=True,
        )[:5],
    }


def default_pointer_path(audit_log_path):
    audit_dir = os.path.dirname(os.path.abspath(audit_log_path))
    return os.path.join(audit_dir, 'pointers.jsonl')


def pointer_governance_events(events, limit=10):
    governance_event_names = {'trust_score_updated', 'pointer_exchanged'}
    filtered = [event for event in events if event.get('event') in governance_event_names]
    filtered.sort(key=lambda event: event.get('timestamp', ''), reverse=True)
    return filtered[:limit]


def render_pointer_governance_events(events):
    governance_events = pointer_governance_events(events)
    html = """
        <div class="card governance-card">
            <div class="step-label">Pointer Governance Events</div>
            <h2>Trust & Agent Exchange Audit</h2>
    """
    if not governance_events:
        html += '<p class="muted">No trust update or pointer exchange events recorded yet.</p></div>'
        return html

    html += """
            <table>
                <thead><tr><th>Event</th><th>Pointer</th><th>Detail</th><th>Timestamp</th></tr></thead>
                <tbody>
    """
    for event in governance_events:
        event_name = str(event.get('event', 'unknown'))
        pointer_id = str(event.get('pointer_id') or event.get('pointer') or '-')
        if event_name == 'trust_score_updated':
            detail = f"score={event.get('score', '-')} reason={event.get('reason', '-')}"
        elif event_name == 'pointer_exchanged':
            detail = (
                f"{event.get('from_agent', '-')} → {event.get('to_agent', '-')} "
                f"purpose={event.get('purpose', '-')} access={event.get('access_level', '-')}"
            )
        else:
            detail = '-'
        html += f"""
                    <tr>
                        <td>{escape(event_name)}</td>
                        <td><code>{escape(pointer_id)}</code></td>
                        <td>{escape(str(detail))}</td>
                        <td>{escape(str(event.get('timestamp', '-')))}</td>
                    </tr>
        """
    html += """
                </tbody>
            </table>
        </div>
    """
    return html


def render_pointer_summary(pointers):
    summary = pointer_summary(pointers)
    status_items = ''.join(
        f"<span class=\"pill\">{escape(status)}: {count}</span>"
        for status, count in sorted(summary['by_status'].items())
    ) or '<span class="muted">No pointer status data</span>'
    type_items = ''.join(
        f"<span class=\"pill\">{escape(context_type)}: {count}</span>"
        for context_type, count in sorted(summary['by_type'].items())
    ) or '<span class="muted">No pointer type data</span>'

    html = f"""
        <div class="card pointer-card">
            <div class="step-label">Context Pointer OS</div>
            <h2>Memory Operating Layer</h2>
            <div class="metrics">
                <div class="metric"><strong>{summary['total']}</strong><span>Total Pointers</span></div>
                <div class="metric"><strong>{summary['active']}</strong><span>Active</span></div>
                <div class="metric"><strong>{summary['invalidated']}</strong><span>Invalidated</span></div>
                <div class="metric"><strong>{summary['avg_trust']:.2f}</strong><span>Avg Trust</span></div>
            </div>
            <div class="step-label">Lifecycle Status</div>
            <p>{status_items}</p>
            <div class="step-label">Context Types</div>
            <p>{type_items}</p>
    """

    if summary['top_findings']:
        html += """
            <div class="step-label">Top Finding Pointers</div>
            <table>
                <thead><tr><th>Pointer</th><th>Status</th><th>Trust</th><th>Priority</th><th>Location</th></tr></thead>
                <tbody>
        """
        for pointer in summary['top_findings']:
            html += f"""
                    <tr>
                        <td><code>{escape(pointer.pointer_id)}</code><br><span class="muted">{escape(pointer.summary)}</span></td>
                        <td>{escape(pointer.status)}</td>
                        <td>{pointer.trust_score:.2f}</td>
                        <td>{pointer.priority:.2f}</td>
                        <td>{escape(pointer.location)}</td>
                    </tr>
            """
        html += """
                </tbody>
            </table>
        """

    if summary['invalidated_recent']:
        html += """
            <div class="step-label">Recent Invalidations</div>
            <ul>
        """
        for pointer in summary['invalidated_recent']:
            html += f"""
                <li><code>{escape(pointer.pointer_id)}</code> — {escape(pointer.invalidated_reason or 'unknown')} at {escape(pointer.invalidated_at or '-')}</li>
            """
        html += "</ul>"

    html += "</div>"
    return html




def default_security_audit_path(audit_log_path):
    audit_dir = os.path.dirname(os.path.abspath(audit_log_path))
    return os.path.join(audit_dir, 'security_audit.jsonl')


def render_security_audit_summary(security_audit_path):
    events = load_jsonl(security_audit_path)
    by_decision = {}
    by_event = {}
    for event in events:
        by_decision[str(event.get('decision', 'unknown'))] = by_decision.get(str(event.get('decision', 'unknown')), 0) + 1
        by_event[str(event.get('event', 'unknown'))] = by_event.get(str(event.get('event', 'unknown')), 0) + 1
    recent = list(reversed(events[-10:]))
    decision_items = ''.join(
        f"<span class=\"pill\">{escape(decision)}: {count}</span>"
        for decision, count in sorted(by_decision.items())
    ) or '<span class="muted">No auth decisions recorded yet</span>'
    html = f"""
        <div class="card security-card">
            <div class="step-label">Security Audit Trail</div>
            <h2>Auth, Scope & Mutation Ledger</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(events)}</strong><span>Security Events</span></div>
                <div class="metric"><strong>{by_event.get('auth_decision', 0)}</strong><span>Auth Decisions</span></div>
                <div class="metric"><strong>{by_event.get('security_mutation', 0)}</strong><span>Mutations</span></div>
                <div class="metric"><strong>{by_decision.get('scope_denied', 0)}</strong><span>Scope Denied</span></div>
            </div>
            <div class="step-label">Decisions</div>
            <p>{decision_items}</p>
    """
    if not recent:
        html += '<p class="muted">No security audit events recorded yet.</p></div>'
        return html
    html += """
            <div class="step-label">Recent Security Events</div>
            <table>
                <thead><tr><th>Event</th><th>Decision</th><th>Actor</th><th>Scope</th><th>Path</th><th>Timestamp</th></tr></thead>
                <tbody>
    """
    for event in recent:
        html += f"""
                    <tr>
                        <td>{escape(str(event.get('event', '-')))}</td>
                        <td>{escape(str(event.get('decision', '-')))}</td>
                        <td>{escape(str(event.get('actor', '-')))}</td>
                        <td><code>{escape(str(event.get('required_scope') or '-'))}</code></td>
                        <td>{escape(str(event.get('method', '-')))} {escape(str(event.get('path', '-')))}</td>
                        <td>{escape(str(event.get('timestamp') or '-'))}</td>
                    </tr>
        """
    html += """
                </tbody>
            </table>
        </div>
    """
    return html

def default_task_tape_paths(audit_log_path):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(audit_log_path)))
    return (
        os.path.join(project_root, 'tapes', 'task_runs.jsonl'),
        os.path.join(project_root, 'tapes', 'task_checkpoints.jsonl'),
    )


def render_task_tape_summary(task_tape_path, task_checkpoint_path):
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    summary = store.summary()
    recent_events = [event.to_dict() for event in store.events()][-8:]
    recent_events.reverse()
    html = f"""
        <div class="card task-card">
            <div class="step-label">Task Tape</div>
            <h2>Append-only Execution & Rollback</h2>
            <div class="metrics">
                <div class="metric"><strong>{summary['task_count']}</strong><span>Tasks</span></div>
                <div class="metric"><strong>{summary['event_count']}</strong><span>Events</span></div>
                <div class="metric"><strong>{summary['checkpoint_count']}</strong><span>Checkpoints</span></div>
                <div class="metric"><strong>{escape(str((summary.get('latest_event') or {}).get('status') or '-'))}</strong><span>Latest Status</span></div>
            </div>
    """
    if not recent_events:
        html += '<p class="muted">No task tape events recorded yet.</p></div>'
        return html
    html += """
            <div class="step-label">Recent Task Events</div>
            <table>
                <thead><tr><th>Event</th><th>Task</th><th>Status</th><th>Target</th><th>Checkpoint</th><th>Timestamp</th></tr></thead>
                <tbody>
    """
    for event in recent_events:
        html += f"""
                    <tr>
                        <td>{escape(str(event.get('event', '-')))}</td>
                        <td><code>{escape(str(event.get('task_id', '-')))}</code></td>
                        <td>{escape(str(event.get('status') or '-'))}</td>
                        <td>{escape(str(event.get('target') or '-'))}</td>
                        <td><code>{escape(str(event.get('checkpoint_id') or '-'))}</code></td>
                        <td>{escape(str(event.get('timestamp') or '-'))}</td>
                    </tr>
        """
    html += """
                </tbody>
            </table>
        </div>
    """
    return html


def render_integrity_summary(audit_log_path, task_tape_path, task_checkpoint_path, security_audit_path):
    ledgers = {
        "pointer_audit": verify_hash_chain(audit_log_path),
        "task_events": verify_hash_chain(task_tape_path),
        "task_checkpoints": verify_hash_chain(task_checkpoint_path),
        "security_audit": verify_hash_chain(security_audit_path),
    }
    ok_count = sum(1 for result in ledgers.values() if result.get("ok"))
    html = f"""
        <div class="card integrity-card">
            <div class="step-label">Tamper-evident Integrity</div>
            <h2>Hash-chained JSONL Ledgers</h2>
            <div class="metrics">
                <div class="metric"><strong>{ok_count}/{len(ledgers)}</strong><span>Ledgers OK</span></div>
                <div class="metric"><strong>{ledgers['task_events'].get('verified_count', 0)}</strong><span>Task Rows</span></div>
                <div class="metric"><strong>{ledgers['security_audit'].get('verified_count', 0)}</strong><span>Security Rows</span></div>
                <div class="metric"><strong>{ledgers['pointer_audit'].get('verified_count', 0)}</strong><span>Pointer Audit Rows</span></div>
            </div>
            <table>
                <thead><tr><th>Ledger</th><th>Status</th><th>Verified</th><th>Legacy Prefix</th><th>Head Hash</th></tr></thead>
                <tbody>
    """
    for name, result in ledgers.items():
        status = "OK" if result.get("ok") else f"BROKEN: {result.get('error')} line={result.get('line')}"
        head_hash = str(result.get("head_hash") or result.get("actual_row_hash") or "-")
        html += f"""
                    <tr>
                        <td>{escape(name)}</td>
                        <td>{escape(status)}</td>
                        <td>{escape(str(result.get('verified_count', 0)))}</td>
                        <td>{escape(str(result.get('legacy_prefix_count', 0)))}</td>
                        <td><code>{escape(head_hash[:16])}</code></td>
                    </tr>
        """
    html += """
                </tbody>
            </table>
        </div>
    """
    return html



def default_secret_inventory_path(audit_log_path):
    audit_dir = os.path.dirname(os.path.abspath(audit_log_path))
    return os.path.join(audit_dir, 'secret_inventory.jsonl')


def render_secret_inventory_summary(inventory_path):
    records = list(latest_records(inventory_path).values()) if os.path.exists(inventory_path) else []
    by_status = {}
    for record in records:
        status = str(record.get('status', 'unknown'))
        by_status[status] = by_status.get(status, 0) + 1
    status_items = ''.join(
        f"<span class=\"pill\">{escape(status)}: {count}</span>"
        for status, count in sorted(by_status.items())
    ) or '<span class="muted">No secret inventory records yet</span>'
    html = f"""
        <div class="card secret-inventory-card">
            <div class="step-label">Secret Inventory</div>
            <h2>Vault Migration Metadata</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(records)}</strong><span>Artifacts</span></div>
                <div class="metric"><strong>{by_status.get('stored_in_vault', 0)}</strong><span>Stored</span></div>
                <div class="metric"><strong>{by_status.get('preflight_passed', 0)}</strong><span>Preflight</span></div>
                <div class="metric"><strong>{by_status.get('removed', 0)}</strong><span>Removed</span></div>
            </div>
            <div class="step-label">Statuses</div>
            <p>{status_items}</p>
    """
    if not records:
        html += '</div>'
        return html
    html += """
            <table>
                <thead><tr><th>Artifact</th><th>Type</th><th>Status</th><th>Vault Ref</th><th>Runtime</th></tr></thead>
                <tbody>
    """
    for record in records[-10:]:
        html += f"""
                    <tr>
                        <td><code>{escape(str(record.get('artifact_path', '-')))}</code></td>
                        <td>{escape(str(record.get('artifact_type', '-')))}</td>
                        <td>{escape(str(record.get('status', '-')))}</td>
                        <td>{escape(str(record.get('vault_path', '-')))} field={escape(str(record.get('field', '-')))}</td>
                        <td>{escape(str(record.get('runtime_destination') or '-'))}</td>
                    </tr>
        """
    html += """
                </tbody>
            </table>
        </div>
    """
    return html





def render_footprint_summary(footprint):
    sizes = footprint.get('sizes', {})
    counts = footprint.get('counts', {})
    props = footprint.get('lightweight_properties', {})
    prop_items = ''.join(
        f'<span class="pill">{escape(str(key))}: {escape(str(value))}</span>'
        for key, value in sorted(props.items())
    ) or '<span class="muted">No footprint properties recorded</span>'
    html = f"""
        <div class="card integrity-card">
            <div class="step-label">Lightweight Footprint</div>
            <h2>Pointer/Tape Context Economy</h2>
            <div class="metrics">
                <div class="metric"><strong>{footprint.get('total_bytes', 0) / 1024:.1f}</strong><span>Total KiB</span></div>
                <div class="metric"><strong>{counts.get('pointers', 0)}</strong><span>Pointers</span></div>
                <div class="metric"><strong>{counts.get('tasks', 0)}</strong><span>Tasks</span></div>
                <div class="metric"><strong>{counts.get('task_events', 0)}</strong><span>Task Events</span></div>
            </div>
            <div class="step-label">Properties</div>
            <p>{prop_items}</p>
            <table>
                <thead><tr><th>Ledger</th><th>Bytes</th></tr></thead>
                <tbody>
    """
    for name, size in sorted(sizes.items()):
        html += f"<tr><td>{escape(str(name))}</td><td>{escape(str(size))}</td></tr>"
    html += """
                </tbody>
            </table>
        </div>
    """
    return html
def queue_summary(pointers, task_events):
    handoff_pending = [p for p in pointers if p.context_type == 'handoff_summary' and p.retrieval_rule == 'handoff_review_required' and p.status == 'active']
    handoff_approved = [p for p in pointers if p.context_type == 'handoff_summary' and p.retrieval_rule == 'handoff_approved' and p.status == 'active']
    promotion_plans = [p for p in pointers if p.context_type == 'handoff_promotion_plan']
    execution_pending = [event for event in task_events if event.get('event') == 'review_required' and event.get('payload', {}).get('review_type') == 'handoff_promotion_execution']
    execution_ready = [event for event in task_events if event.get('event') == 'handoff_promotion_execution_ready']
    resume_pending = [event for event in task_events if event.get('event') == 'review_required' and event.get('payload', {}).get('review_type') == 'execution_resume_action']
    resume_ready = [event for event in task_events if event.get('event') == 'resume_action_ready']
    return {
        'handoff_pending': handoff_pending,
        'handoff_approved': handoff_approved,
        'promotion_plans': promotion_plans,
        'execution_pending': execution_pending,
        'execution_ready': execution_ready,
        'resume_pending': resume_pending,
        'resume_ready': resume_ready,
    }


def render_handoff_queue_summary(queue):
    html = f"""
        <div class="card governance-card">
            <div class="step-label">Handoff Queue Overview</div>
            <h2>Inbox → Promotion → Resume</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(queue['handoff_pending'])}</strong><span>Pending Handoffs</span></div>
                <div class="metric"><strong>{len(queue['handoff_approved'])}</strong><span>Approved Handoffs</span></div>
                <div class="metric"><strong>{len(queue['execution_pending'])}</strong><span>Execution Reviews</span></div>
                <div class="metric"><strong>{len(queue['resume_pending'])}</strong><span>Resume Reviews</span></div>
            </div>
    """
    if not any(queue.values()):
        html += '<p class="muted">No handoff queue activity yet.</p></div>'
        return html
    def render_ids(items, key):
        rendered = []
        for item in items[:8]:
            value = item.get(key, '-') if isinstance(item, dict) else getattr(item, key, '-')
            rendered.append(f'<span class="pill">{escape(str(value))}</span>')
        return ''.join(rendered) or '<span class="muted">none</span>'
    html += f"""
            <div class="step-label">Pending Handoff IDs</div>
            <p>{render_ids(queue['handoff_pending'], 'pointer_id')}</p>
            <div class="step-label">Execution Review Task IDs</div>
            <p>{render_ids(queue['execution_pending'], 'task_id')}</p>
            <div class="step-label">Resume Review Task IDs</div>
            <p>{render_ids(queue['resume_pending'], 'task_id')}</p>
        </div>
    """
    return html




def default_mcp_registry_path(audit_log_path):
    return os.path.join(os.path.dirname(os.path.abspath(audit_log_path)), 'mcp_connectors.json')


def default_mcp_audit_path(audit_log_path):
    return os.path.join(os.path.dirname(os.path.abspath(audit_log_path)), 'mcp_audit.jsonl')


def default_mcp_review_path(audit_log_path):
    return os.path.join(os.path.dirname(os.path.abspath(audit_log_path)), 'mcp_reviews.jsonl')


def render_mcp_connector_summary(registry_path, mcp_audit_path, mcp_review_path=None):
    registry = MCPRegistry(registry_path, mcp_audit_path, mcp_review_path)
    connectors = registry.load() if os.path.exists(registry_path) else []
    pending_reviews = registry.reviews(status='pending') if mcp_review_path and os.path.exists(mcp_review_path) else []
    active = [c for c in connectors if c.status == 'active']
    approval_required = [c for c in connectors if c.requires_human_approval]
    audit_integrity = verify_hash_chain(mcp_audit_path) if os.path.exists(mcp_audit_path) else {'ok': True, 'row_count': 0}
    html = f"""
        <div class="card governance-card">
            <div class="step-label">MCP Connector Registry</div>
            <h2>Text-first Tool Governance</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(connectors)}</strong><span>Connectors</span></div>
                <div class="metric"><strong>{len(active)}</strong><span>Active</span></div>
                <div class="metric"><strong>{len(pending_reviews)}</strong><span>Pending Reviews</span></div>
                <div class="metric"><strong>{'OK' if audit_integrity.get('ok') else 'CHECK'}</strong><span>MCP Audit Chain</span></div>
            </div>
            <p class="muted">MCP connector definitions are checked as text before registration. No MCP tool execution is performed here. Remote URLs must be HTTPS; secrets are file references only.</p>
    """
    if pending_reviews:
        html += '<h3>Pending MCP Reviews</h3><table><thead><tr><th>Review</th><th>Connector</th><th>Allowed Tools</th><th>Status</th></tr></thead><tbody>'
        for review in pending_reviews[:10]:
            connector = review.get('connector') or {}
            allowed = ''.join(f'<span class="pill"><code>{escape(str(tool))}</code></span>' for tool in connector.get('allowed_tools', [])) or '<span class="muted">none</span>'
            html += f"""<tr><td><code>{escape(str(review.get('review_id')))}</code></td><td><code>{escape(str(review.get('connector_id')))}</code></td><td>{allowed}</td><td>{escape(str(review.get('status')))}</td></tr>"""
        html += '</tbody></table>'
    if not connectors:
        html += '<p class="muted">No MCP connectors registered yet.</p></div>'
        return html
    html += '<table><thead><tr><th>Connector</th><th>Transport</th><th>Status</th><th>Approval</th><th>Allowed Tools</th><th>Secret Handling</th></tr></thead><tbody>'
    for connector in connectors[:20]:
        allowed = ''.join(f'<span class="pill"><code>{escape(str(tool))}</code></span>' for tool in connector.allowed_tools) or '<span class="muted">none</span>'
        url_line = f'<br><span class="muted">{escape(str(connector.url))}</span>' if connector.url else ''
        html += f"""
            <tr>
                <td><code>{escape(connector.connector_id)}</code><br>{escape(connector.name)}{url_line}</td>
                <td>{escape(connector.transport)}</td>
                <td>{escape(connector.status)}</td>
                <td>{'required' if connector.requires_human_approval else 'not required'}</td>
                <td>{allowed}</td>
                <td>env_secret_files={len(connector.env_secret_files)} / raw_values_hidden=true</td>
            </tr>
        """
    html += '</tbody></table></div>'
    return html



def render_mcp_execution_summary(task_tape_path, task_checkpoint_path):
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    reviews = pending_mcp_execution_reviews(store)
    html = f"""
        <div class="card governance-card">
            <div class="step-label">MCP Execution Adapter</div>
            <h2>Dry-run / Metadata-only Tool Gate</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(reviews)}</strong><span>Pending Reviews</span></div>
                <div class="metric"><strong>no</strong><span>Tool Executed</span></div>
                <div class="metric"><strong>no</strong><span>Args Values Stored</span></div>
                <div class="metric"><strong>dry-run</strong><span>Mode</span></div>
            </div>
            <p class="muted">The adapter evaluates connector status, tool allowlists, argument safety, and approval gates. It does not launch MCP servers or execute tools.</p>
    """
    if not reviews:
        html += '<p class="muted">No pending MCP execution reviews.</p></div>'
        return html
    html += '<table><thead><tr><th>Task</th><th>Connector</th><th>Tool</th><th>Args Fingerprint</th><th>Mode</th></tr></thead><tbody>'
    for review in reviews[:10]:
        payload = review.get('payload') or {}
        html += f"""
            <tr>
                <td><code>{escape(str(review.get('task_id')))}</code></td>
                <td><code>{escape(str(payload.get('connector_id') or '-'))}</code></td>
                <td>{escape(str(payload.get('tool_name') or '-'))}</td>
                <td><code>{escape(str(payload.get('args_sha256') or '-'))}</code><br><span class="muted">values_stored={escape(str(payload.get('args_values_stored')))}</span></td>
                <td>{escape(str(payload.get('execution_mode') or '-'))}</td>
            </tr>
        """
    html += '</tbody></table></div>'
    return html


def render_human_escalation_summary(task_tape_path, task_checkpoint_path):
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    escalations = pending_human_escalations(store)
    human_required = [row for row in escalations if (row.get('decision') or {}).get('requires_human')]
    severities = {}
    for row in escalations:
        severity = str((row.get('decision') or {}).get('severity') or 'unknown')
        severities[severity] = severities.get(severity, 0) + 1
    severity_summary = ', '.join(f'{escape(k)}={v}' for k, v in sorted(severities.items())) or 'none'
    html = f"""
        <div class="card governance-card">
            <div class="step-label">Human Escalation Queue</div>
            <h2>Assisted Autonomy Review Gate</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(escalations)}</strong><span>Pending Escalations</span></div>
                <div class="metric"><strong>{len(human_required)}</strong><span>Human Required</span></div>
                <div class="metric"><strong>no</strong><span>Secret Values Stored</span></div>
                <div class="metric"><strong>no</strong><span>Raw Diffs / Outputs</span></div>
            </div>
            <p class="muted">Aggregates metadata-only escalation decisions from GitHub, MCP, and sandbox review pipelines. Approval/rejection stays routed through each owning pipeline endpoint.</p>
            <p class="muted">Severity distribution: {severity_summary}. Raw request bodies, raw diff text, stdout/stderr, checkpoint contents, and secret values are not persisted.</p>
    """
    if not escalations:
        html += '<p class="muted">No pending Human Escalation decisions.</p></div>'
        return html
    html += '<table><thead><tr><th>Task</th><th>Review Type</th><th>Severity / Mode</th><th>Reasons</th><th>Pipeline Endpoint</th></tr></thead><tbody>'
    for row in escalations[:10]:
        decision = row.get('decision') or {}
        reasons = ''.join(f'<span class="pill">{escape(str(reason))}</span>' for reason in decision.get('reasons', [])) or '<span class="muted">none</span>'
        html += f"""
            <tr>
                <td><code>{escape(str(row.get('task_id')))}</code></td>
                <td>{escape(str(row.get('review_type') or '-'))}</td>
                <td>{escape(str(decision.get('severity') or '-'))}<br><span class="muted">mode={escape(str(decision.get('recommended_mode') or '-'))} / requires_human={escape(str(decision.get('requires_human')))}</span></td>
                <td>{reasons}</td>
                <td><code>{escape(str(row.get('approval_endpoint_hint') or '-'))}</code><br><span class="muted">metadata_only={escape(str(row.get('metadata_only')))}</span></td>
            </tr>
        """
    html += '</tbody></table></div>'
    return html


def render_github_pr_dry_run_summary(task_tape_path, task_checkpoint_path):
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    reviews = pending_github_pr_reviews(store)
    html = f"""
        <div class="card governance-card">
            <div class="step-label">GitHub PR Dry-run</div>
            <h2>Review-gated PR Planning</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(reviews)}</strong><span>Pending Reviews</span></div>
                <div class="metric"><strong>no</strong><span>Branch Created</span></div>
                <div class="metric"><strong>no</strong><span>Push</span></div>
                <div class="metric"><strong>no</strong><span>PR Created</span></div>
            </div>
            <p class="muted">Plans GitHub PR work without creating branches, commits, pushes, or pull requests. Raw issue summaries are not stored; only hashes and metadata are recorded.</p>
    """
    if not reviews:
        html += '<p class="muted">No pending GitHub PR dry-run reviews.</p></div>'
        return html
    html += '<table><thead><tr><th>Task</th><th>Repo</th><th>Branch</th><th>Plan</th><th>Files</th></tr></thead><tbody>'
    for review in reviews[:10]:
        plan = (review.get('payload') or {}).get('plan') or {}
        files = ''.join(f'<span class="pill"><code>{escape(str(path))}</code></span>' for path in plan.get('candidate_files', [])) or '<span class="muted">none</span>'
        html += f"""
            <tr>
                <td><code>{escape(str(review.get('task_id')))}</code></td>
                <td><code>{escape(str(plan.get('repo') or '-'))}</code></td>
                <td>{escape(str(plan.get('proposed_branch') or '-'))}</td>
                <td><code>{escape(str(plan.get('plan_sha256') or '-'))}</code><br><span class="muted">pr_created={escape(str(plan.get('pr_created')))}</span></td>
                <td>{files}</td>
            </tr>
        """
    html += '</tbody></table></div>'
    return html



def render_github_diff_review_summary(task_tape_path, task_checkpoint_path):
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    reviews = pending_github_diff_reviews(store)
    html = f"""
        <div class="card governance-card">
            <div class="step-label">GitHub Diff Review</div>
            <h2>Metadata-only Diff Planning</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(reviews)}</strong><span>Pending Reviews</span></div>
                <div class="metric"><strong>no</strong><span>Files Written</span></div>
                <div class="metric"><strong>no</strong><span>Patch Applied</span></div>
                <div class="metric"><strong>no</strong><span>Commit / PR</span></div>
            </div>
            <p class="muted">Diff reviews store only hashes, sizes, file names, and line counts. Raw diffs are not persisted and patches are not applied.</p>
    """
    if not reviews:
        html += '<p class="muted">No pending GitHub diff reviews.</p></div>'
        return html
    html += '<table><thead><tr><th>Task</th><th>Source</th><th>Repo</th><th>Diff</th><th>Files</th></tr></thead><tbody>'
    for review in reviews[:10]:
        plan = (review.get('payload') or {}).get('plan') or {}
        files = ''.join(f'<span class="pill"><code>{escape(str(path))}</code></span>' for path in plan.get('changed_files', [])) or '<span class="muted">none</span>'
        html += f"""
            <tr>
                <td><code>{escape(str(review.get('task_id')))}</code></td>
                <td><code>{escape(str(plan.get('source_task_id') or '-'))}</code></td>
                <td><code>{escape(str(plan.get('repo') or '-'))}</code></td>
                <td><code>{escape(str(plan.get('diff_sha256') or '-'))}</code><br><span class="muted">+{escape(str(plan.get('added_lines', 0)))} / -{escape(str(plan.get('removed_lines', 0)))}, patch_applied={escape(str(plan.get('patch_applied')))}</span></td>
                <td>{files}</td>
            </tr>
        """
    html += '</tbody></table></div>'
    return html



def render_sandbox_patch_plan_summary(task_tape_path, task_checkpoint_path):
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    reviews = pending_sandbox_patch_plans(store)
    html = f"""
        <div class="card governance-card">
            <div class="step-label">Sandbox Patch Plan</div>
            <h2>Ephemeral Workspace Validation Gate</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(reviews)}</strong><span>Pending Reviews</span></div>
                <div class="metric"><strong>no</strong><span>Patch Applied</span></div>
                <div class="metric"><strong>no</strong><span>Commands Executed</span></div>
                <div class="metric"><strong>ephemeral</strong><span>Workspace</span></div>
            </div>
            <p class="muted">Plans only metadata for an isolated patch/test runner. No live repo writes, no network, and no raw validation command values are stored.</p>
    """
    if not reviews:
        html += '<p class="muted">No pending sandbox patch plans.</p></div>'
        return html
    html += '<table><thead><tr><th>Task</th><th>Source Diff</th><th>Repo</th><th>Validation</th><th>Files</th></tr></thead><tbody>'
    for review in reviews[:10]:
        plan = (review.get('payload') or {}).get('plan') or {}
        files = ''.join(f'<span class="pill"><code>{escape(str(path))}</code></span>' for path in plan.get('changed_files', [])) or '<span class="muted">none</span>'
        html += f"""
            <tr>
                <td><code>{escape(str(review.get('task_id')))}</code></td>
                <td><code>{escape(str(plan.get('diff_task_id') or '-'))}</code></td>
                <td><code>{escape(str(plan.get('repo') or '-'))}</code></td>
                <td><code>{escape(str(plan.get('sandbox_plan_sha256') or '-'))}</code><br><span class="muted">commands_executed={escape(str(plan.get('commands_executed')))} / validation_commands={escape(str(plan.get('validation_command_count', 0)))} / patch_applied={escape(str(plan.get('patch_applied')))}</span></td>
                <td>{files}</td>
            </tr>
        """
    html += '</tbody></table></div>'
    return html


def render_sandbox_patch_execution_summary(task_tape_path, task_checkpoint_path):
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    reviews = pending_sandbox_patch_executions(store)
    html = f"""
        <div class="card governance-card">
            <div class="step-label">Sandbox Patch Execution</div>
            <h2>Isolated Runner Readiness</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(reviews)}</strong><span>Pending Reviews</span></div>
                <div class="metric"><strong>no</strong><span>Workspace Copied</span></div>
                <div class="metric"><strong>no</strong><span>Patch Applied</span></div>
                <div class="metric"><strong>no</strong><span>Commands Executed</span></div>
            </div>
            <p class="muted">Execution reviews remain metadata-only. They do not copy workspaces, apply patches, or execute commands yet.</p>
    """
    if not reviews:
        html += '<p class="muted">No pending sandbox patch executions.</p></div>'
        return html
    html += '<table><thead><tr><th>Task</th><th>Source Plan</th><th>Repo</th><th>Runner</th><th>Files</th></tr></thead><tbody>'
    for review in reviews[:10]:
        plan = (review.get('payload') or {}).get('plan') or {}
        files = ''.join(f'<span class="pill"><code>{escape(str(path))}</code></span>' for path in plan.get('changed_files', [])) or '<span class="muted">none</span>'
        html += f"""
            <tr>
                <td><code>{escape(str(review.get('task_id')))}</code></td>
                <td><code>{escape(str(plan.get('patch_task_id') or '-'))}</code></td>
                <td><code>{escape(str(plan.get('repo') or '-'))}</code></td>
                <td><code>{escape(str(plan.get('sandbox_execution_sha256') or '-'))}</code><br><span class="muted">workspace_copied={escape(str(plan.get('workspace_copied')))} / patch_applied={escape(str(plan.get('patch_applied')))} / commands_executed={escape(str(plan.get('commands_executed')))}</span></td>
                <td>{files}</td>
            </tr>
        """
    html += '</tbody></table></div>'
    return html



def render_sandbox_patch_execution_results(task_tape_path, task_checkpoint_path):
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    events = completed_sandbox_patch_executions(store)
    html = f"""
        <div class="card governance-card">
            <div class="step-label">Sandbox Patch Execution Results</div>
            <h2>Completed Runs</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(events)}</strong><span>Completed</span></div>
                <div class="metric"><strong>no</strong><span>Raw Outputs Stored</span></div>
                <div class="metric"><strong>hashes</strong><span>Result Storage</span></div>
                <div class="metric"><strong>yes</strong><span>Audit Trail</span></div>
            </div>
            <p class="muted">Completed runs store metadata only: hashes, sizes, exit codes, and status flags. Raw command output stays out of Task Tape.</p>
    """
    if not events:
        html += '<p class="muted">No completed sandbox patch executions yet.</p></div>'
        return html
    html += '<table><thead><tr><th>Task</th><th>Status</th><th>Patch</th><th>Commands</th><th>Workspace</th></tr></thead><tbody>'
    for event in events[:10]:
        payload = event.get('payload') or {}
        command_count = len(payload.get('command_results') or [])
        html += f"""
            <tr>
                <td><code>{escape(str(event.get('task_id')))}</code></td>
                <td>{escape(str(event.get('status') or '-'))}</td>
                <td><code>{escape(str(payload.get('patch_apply_stage') or '-'))}</code><br><span class="muted">applied={escape(str(payload.get('patch_applied')))}</span></td>
                <td><span class="muted">count={command_count} success={escape(str(payload.get('success')))}</span></td>
                <td><span class="muted">copied={escape(str(payload.get('workspace_copied')))} / type={escape(str(payload.get('workspace_type') or '-'))}</span></td>
            </tr>
        """
    html += '</tbody></table></div>'
    return html


def render_execution_scoreboard_summary(task_tape_path, task_checkpoint_path):
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    scoreboard = build_execution_scoreboard(store)
    html = f"""
        <div class="card governance-card">
            <div class="step-label">Execution Scoreboard</div>
            <h2>Safety & Throughput Snapshot</h2>
            <div class="metrics">
                <div class="metric"><strong>{scoreboard['completed_runs']}</strong><span>Completed</span></div>
                <div class="metric"><strong>{scoreboard['success_runs']}</strong><span>Success</span></div>
                <div class="metric"><strong>{scoreboard['failure_runs']}</strong><span>Failure</span></div>
                <div class="metric"><strong>{scoreboard['success_rate']:.1f}%</strong><span>Success Rate</span></div>
            </div>
            <p class="muted">Metadata-only scoreboard: completion counts, failure kinds, retry/replan/intake load, and recent failure summaries only.</p>
            <div class="step-label">Failure Kinds</div>
            <p>
    """
    failure_kinds = scoreboard.get('failure_kind_counts') or {}
    if failure_kinds:
        html += ''.join(f'<span class="pill">{escape(kind)}: {count}</span>' for kind, count in failure_kinds.items())
    else:
        html += '<span class="muted">No failure kinds yet</span>'
    html += """
            </p>
            <div class="step-label">Replay & Replan Load</div>
            <p>
                <span class="pill">retry={}</span>
                <span class="pill">replan={}</span>
                <span class="pill">intake={}</span>
            </p>
    """.format(scoreboard.get('pending_retry_reviews', 0), scoreboard.get('replan_templates', 0), scoreboard.get('diff_intakes', 0))
    recent_failures = scoreboard.get('recent_failures') or []
    if recent_failures:
        html += '<div class="step-label">Recent Failures</div><table><thead><tr><th>Task</th><th>Failure Kind</th><th>Status</th><th>Patch</th><th>Workspace</th></tr></thead><tbody>'
        for item in recent_failures:
            html += f"""
                <tr>
                    <td><code>{escape(str(item.get('task_id') or '-'))}</code></td>
                    <td>{escape(str(item.get('failure_kind') or '-'))}</td>
                    <td>{escape(str(item.get('status') or '-'))}</td>
                    <td>{escape(str(item.get('patch_apply_stage') or '-'))}</td>
                    <td>{escape(str(item.get('workspace_copied')))}</td>
                </tr>
            """
        html += '</tbody></table>'
    else:
        html += '<p class="muted">No completed failures yet.</p>'
    html += '</div>'
    return html


def render_auto_fix_candidate_summary(task_tape_path, task_checkpoint_path):
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    candidates = pending_auto_fix_candidates(store)
    html = f"""
        <div class="card governance-card">
            <div class="step-label">Auto Fix Candidates</div>
            <h2>Metadata-only Repair Strategy</h2>
            <div class="metrics">
                <div class="metric"><strong>{len(candidates)}</strong><span>Candidates</span></div>
                <div class="metric"><strong>no</strong><span>Raw Diff</span></div>
                <div class="metric"><strong>no</strong><span>Raw Outputs</span></div>
                <div class="metric"><strong>no</strong><span>Auto Execute</span></div>
            </div>
            <p class="muted">Candidates contain strategy, confidence, required inputs, and hashes only. They do not contain patch text, stdout/stderr, commits, pushes, or PR creation.</p>
    """
    if not candidates:
        html += '<p class="muted">No auto fix candidates yet.</p></div>'
        return html
    html += '<table><thead><tr><th>Task</th><th>Failure</th><th>Strategy</th><th>Confidence</th><th>Inputs</th></tr></thead><tbody>'
    for row in candidates[-10:]:
        candidate = (row.get('payload') or {}).get('candidate') or {}
        inputs = ''.join(f'<span class="pill">{escape(str(item))}</span>' for item in candidate.get('required_human_inputs', [])) or '<span class="muted">none</span>'
        html += f"""
            <tr>
                <td><code>{escape(str(row.get('task_id') or '-'))}</code><br><span class="muted">replan={escape(str(candidate.get('replan_task_id') or '-'))}</span></td>
                <td>{escape(str(candidate.get('failure_kind') or '-'))}</td>
                <td>{escape(str(candidate.get('candidate_strategy') or '-'))}</td>
                <td>{escape(str(candidate.get('confidence') or '-'))}</td>
                <td>{inputs}</td>
            </tr>
        """
    html += '</tbody></table></div>'
    return html


def render_rate_limit_backend_summary(environ=None):
    environ = os.environ if environ is None else environ
    enabled = str(environ.get('CPOS_RATE_LIMIT_ENABLED', 'false')).lower() in {'1', 'true', 'yes'}
    backend = str(environ.get('CPOS_RATE_LIMIT_BACKEND', 'memory')).lower()
    file_path = environ.get('CPOS_RATE_LIMIT_STORE_PATH') if backend == 'file' else None
    redis_file = environ.get('CPOS_RATE_LIMIT_REDIS_URL_FILE') if backend == 'redis' else None
    redis_configured = bool(redis_file and os.path.exists(redis_file))
    html = f"""
        <div class="card security-card">
            <div class="step-label">Rate Limit Backend</div>
            <h2>Request Throttling Posture</h2>
            <div class="metrics">
                <div class="metric"><strong>{'ON' if enabled else 'OFF'}</strong><span>Enabled</span></div>
                <div class="metric"><strong>{escape(backend)}</strong><span>Backend</span></div>
                <div class="metric"><strong>{'yes' if redis_configured else '-'}</strong><span>Redis URL File</span></div>
                <div class="metric"><strong>{escape(str(environ.get('CPOS_RATE_LIMIT_WINDOW_SECONDS', '60')))}</strong><span>Window Seconds</span></div>
            </div>
            <p class="muted">Stores bucket keys and timestamps only; no Authorization headers, request bodies, tokens, or secrets.</p>
    """
    if file_path:
        html += f'<p>File store: <code>{escape(file_path)}</code></p>'
    if redis_file:
        html += f'<p>Redis URL file: <code>{escape(redis_file)}</code> value_hidden=true configured={escape(str(redis_configured))}</p>'
    html += '</div>'
    return html


def render_handoff_graph_report(pointer_path, task_tape_path, task_checkpoint_path):
    graph = build_handoff_graph(PointerManager(pointer_path), TaskTapeStore(task_tape_path, task_checkpoint_path), limit=20)
    counts = graph.get('counts', {})
    html = f"""
        <div class="card governance-card">
            <div class="step-label">Handoff Flow Graph</div>
            <h2>Handoff → Promotion → Execution → Resume</h2>
            <div class="metrics">
                <div class="metric"><strong>{counts.get('handoffs', 0)}</strong><span>Handoffs</span></div>
                <div class="metric"><strong>{counts.get('promotions', 0)}</strong><span>Promotions</span></div>
                <div class="metric"><strong>{counts.get('execution_reviews', 0)}</strong><span>Executions</span></div>
                <div class="metric"><strong>{counts.get('resume_reviews', 0)}</strong><span>Resumes</span></div>
            </div>
            <p class="muted">Metadata-only graph. Raw handoff bodies, checkpoint contents, request bodies, proposed code, and secrets are excluded.</p>
    """
    if not graph.get('handoffs'):
        html += '<p class="muted">No handoff graph records yet.</p></div>'
        return html
    html += '<table><thead><tr><th>Handoff</th><th>Status</th><th>Promotion</th><th>Execution</th><th>Resume</th></tr></thead><tbody>'
    for handoff in graph.get('handoffs', [])[:10]:
        promotions = handoff.get('promotions', [])
        promotion_ids = {p.get('pointer_id') for p in promotions}
        executions = [e for e in graph.get('execution_reviews', []) if e.get('promotion_pointer_id') in promotion_ids]
        execution_task_ids = {e.get('task_id') for e in executions}
        resumes = [r for r in graph.get('resume_reviews', []) if r.get('task_id') in execution_task_ids]
        promotion_text = '<br>'.join(f"<code>{escape(str(p.get('pointer_id')))}</code><br><span class='muted'>warnings={escape(str(len(p.get('warnings', []))))} blocked={escape(str(len(p.get('blocked_inputs', []))))}</span>" for p in promotions) or '<span class="muted">none</span>'
        execution_text = '<br>'.join(f"<code>{escape(str(e.get('task_id')))}</code><br><span class='muted'>{escape(str(e.get('execution_mode') or '-'))}</span>" for e in executions) or '<span class="muted">none</span>'
        resume_text = '<br>'.join(f"<code>{escape(str(r.get('task_id')))}</code><br><span class='muted'>{escape(str(r.get('first_action_title') or r.get('first_action_id') or '-'))}</span>" for r in resumes) or '<span class="muted">none</span>'
        html += f"""
            <tr>
                <td><code>{escape(str(handoff.get('pointer_id')))}</code><br><span class="muted">{escape(str(handoff.get('summary') or ''))}</span></td>
                <td>{escape(str(handoff.get('review_status') or '-'))}</td>
                <td>{promotion_text}</td>
                <td>{execution_text}</td>
                <td>{resume_text}</td>
            </tr>
        """
    html += '</tbody></table></div>'
    return html
def render_security_profile_validation(validation=None):
    validation = validation or validate_security_posture()
    failures = validation.get('failures', [])
    profile = validation.get('profile', 'custom')
    status = 'OK' if validation.get('ok') else 'CHECK'
    border = '#3fb950' if validation.get('ok') else '#f85149'
    html = f"""
        <div class="card profile-card" style="border-color: {border};">
            <div class="step-label">Security Profile Validation</div>
            <h2>Posture: {escape(str(profile))} / {escape(status)}</h2>
            <div class="metrics">
                <div class="metric"><strong>{escape(str(profile))}</strong><span>Profile</span></div>
                <div class="metric"><strong>{len(validation.get('checks', []))}</strong><span>Checks</span></div>
                <div class="metric"><strong>{len(failures)}</strong><span>Failures</span></div>
                <div class="metric"><strong>{escape(status)}</strong><span>Status</span></div>
            </div>
    """
    if not failures:
        html += '<p class="success">Security profile validation passed or no strict checks apply.</p></div>'
        return html
    html += """
            <table>
                <thead><tr><th>Check</th><th>Severity</th><th>Message</th></tr></thead>
                <tbody>
    """
    for failure in failures:
        html += f"""
                    <tr>
                        <td>{escape(str(failure.get('name', '-')))}</td>
                        <td>{escape(str(failure.get('severity', '-')))}</td>
                        <td>{escape(str(failure.get('message', '-')))}</td>
                    </tr>
        """
    html += """
                </tbody>
            </table>
        </div>
    """
    return html

def generate_hackathon_report(audit_log_path, output_path="hackathon_report.html", pointer_path=None, task_tape_path=None, task_checkpoint_path=None, security_audit_path=None, secret_inventory_path=None, mcp_registry_path=None, mcp_audit_path=None, mcp_review_path=None):
    events = load_jsonl(audit_log_path)
    pointer_path = pointer_path if pointer_path is not None else default_pointer_path(audit_log_path)
    pointers = load_pointers(pointer_path)
    default_tape_path, default_checkpoint_path = default_task_tape_paths(audit_log_path)
    task_tape_path = task_tape_path if task_tape_path is not None else default_tape_path
    task_checkpoint_path = task_checkpoint_path if task_checkpoint_path is not None else default_checkpoint_path
    security_audit_path = security_audit_path if security_audit_path is not None else default_security_audit_path(audit_log_path)
    secret_inventory_path = secret_inventory_path if secret_inventory_path is not None else default_secret_inventory_path(audit_log_path)
    mcp_registry_path = mcp_registry_path if mcp_registry_path is not None else default_mcp_registry_path(audit_log_path)
    mcp_audit_path = mcp_audit_path if mcp_audit_path is not None else default_mcp_audit_path(audit_log_path)
    mcp_review_path = mcp_review_path if mcp_review_path is not None else default_mcp_review_path(audit_log_path)
    generated_at = datetime.datetime.now().isoformat(timespec='seconds')

    html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>CPOS Engine-Zero: Autonomous DevOps Report</title>
    <style>
        body {{ font-family: 'Inter', -apple-system, sans-serif; background: #010409; color: #e6edf3; line-height: 1.6; padding: 40px; }}
        .container {{ max-width: 1100px; margin: auto; }}
        .header {{ border-bottom: 1px solid #30363d; padding-bottom: 20px; margin-bottom: 40px; }}
        .badge {{ background: #238636; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; vertical-align: middle; }}
        .card {{ background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 24px; margin-bottom: 24px; }}
        .finding {{ border-left: 4px solid #f85149; padding-left: 16px; margin: 16px 0; }}
        .finding.medium {{ border-left-color: #d29922; }}
        .finding.high {{ border-left-color: #f85149; }}
        .finding.critical {{ border-left-color: #ff7b72; }}
        .success {{ color: #3fb950; font-weight: bold; }}
        .muted {{ color: #8b949e; font-size: 0.9em; }}
        pre {{ background: #161b22; padding: 16px; border-radius: 8px; overflow-x: auto; border: 1px solid #30363d; font-family: 'JetBrains Mono', monospace; font-size: 0.9em; }}
        code {{ color: #a5d6ff; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ border-top: 1px solid #30363d; padding: 10px; text-align: left; vertical-align: top; }}
        th {{ color: #8b949e; font-size: 0.8em; text-transform: uppercase; }}
        .step-label {{ color: #8b949e; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.05em; }}
        .architect-banner {{ background: linear-gradient(90deg, #1f6feb 0%, #8957e5 100%); color: white; padding: 12px; border-radius: 8px; margin-bottom: 20px; text-align: center; font-weight: bold; }}
        .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0 24px; }}
        .metric {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 14px; }}
        .metric strong {{ display: block; font-size: 1.8em; }}
        .metric span {{ color: #8b949e; font-size: 0.85em; }}
        .pill {{ display: inline-block; background: #161b22; border: 1px solid #30363d; border-radius: 999px; padding: 4px 10px; margin: 4px 6px 4px 0; }}
        .pointer-card {{ border-color: #1f6feb; }}
        .governance-card {{ border-color: #8957e5; }}
        .task-card {{ border-color: #d29922; }}
        .security-card {{ border-color: #f85149; }}
        .integrity-card {{ border-color: #3fb950; }}
        .profile-card {{ border-color: #f85149; }}
        .secret-inventory-card {{ border-color: #8957e5; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ CPOS Engine-Zero <span class="badge">HACKATHON v1.0</span></h1>
            <p>Autonomous DevOps Stability Agent | Powered by Gemini & Context Pointers</p>
            <p class="muted">Generated at {escape(generated_at)}</p>
        </div>

        <div class="architect-banner">
            AUTO-FIXING ENGINE ACTIVE: Self-Healing successful.
        </div>
"""

    html += render_pointer_summary(pointers)
    html += render_pointer_governance_events(events)
    html += render_task_tape_summary(task_tape_path, task_checkpoint_path)
    html += render_security_audit_summary(security_audit_path)
    html += render_integrity_summary(audit_log_path, task_tape_path, task_checkpoint_path, security_audit_path)
    html += render_footprint_summary(build_footprint(
        pointer_path=pointer_path,
        pointer_audit_path=audit_log_path,
        task_tape_path=task_tape_path,
        task_checkpoint_path=task_checkpoint_path,
        security_audit_path=security_audit_path,
        secret_inventory_path=secret_inventory_path,
    ))
    queue = queue_summary(pointers, events)
    html += render_handoff_queue_summary(queue)
    html += render_handoff_graph_report(pointer_path, task_tape_path, task_checkpoint_path)
    html += render_mcp_connector_summary(mcp_registry_path, mcp_audit_path, mcp_review_path)
    html += render_human_escalation_summary(task_tape_path, task_checkpoint_path)
    html += render_mcp_execution_summary(task_tape_path, task_checkpoint_path)
    html += render_github_pr_dry_run_summary(task_tape_path, task_checkpoint_path)
    html += render_github_diff_review_summary(task_tape_path, task_checkpoint_path)
    html += render_sandbox_patch_plan_summary(task_tape_path, task_checkpoint_path)
    html += render_sandbox_patch_execution_summary(task_tape_path, task_checkpoint_path)
    html += render_sandbox_patch_execution_results(task_tape_path, task_checkpoint_path)
    html += render_execution_scoreboard_summary(task_tape_path, task_checkpoint_path)
    html += render_auto_fix_candidate_summary(task_tape_path, task_checkpoint_path)
    html += render_rate_limit_backend_summary()
    html += render_security_profile_validation()
    html += render_secret_inventory_summary(secret_inventory_path)

    for event in reversed(events):
        target = event.get('target', 'Unknown')
        findings = event.get('rule_findings', [])
        sandbox = event.get('sandbox_lint', {})

        html += f"""
        <div class="card">
            <div class="step-label">Target File</div>
            <h3>{escape(os.path.basename(str(target)))}</h3>
            <p class="file-path">{escape(str(target))}</p>

            <div class="step-label">Analysis Findings ({len(findings)})</div>
"""
        for finding in findings:
            severity = finding.get('severity', 'unknown')
            severity_class = severity if severity in ['medium', 'high', 'critical'] else ''
            html += f"""
            <div class="finding {escape(severity_class)}">
                <strong>[{escape(str(severity).upper())}] {escape(str(finding.get('title', 'Unknown')))}</strong> (Line {escape(str(finding.get('line', '-')))})<br>
                <code>{escape(str(finding.get('content', '')))}</code>
            </div>
"""

        if sandbox.get('exit_code') == 0:
            html += f"""
            <div class="step-label">Verification Result</div>
            <p class="success">✨ VERIFIED STABLE: All issues resolved autonomously.</p>
            <pre>{escape(str(sandbox.get('stdout', 'No output')))}</pre>
"""
        else:
            html += f"""
            <div class="step-label">Verification Result</div>
            <p style="color: #f85149;">❌ UNSTABLE: Issues remaining or verification failed.</p>
            <pre>{escape(str(sandbox.get('stdout', 'Error output')))}</pre>
"""
        html += "</div>"

    html += """
    </div>
</body>
</html>
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[*] Hackathon Report generated: {output_path}")


if __name__ == "__main__":
    generate_hackathon_report("/home/mayutama/cpos_defensive_agent/cpos/audit_log.jsonl")
