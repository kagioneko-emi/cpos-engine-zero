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
