from __future__ import annotations

import cpos.reflection_evaluator as reflection


def _world(**overrides):
    base = {
        'schema': 'kagioneko.world_model_snapshot.v1',
        'session': {'late_night_extra_confirmation': False},
        'release': {'final_v0_1_1_paused': True},
        'goals': {
            'schema': 'kagioneko.goal_summary.v1',
            'confirmation_required_goal_ids': ['cpos_v0_1_1_final', 'zenn_cognitive_agent_os_article'],
        },
    }
    base.update(overrides)
    return base


def assert_eval_safety(result):
    assert result['schema'] == 'kagioneko.reflection_evaluation.v1'
    assert result['metadata_only'] is True
    assert result['raw_request_stored'] is False
    assert result['raw_diff_stored'] is False
    assert result['raw_outputs_stored'] is False
    assert result['secret_values_stored'] is False
    assert result['execute_automatically'] is False


def test_reflection_allows_safe_private_doc_action():
    result = reflection.evaluate_proposed_action(
        {
            'action_id': 'private_diagram_doc',
            'action_type': 'doc',
            'summary': 'Add private Mermaid diagrams',
            'target_repo': 'private_lab',
            'requires_execution': False,
        },
        world_model_snapshot=_world(),
    )

    assert_eval_safety(result)
    assert result['recommendation'] == 'proceed'
    assert result['risk'] == 'low'
    assert result['blocking_issues'] == []


def test_reflection_asks_for_publish_confirmation():
    result = reflection.evaluate_proposed_action(
        {
            'action_id': 'zenn_cognitive_agent_os_article',
            'action_type': 'publish',
            'summary': 'Set Zenn article published true',
            'target_repo': 'zenn',
            'touches_public_surface': True,
        },
        world_model_snapshot=_world(),
    )

    assert_eval_safety(result)
    assert result['recommendation'] == 'ask'
    assert result['risk'] == 'high'
    assert result['required_confirmations']


def test_reflection_blocks_raw_db_rows_and_android_phone_data():
    db = reflection.evaluate_proposed_action(
        {'action_id': 'read_db_rows', 'action_type': 'sensor', 'summary': 'Read conversation DB rows', 'reads_raw_db_rows': True},
        world_model_snapshot=_world(),
    )
    phone = reflection.evaluate_proposed_action(
        {'action_id': 'read_phone', 'action_type': 'sensor', 'summary': 'Read phone data', 'reads_android_raw_data': True, 'reads_phone_data': True},
        world_model_snapshot=_world(),
    )

    assert db['recommendation'] == 'block'
    assert 'raw DB row access' in db['blocking_issues'][0]
    assert phone['recommendation'] == 'block'
    assert 'raw Android/phone data' in phone['blocking_issues'][0]


def test_reflection_blocks_authorized_keys_and_agi_overclaim():
    keys = reflection.evaluate_proposed_action(
        {'action_id': 'keys', 'action_type': 'authorized_keys', 'summary': 'Change authorized_keys'},
        world_model_snapshot=_world(),
    )
    agi = reflection.evaluate_proposed_action(
        {'action_id': 'agi_claim', 'action_type': 'publish', 'summary': 'AGI completed announcement', 'touches_public_surface': True},
        world_model_snapshot=_world(),
    )

    assert keys['recommendation'] == 'block'
    assert keys['risk'] == 'critical'
    assert agi['recommendation'] == 'block'
    assert 'completed AGI' in agi['blocking_issues'][0]


def test_reflection_late_night_high_stakes_needs_extra_confirmation():
    result = reflection.evaluate_proposed_action(
        {'action_id': 'push_late', 'action_type': 'push', 'summary': 'Push changes'},
        world_model_snapshot=_world(session={'late_night_extra_confirmation': True}, release={'final_v0_1_1_paused': False}),
    )

    assert result['recommendation'] == 'ask'
    assert 'late-night high-stakes extra confirmation' in result['required_confirmations']


def test_reflection_blocks_invalid_goal_store_validation():
    result = reflection.evaluate_proposed_action(
        {
            'action_id': 'goal_backed_action',
            'action_type': 'doc',
            'summary': 'Use persisted goal store to plan next work',
            'requires_execution': False,
        },
        world_model_snapshot=_world(goal_store_validation={
            'schema': 'kagioneko.goal_store_validation.v1',
            'ok': False,
            'goal_count': 1,
            'error_count': 1,
            'error_codes': ['write_enabled_forbidden'],
            'metadata_only': True,
            'raw_request_stored': False,
            'raw_diff_stored': False,
            'raw_outputs_stored': False,
            'secret_values_stored': False,
            'execute_automatically': False,
        }),
    )

    assert_eval_safety(result)
    assert result['recommendation'] == 'block'
    assert result['risk'] == 'critical'
    assert result['goal_store_validation_used'] is True
    assert result['goal_store_error_codes'] == ['write_enabled_forbidden']
    assert 'codes=write_enabled_forbidden' in result['blocking_issues'][0]


def test_reflection_goal_store_duplicate_ids_are_medium_but_blocked():
    result = reflection.evaluate_proposed_action(
        {'action_id': 'goal_backed_action', 'action_type': 'doc', 'summary': 'Plan from persisted goals', 'requires_execution': False},
        world_model_snapshot=_world(goal_store_validation={
            'schema': 'kagioneko.goal_store_validation.v1',
            'ok': False,
            'goal_count': 2,
            'error_count': 1,
            'error_codes': ['duplicate_goal_id'],
            'metadata_only': True,
            'raw_request_stored': False,
            'raw_diff_stored': False,
            'raw_outputs_stored': False,
            'secret_values_stored': False,
            'execute_automatically': False,
        }),
    )

    assert result['recommendation'] == 'block'
    assert result['risk'] == 'medium'
    assert result['goal_store_error_codes'] == ['duplicate_goal_id']


def test_reflection_cli_accepts_goal_store(monkeypatch, capsys):
    seen = {}

    def fake_world_model_snapshot(**kwargs):
        seen.update(kwargs)
        return _world(goal_store_validation={
            'schema': 'kagioneko.goal_store_validation.v1',
            'ok': True,
            'goal_count': 1,
            'error_count': 0,
            'error_codes': [],
            'metadata_only': True,
            'raw_request_stored': False,
            'raw_diff_stored': False,
            'raw_outputs_stored': False,
            'secret_values_stored': False,
            'execute_automatically': False,
        })

    monkeypatch.setattr(reflection, 'build_world_model_snapshot', fake_world_model_snapshot)

    reflection.main(['evaluate', '--action-type', 'doc', '--summary', 'Draft docs', '--goal-store', 'goals/goals.example.json', '--json'])

    out = capsys.readouterr().out
    assert 'kagioneko.reflection_evaluation.v1' in out
    assert seen['goal_store_path'] == 'goals/goals.example.json'


def test_reflection_cli_json(monkeypatch, capsys):
    monkeypatch.setattr(reflection, 'build_world_model_snapshot', lambda: _world())

    reflection.main(['evaluate', '--action-type', 'doc', '--summary', 'Draft docs', '--json'])

    out = capsys.readouterr().out
    assert 'kagioneko.reflection_evaluation.v1' in out
    assert 'proceed' in out
