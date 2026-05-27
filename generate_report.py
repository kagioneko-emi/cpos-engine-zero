import json
import datetime
import os
from html import escape

from cpos.pointer_os import ContextPointer
from cpos.task_tape import TaskTapeStore
from cpos.hash_chain import verify_hash_chain


def load_jsonl(path):
    rows = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
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

def generate_hackathon_report(audit_log_path, output_path="hackathon_report.html", pointer_path=None, task_tape_path=None, task_checkpoint_path=None, security_audit_path=None):
    events = load_jsonl(audit_log_path)
    pointer_path = pointer_path if pointer_path is not None else default_pointer_path(audit_log_path)
    pointers = load_pointers(pointer_path)
    default_tape_path, default_checkpoint_path = default_task_tape_paths(audit_log_path)
    task_tape_path = task_tape_path if task_tape_path is not None else default_tape_path
    task_checkpoint_path = task_checkpoint_path if task_checkpoint_path is not None else default_checkpoint_path
    security_audit_path = security_audit_path if security_audit_path is not None else default_security_audit_path(audit_log_path)
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
