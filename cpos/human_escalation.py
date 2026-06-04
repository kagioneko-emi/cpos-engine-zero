from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

DANGEROUS_KEYWORDS = {
    'delete': 'destructive_operation',
    'remove': 'destructive_operation',
    'rm -rf': 'destructive_operation',
    'overwrite': 'destructive_operation',
    'reset --hard': 'destructive_operation',
    'force push': 'destructive_operation',
    'systemctl stop': 'service_stop',
    'authorized_keys': 'forbidden_ssh_key_change',
    'private key': 'secret_material',
    'api key': 'secret_material',
    'token': 'secret_material',
    '.env': 'secret_material',
    'open port': 'network_exposure',
    'port': 'network_exposure',
    'deploy': 'production_change',
    'push': 'git_publish',
}

LOW_CONFIDENCE_THRESHOLD = 0.55
MEDIUM_CONFIDENCE_THRESHOLD = 0.75


@dataclass(frozen=True)
class EscalationDecision:
    requires_human: bool
    severity: str
    reasons: list[str]
    recommended_mode: str
    question: str
    options: list[str]
    safe_autonomy_allowed: bool
    destructive_actions_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            'requires_human': self.requires_human,
            'severity': self.severity,
            'reasons': self.reasons,
            'recommended_mode': self.recommended_mode,
            'question': self.question,
            'options': self.options,
            'safe_autonomy_allowed': self.safe_autonomy_allowed,
            'destructive_actions_performed': self.destructive_actions_performed,
        }


def _keyword_reasons(text: str) -> list[str]:
    lower = text.lower()
    reasons: list[str] = []
    for keyword, reason in DANGEROUS_KEYWORDS.items():
        if keyword in lower and reason not in reasons:
            reasons.append(reason)
    return reasons


def decide_escalation(
    *,
    summary: str,
    confidence: float = 1.0,
    risk: str = 'low',
    touches_secrets: bool = False,
    touches_production: bool = False,
    destructive: bool = False,
    user_confirmation_required: bool = False,
) -> dict[str, Any]:
    reasons = _keyword_reasons(summary)
    normalized_risk = risk.lower().strip()
    if normalized_risk not in {'low', 'medium', 'high', 'critical'}:
        normalized_risk = 'medium'
        reasons.append('unknown_risk_level')

    if touches_secrets and 'secret_material' not in reasons:
        reasons.append('secret_material')
    if touches_production and 'production_change' not in reasons:
        reasons.append('production_change')
    if destructive and 'destructive_operation' not in reasons:
        reasons.append('destructive_operation')
    if user_confirmation_required and 'policy_requires_confirmation' not in reasons:
        reasons.append('policy_requires_confirmation')
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        reasons.append('low_confidence')
    elif confidence < MEDIUM_CONFIDENCE_THRESHOLD:
        reasons.append('medium_confidence')

    hard_gate_reasons = {
        'destructive_operation',
        'forbidden_ssh_key_change',
        'secret_material',
        'network_exposure',
        'production_change',
        'service_stop',
        'git_publish',
        'policy_requires_confirmation',
        'low_confidence',
    }
    requires_human = normalized_risk in {'high', 'critical'} or any(reason in hard_gate_reasons for reason in reasons)

    if normalized_risk == 'critical' or 'forbidden_ssh_key_change' in reasons:
        severity = 'critical'
    elif normalized_risk == 'high' or requires_human:
        severity = 'high'
    elif normalized_risk == 'medium' or 'medium_confidence' in reasons:
        severity = 'medium'
    else:
        severity = 'low'

    if requires_human:
        recommended_mode = 'assisted_autonomy'
        question = 'Human approval or clarification is required before continuing.'
        options = ['approve_with_constraints', 'request_more_context', 'reject_or_replan']
    elif severity == 'medium':
        recommended_mode = 'cautious_autonomy'
        question = 'Proceed autonomously with extra validation and stop on first anomaly.'
        options = ['continue_with_validation', 'ask_if_uncertain']
    else:
        recommended_mode = 'safe_autonomy'
        question = 'Proceed autonomously within the documented safety boundaries.'
        options = ['continue']

    return EscalationDecision(
        requires_human=requires_human,
        severity=severity,
        reasons=reasons,
        recommended_mode=recommended_mode,
        question=question,
        options=options,
        safe_autonomy_allowed=not requires_human,
    ).to_dict()



