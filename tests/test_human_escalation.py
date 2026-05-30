import pytest

from cpos import human_escalation


def test_low_risk_high_confidence_allows_safe_autonomy():
    result = human_escalation.decide_escalation(summary='update README wording', confidence=0.95, risk='low')

    assert result['requires_human'] is False
    assert result['recommended_mode'] == 'safe_autonomy'
    assert result['safe_autonomy_allowed'] is True
    assert result['destructive_actions_performed'] is False


def test_secret_or_token_work_requires_human():
    result = human_escalation.decide_escalation(summary='rotate API token in .env', confidence=0.9, risk='medium')

    assert result['requires_human'] is True
    assert result['severity'] == 'high'
    assert 'secret_material' in result['reasons']
    assert result['recommended_mode'] == 'assisted_autonomy'


def test_destructive_and_authorized_keys_are_hard_gates():
    result = human_escalation.decide_escalation(summary='remove authorized_keys entry', confidence=0.99, risk='low')

    assert result['requires_human'] is True
    assert result['severity'] == 'critical'
    assert 'forbidden_ssh_key_change' in result['reasons']
    assert 'destructive_operation' in result['reasons']


def test_low_confidence_escalates_even_when_risk_unknown():
    result = human_escalation.decide_escalation(summary='unclear migration', confidence=0.4, risk='weird')

    assert result['requires_human'] is True
    assert 'unknown_risk_level' in result['reasons']
    assert 'low_confidence' in result['reasons']


def test_cli_json_exits_two_when_human_required(capsys):
    with pytest.raises(SystemExit) as exc:
        human_escalation.main(['--summary', 'push to GitHub', '--risk', 'high', '--json'])

    assert exc.value.code == 2
    assert '"requires_human": true' in capsys.readouterr().out
