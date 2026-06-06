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


def test_safe_handoff_digest_is_heading_only(tmp_path):
    handoff = tmp_path / 'NEXT_HANDOFF.md'
    handoff.write_text('# First\nsecret body should not appear\n## Latest Handoff\nraw diff should not appear\n', encoding='utf-8')

    digest = resume_pointer.build_safe_handoff_digest(handoff)

    assert digest['schema'] == 'kagioneko.safe_handoff_digest.v1'
    assert digest['metadata_only'] is True
    assert digest['body_included'] is False
    assert digest['full_handoff_stored'] is False
    assert digest['heading_count'] == 2
    assert digest['latest_heading'] == 'Latest Handoff'
    assert 'secret body' not in str(digest)
    assert 'raw diff' not in str(digest)


def test_resume_pointer_can_include_handoff_digest(tmp_path):
    handoff = tmp_path / 'NEXT_HANDOFF.md'
    handoff.write_text('# Start Here\n## Latest Handoff\nbody not included\n', encoding='utf-8')

    pointer = resume_pointer.build_resume_pointer(_world(), include_handoff_digest=True, handoff_path=handoff)

    assert_pointer_safety(pointer)
    assert pointer['handoff']['schema'] == 'kagioneko.safe_handoff_digest.v1'
    assert pointer['handoff']['latest_heading'] == 'Latest Handoff'
    assert 'body not included' not in str(pointer)


def test_resume_pointer_cli_accepts_reflection_json_and_handoff_digest(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(resume_pointer, 'build_world_model_snapshot', lambda **kwargs: _world())
    reflection = tmp_path / 'reflection.json'
    reflection.write_text('{"schema":"kagioneko.reflection_evaluation.v1","recommendation":"ask","risk":"high","goal_store_validation_used":true,"goal_store_error_codes":["duplicate_goal_id"]}', encoding='utf-8')
    handoff = tmp_path / 'NEXT_HANDOFF.md'
    handoff.write_text('# Start\n## Latest Handoff\nprivate body omitted\n', encoding='utf-8')

    resume_pointer.main([
        'build',
        '--goal-store', 'goals/goals.example.json',
        '--reflection-json', str(reflection),
        '--include-handoff-digest',
        '--handoff-path', str(handoff),
        '--json',
    ])

    out = capsys.readouterr().out
    assert '"last_recommendation": "ask"' in out
    assert 'kagioneko.safe_handoff_digest.v1' in out
    assert 'private body omitted' not in out


def test_resume_pointer_validator_accepts_safe_pointer():
    pointer = resume_pointer.build_resume_pointer(_world(), include_handoff_digest=True)

    result = resume_pointer.validate_resume_pointer(pointer)

    assert result['schema'] == 'kagioneko.resume_pointer_validation.v1'
    assert result['ok'] is True
    assert result['error_count'] == 0
    assert result['metadata_only'] is True
    assert result['execute_automatically'] is False


def test_resume_pointer_validator_rejects_write_and_handoff_body():
    pointer = resume_pointer.build_resume_pointer(_world(), include_handoff_digest=True)
    pointer['write_policy']['tape_memory_write_enabled'] = True
    pointer['handoff']['body_included'] = True

    result = resume_pointer.validate_resume_pointer(pointer)

    assert result['ok'] is False
    assert 'write_enabled_forbidden' in result['error_codes']
    assert 'handoff_body_forbidden' in result['error_codes']


def test_tape_memory_write_plan_is_dry_run_only():
    pointer = resume_pointer.build_resume_pointer(_world())

    plan = resume_pointer.build_tape_memory_write_plan(pointer)

    assert plan['schema'] == 'kagioneko.tape_memory_write_plan.v1'
    assert plan['dry_run'] is True
    assert plan['would_write'] is False
    assert plan['write_enabled'] is False
    assert plan['requires_human_confirmation'] is True
    assert plan['secret_scan_required_before_write'] is True
    assert plan['execute_automatically'] is False


def test_resume_pointer_validate_and_write_plan_cli(tmp_path, capsys):
    pointer = resume_pointer.build_resume_pointer(_world())
    path = tmp_path / 'pointer.json'
    import json
    path.write_text(json.dumps(pointer), encoding='utf-8')

    resume_pointer.main(['validate', '--pointer-json', str(path), '--json'])
    assert 'kagioneko.resume_pointer_validation.v1' in capsys.readouterr().out

    resume_pointer.main(['write-plan', '--pointer-json', str(path), '--json'])
    out = capsys.readouterr().out
    assert 'kagioneko.tape_memory_write_plan.v1' in out
    assert '"would_write": false' in out