def review_escalation_decision(
    *,
    review_type: str,
    summary: str,
    confidence: float = 1.0,
    risk: str = 'medium',
    touches_secrets: bool = False,
    touches_production: bool = False,
    destructive: bool = False,
    user_confirmation_required: bool = True,
) -> dict[str, Any]:
    """Return a metadata-only escalation decision suitable for review payloads.

    The decision intentionally stores only policy metadata: reasons, severity,
    mode, options, and booleans. It must not include raw request bodies, raw
    diffs, stdout/stderr, checkpoint contents, or secret values.
    """
    decision = decide_escalation(
        summary=summary,
        confidence=confidence,
        risk=risk,
        touches_secrets=touches_secrets,
        touches_production=touches_production,
        destructive=destructive,
        user_confirmation_required=user_confirmation_required,
    )
    return {
        'schema': 'cpos.human_escalation_decision.v1',
        'review_type': review_type,
        'requires_human': decision['requires_human'],
        'severity': decision['severity'],
        'reasons': decision['reasons'],
        'recommended_mode': decision['recommended_mode'],
        'question': decision['question'],
        'options': decision['options'],
        'safe_autonomy_allowed': decision['safe_autonomy_allowed'],
        'decision_values_stored': True,
        'raw_request_stored': False,
        'raw_diff_stored': False,
        'raw_outputs_stored': False,
        'secret_values_stored': False,
        'destructive_actions_performed': False,
    }


def pending_human_escalations(store: Any) -> list[dict[str, Any]]:
    """Collect pending review events that carry a Human Escalation decision.

    This is a read-only, metadata-only queue over existing Task Tape reviews.
    Existing pipeline-specific approve/reject endpoints remain the source of
    truth; this function does not create a second approval authority.
    """
    terminal_events_by_type = {
        'github_pr_dry_run': {'github_pr_dry_run_approved', 'github_pr_dry_run_rejected'},
        'github_diff_review': {'github_diff_review_approved', 'github_diff_review_rejected'},
        'sandbox_patch_plan': {'sandbox_patch_plan_approved', 'sandbox_patch_plan_rejected'},
        'sandbox_patch_execution': {'sandbox_patch_execution_approved', 'sandbox_patch_execution_rejected'},
        'sandbox_patch_execution_retry': {'sandbox_patch_execution_retry_approved', 'sandbox_patch_execution_retry_rejected'},
        'sandbox_patch_generation': {'sandbox_patch_generation_approved', 'sandbox_patch_generation_rejected'},
        'mcp_tool_execution': {'mcp_execution_approved', 'mcp_execution_rejected', 'mcp_execution_dry_run_ready'},
        'mcp_capability_probe': {'mcp_probe_approved', 'mcp_probe_rejected', 'mcp_probe_dry_run_ready'},
    }
    terminal_task_ids: set[str] = set()
    events = store.events()
    for event in events:
        review_type = (event.payload or {}).get('review_type')
        if event.event in terminal_events_by_type.get(review_type, set()):
            terminal_task_ids.add(event.task_id)

    rows: list[dict[str, Any]] = []
    for event in events:
        payload = event.payload or {}
        decision = payload.get('human_escalation')
        if event.event != 'review_required' or not isinstance(decision, dict):
            continue
        if event.task_id in terminal_task_ids:
            continue
        review_type = payload.get('review_type')
        rows.append({
            'task_id': event.task_id,
            'event_id': event.event_id,
            'timestamp': event.timestamp,
            'target': event.target,
            'status': event.status,
            'review_type': review_type,
            'decision': decision,
            'metadata_only': True,
            'owning_pipeline': _owning_pipeline_hint(review_type),
            'pipeline_stage': _pipeline_stage_hint(review_type),
            'pipeline_node_id': f'{review_type}:{event.task_id}' if review_type else event.task_id,
            'review_endpoint_hint': _review_endpoint_hint(review_type),
            'flow_graph_endpoint_hint': _flow_graph_endpoint_hint(review_type, payload, event.task_id),
            'sandbox_flow_source_execution_task_id': _sandbox_flow_source_execution_task_id(review_type, payload, event.task_id),
            'approval_endpoint_hint': _approval_endpoint_hint(review_type, event.task_id),
            'rejection_endpoint_hint': _rejection_endpoint_hint(review_type, event.task_id),
        })
    return rows



def _owning_pipeline_hint(review_type: str | None) -> str:
    mapping = {
        'github_pr_dry_run': 'github_pr_dry_run',
        'github_diff_review': 'github_diff_review',
        'sandbox_patch_plan': 'sandbox_patch_pipeline',
        'sandbox_patch_execution': 'sandbox_patch_pipeline',
        'sandbox_patch_execution_retry': 'sandbox_failure_recovery',
        'sandbox_patch_generation': 'sandbox_failure_recovery',
        'mcp_tool_execution': 'mcp_execution',
        'mcp_capability_probe': 'mcp_probe',
    }
    return mapping.get(review_type, 'unknown')


