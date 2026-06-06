from __future__ import annotations

import json

import pytest

import cpos.goal_store as goal_store


def assert_store_safety(result):
    assert result['schema'] == 'kagioneko.goal_store_validation.v1'
    assert result['metadata_only'] is True
    assert result['raw_request_stored'] is False
    assert result['raw_diff_stored'] is False
    assert result['raw_outputs_stored'] is False
    assert result['secret_values_stored'] is False
    assert result['execute_automatically'] is False
    assert result['write_enabled'] is False
    assert result['autonomous_goal_updates'] is False
    assert result['self_preservation_goals'] is False


def valid_goal(goal_id='demo_goal'):
    return {
        'schema': 'kagioneko.goal.v1',
        'goal_id': goal_id,
        'title': 'Demo goal',
        'scope': 'project',
        'state': 'active',
        'priority': 'medium',
        'created_at': '2026-06-07T00:00:00+09:00',
        'updated_at': '2026-06-07T00:00:00+09:00',
        'revisit_after': None,
        'success_criteria': ['tests pass'],
        'safety_constraints': ['no secrets'],
        'source_of_truth': ['README.md'],
        'requires_human_confirmation': False,
        'metadata_only': True,
        'raw_request_stored': False,
        'raw_diff_stored': False,
        'raw_outputs_stored': False,
        'secret_values_stored': False,
        'execute_automatically': False,
    }


def valid_goal_set(goals=None):
    return {
        'schema': 'kagioneko.goal_set.v1',
        'version': 1,
        'updated_at': '2026-06-07T00:00:00+09:00',
        'write_enabled': False,
        'autonomous_goal_updates': False,
        'self_preservation_goals': False,
        'metadata_only': True,
        'goals': goals if goals is not None else [valid_goal()],
    }


def test_goal_store_validates_example_file():
    result = goal_store.validate_file('goals/goals.example.json', include_merged_summary=True)

    assert_store_safety(result)
    assert result['ok'] is True
    assert result['goal_count'] == 1
    assert result['merged_goal_count'] >= 8
    assert result['external_goal_ids'] == ['zenn_cognitive_agent_os_article']


def test_goal_store_rejects_writes_autonomy_and_self_preservation():
    payload = valid_goal_set()
    payload['write_enabled'] = True
    payload['autonomous_goal_updates'] = True
    payload['self_preservation_goals'] = True
    payload['goals'][0]['goal_id'] = 'self_preservation_drive'

    result = goal_store.validate_goal_set(payload)

    assert result['ok'] is False
    codes = {error['code'] for error in result['errors']}
    assert 'write_enabled_forbidden' in codes
    assert 'autonomous_goal_updates_forbidden' in codes
    assert 'self_preservation_goals_forbidden' in codes
    assert 'self_preservation_goal_forbidden' in codes


def test_goal_store_rejects_raw_sensitive_fields_and_patterns():
    goal = valid_goal()
    goal['token'] = 'not-allowed'
    goal['success_criteria'].append('read raw db rows from private log')
    payload = valid_goal_set([goal])

    result = goal_store.validate_goal_set(payload)

    assert result['ok'] is False
    codes = {error['code'] for error in result['errors']}
    assert 'forbidden_goal_key' in codes
    assert 'risky_text_detected' in codes


def test_goal_store_rejects_bad_safety_flags_and_duplicates():
    first = valid_goal('dup')
    second = valid_goal('dup')
    second['execute_automatically'] = True
    second['metadata_only'] = False
    payload = valid_goal_set([first, second])

    result = goal_store.validate_goal_set(payload)

    assert result['ok'] is False
    codes = {error['code'] for error in result['errors']}
    assert 'duplicate_goal_id' in codes
    assert 'safety_flag_must_be_false' in codes
    assert 'metadata_only_required' in codes


def test_goal_store_cli_json_success_and_failure(tmp_path, capsys):
    good = tmp_path / 'goals.json'
    good.write_text(json.dumps(valid_goal_set()), encoding='utf-8')
    goal_store.main(['validate', '--path', str(good), '--json'])
    assert '"ok": true' in capsys.readouterr().out

    bad = tmp_path / 'bad.json'
    payload = valid_goal_set()
    payload['goals'][0]['scope'] = 'forbidden'
    bad.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(SystemExit):
        goal_store.main(['validate', '--path', str(bad), '--json'])
    assert '"ok": false' in capsys.readouterr().out


def test_goal_store_summary_is_metadata_only():
    result = goal_store.build_goal_store_summary('goals/goals.example.json')

    assert result['schema'] == 'kagioneko.goal_store_summary.v1'
    assert result['metadata_only'] is True
    assert result['raw_request_stored'] is False
    assert result['raw_diff_stored'] is False
    assert result['raw_outputs_stored'] is False
    assert result['secret_values_stored'] is False
    assert result['execute_automatically'] is False
    assert result['validation_ok'] is True
    assert result['external_goal_count'] == 1
    assert result['merged_goal_count'] >= result['default_goal_count']
    assert 'zenn_cognitive_agent_os_article' in result['merged_goal_ids']
    assert 'counts_by_state' in result


def test_goal_store_summary_cli_json(tmp_path, capsys):
    good = tmp_path / 'goals.json'
    good.write_text(json.dumps(valid_goal_set()), encoding='utf-8')

    goal_store.main(['summary', '--path', str(good), '--json'])

    out = capsys.readouterr().out
    assert 'kagioneko.goal_store_summary.v1' in out
    assert 'merged_goal_count' in out
