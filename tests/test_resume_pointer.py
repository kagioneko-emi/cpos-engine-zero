from __future__ import annotations

import cpos.resume_pointer as resume_pointer


def _world():
    return {
        'schema': 'kagioneko.world_model_snapshot.v1',
        'repo': {
            'path': '/tmp/private-path-not-emitted-as-value',
            'public_repo': 'kagioneko/cpos-engine-zero',
            'git': {'metadata': {'head': 'abc123'}},
        },
        'overall_risk': 'medium',
        'known_risks': [{'name': 'late_night_high_stakes_caution', 'risk': 'medium'}],
        'suggested_next_actions': ['ask_before_push'],
        'goal_store_validation': {
            'schema': 'kagioneko.goal_store_validation.v1',
            'ok': True,
            'goal_count': 1,
            'merged_goal_count': 12,
            'external_goal_ids': ['demo_goal'],
            'error_count': 0,
            'error_codes': [],
        },
    }


def assert_pointer_safety(pointer):
    assert pointer['schema'] == 'kagioneko.tape_memory_bridge_pointer.v1'
    assert pointer['metadata_only'] is True
    assert pointer['raw_request_stored'] is False
    assert pointer['raw_diff_stored'] is False
    assert pointer['raw_outputs_stored'] is False
    assert pointer['secret_values_stored'] is False
    assert pointer['execute_automatically'] is False
    assert pointer['write_policy']['tape_memory_write_enabled'] is False
    assert pointer['write_policy']['requires_human_confirmation_before_write'] is True
    assert pointer['write_policy']['stdout_only'] is True


def test_resume_pointer_is_metadata_only_and_compact():
    pointer = resume_pointer.build_resume_pointer(_world())

    assert_pointer_safety(pointer)
    assert pointer['pointer_type'] == 'cpos_resume'
    assert pointer['repo'] == 'kagioneko/cpos-engine-zero'
    assert pointer['repo_path_present'] is True
    assert pointer['commit'] == 'abc123'
    assert pointer['world_model']['known_risk_names'] == ['late_night_high_stakes_caution']
    assert pointer['goal_store']['validation_ok'] is True
    assert pointer['goal_store']['merged_goal_count'] == 12
    assert pointer['goal_store']['external_goal_ids'] == ['demo_goal']
    assert '/tmp/private-path-not-emitted-as-value' not in str(pointer)


def test_resume_pointer_can_include_reflection_metadata_only():
    pointer = resume_pointer.build_resume_pointer(
        _world(),
        reflection_evaluation={
            'schema': 'kagioneko.reflection_evaluation.v1',
            'recommendation': 'ask',
            'risk': 'high',
            'goal_store_validation_used': True,
            'goal_store_error_codes': ['duplicate_goal_id'],
        },
    )

    assert pointer['reflection']['present'] is True
    assert pointer['reflection']['last_recommendation'] == 'ask'
    assert pointer['reflection']['last_risk'] == 'high'
    assert pointer['reflection']['goal_store_error_codes'] == ['duplicate_goal_id']


def test_resume_pointer_cli_json(monkeypatch, capsys):
    monkeypatch.setattr(resume_pointer, 'build_world_model_snapshot', lambda **kwargs: _world())

    resume_pointer.main(['build', '--goal-store', 'goals/goals.example.json', '--json'])

    out = capsys.readouterr().out
    assert 'kagioneko.tape_memory_bridge_pointer.v1' in out
    assert 'tape_memory_write_enabled' in out
    assert 'abc123' in out