def _pipeline_stage_hint(review_type: str | None) -> str:
    mapping = {
        'github_pr_dry_run': 'pr_dry_run_review',
        'github_diff_review': 'diff_review_gate',
        'sandbox_patch_plan': 'sandbox_patch_plan_gate',
        'sandbox_patch_execution': 'sandbox_execution_gate',
        'sandbox_patch_execution_retry': 'sandbox_retry_gate',
        'sandbox_patch_generation': 'patch_generation_gate',
        'mcp_tool_execution': 'mcp_tool_execution_gate',
        'mcp_capability_probe': 'mcp_capability_probe_gate',
    }
    return mapping.get(review_type, 'unknown')


def _sandbox_flow_source_execution_task_id(review_type: str | None, payload: dict[str, Any], task_id: str) -> str | None:
    plan = payload.get('plan') or {}
    if review_type in {'sandbox_patch_execution_retry', 'sandbox_patch_generation', 'sandbox_patch_plan'}:
        return plan.get('source_execution_task_id') or payload.get('source_execution_task_id')
    if review_type == 'sandbox_patch_execution':
        # This review becomes the execution task once approved and run; use it
        # as a future graph filter without executing anything automatically.
        return task_id
    return None


def _flow_graph_endpoint_hint(review_type: str | None, payload: dict[str, Any], task_id: str) -> str | None:
    source_task_id = _sandbox_flow_source_execution_task_id(review_type, payload, task_id)
    if source_task_id:
        return f'/sandbox/flow-graph?source_execution_task_id={source_task_id}'
    return None

def _review_endpoint_hint(review_type: str | None) -> str | None:
    mapping = {
        'github_pr_dry_run': '/github/pr-dry-runs',
        'github_diff_review': '/github/diff-reviews',
        'sandbox_patch_plan': '/sandbox/patch-plans',
        'sandbox_patch_execution': '/sandbox/executions',
        'sandbox_patch_execution_retry': '/sandbox/execution-retries',
        'sandbox_patch_generation': '/sandbox/patch-generations',
        'mcp_tool_execution': '/mcp/executions',
        'mcp_capability_probe': '/mcp/probes',
    }
    return mapping.get(review_type)


def _approval_endpoint_hint(review_type: str | None, task_id: str) -> str | None:
    mapping = {
        'github_pr_dry_run': f'/github/pr-dry-runs/{task_id}/approve',
        'github_diff_review': f'/github/diff-reviews/{task_id}/approve',
        'sandbox_patch_plan': f'/sandbox/patch-plans/{task_id}/approve',
        'sandbox_patch_execution': f'/sandbox/executions/{task_id}/approve',
        'sandbox_patch_execution_retry': f'/sandbox/execution-retries/{task_id}/approve',
        'sandbox_patch_generation': f'/sandbox/patch-generations/{task_id}/approve',
        'mcp_tool_execution': f'/mcp/executions/{task_id}/approve',
        'mcp_capability_probe': f'/mcp/probes/{task_id}/approve',
    }
    return mapping.get(review_type)


def _rejection_endpoint_hint(review_type: str | None, task_id: str) -> str | None:
    approval = _approval_endpoint_hint(review_type, task_id)
    return approval.replace('/approve', '/reject') if approval else None

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Decide whether an agent task should escalate to a human.')
    parser.add_argument('--summary', required=True, help='Short task summary to evaluate.')
    parser.add_argument('--confidence', type=float, default=1.0, help='Agent confidence from 0.0 to 1.0.')
    parser.add_argument('--risk', default='low', help='Risk level: low, medium, high, or critical.')
    parser.add_argument('--touches-secrets', action='store_true')
    parser.add_argument('--touches-production', action='store_true')
    parser.add_argument('--destructive', action='store_true')
    parser.add_argument('--user-confirmation-required', action='store_true')
    parser.add_argument('--json', action='store_true')
    return parser


def print_text(result: dict[str, Any]) -> None:
    status = 'HUMAN_REQUIRED' if result['requires_human'] else 'AUTO_OK'
    print(f'Human escalation decision: {status}')
    print(f"severity: {result['severity']}")
    print(f"mode: {result['recommended_mode']}")
    print(f"reasons: {', '.join(result['reasons']) if result['reasons'] else '-'}")
    print(f"question: {result['question']}")
    print(f"options: {', '.join(result['options'])}")


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    result = decide_escalation(
        summary=args.summary,
        confidence=args.confidence,
        risk=args.risk,
        touches_secrets=args.touches_secrets,
        touches_production=args.touches_production,
        destructive=args.destructive,
        user_confirmation_required=args.user_confirmation_required,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    if result['requires_human']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
