from __future__ import annotations

import cpos.resume_pipeline as resume_pipeline


def _world():
    return {
        'schema': 'kagioneko.world_model_snapshot.v1',
        'repo': {
            'path': '/tmp/private-path-not-emitted-as-value',
            'public_repo': 'kagioneko/cpos-engine-zero',
            'git': {'metadata': {'head': 'abc123'}},
        },
        'session': {'late_night_extra_confirmation': False},
        'release': {'final_v0_1_1_paused': True},
        'goals': {'schema': 'kagioneko.goal_summary.v1', 'confirmation_required_goal_ids': []},
        'overall_risk': 'medium',
        'known_risks': [{'name': 'public_private_boundary', 'risk': 'medium'}],
        'suggested_next_actions': ['continue_world_model_or_goal_manager_work'],
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


def assert_bundle_safety(bundle):
    assert bundle['schema'] == 'kagioneko.resume_pipeline_bundle.v1'
    assert bundle['metadata_only'] is True
    assert bundle['raw_request_stored'] is False
    assert bundle['raw_diff_stored'] is False
    assert bundle['raw_outputs_stored'] is False
    assert bundle['secret_values_stored'] is False
    assert bundle['execute_automatically'] is False
    assert bundle['overall']['would_write'] is False
    assert bundle['overall']['write_enabled'] is False


def test_resume_pipeline_bundle_runs_read_only(monkeypatch, tmp_path):
    monkeypatch.setattr(resume_pipeline, 'build_world_model_snapshot', lambda **kwargs: _world())
    handoff = tmp_path / 'NEXT_HANDOFF.md'
    handoff.write_text('# Start\n## Latest Handoff\nprivate body omitted\n', encoding='utf-8')

    bundle = resume_pipeline.build_resume_pipeline_bundle(goal_store_path='goals/goals.example.json', handoff_path=handoff)

    assert_bundle_safety(bundle)
    assert bundle['reflection']['recommendation'] == 'proceed'
    assert bundle['resume_pointer']['schema'] == 'kagioneko.tape_memory_bridge_pointer.v1'
    assert bundle['resume_pointer_validation']['ok'] is True
    assert bundle['tape_memory_write_plan']['dry_run'] is True
    assert bundle['tape_memory_write_plan']['would_write'] is False
    assert 'private body omitted' not in str(bundle)


def test_resume_pipeline_public_publish_asks_without_writing(monkeypatch):
    monkeypatch.setattr(resume_pipeline, 'build_world_model_snapshot', lambda **kwargs: _world())

    bundle = resume_pipeline.build_resume_pipeline_bundle(
        action_type='publish',
        summary='Publish article',
        target_repo='zenn',
        touches_public_surface=True,
    )

    assert bundle['reflection']['recommendation'] == 'ask'
    assert bundle['reflection']['risk'] == 'high'
    assert bundle['overall']['would_write'] is False
    assert bundle['resume_pointer_validation']['ok'] is True


def test_resume_pipeline_cli_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(resume_pipeline, 'build_world_model_snapshot', lambda **kwargs: _world())
    handoff = tmp_path / 'NEXT_HANDOFF.md'
    handoff.write_text('# Start\n## Latest Handoff\nbody omitted\n', encoding='utf-8')

    resume_pipeline.main(['run', '--goal-store', 'goals/goals.example.json', '--handoff-path', str(handoff), '--json'])

    out = capsys.readouterr().out
    assert 'kagioneko.resume_pipeline_bundle.v1' in out
    assert 'kagioneko.tape_memory_write_plan.v1' in out
    assert 'body omitted' not in out


def test_resume_pipeline_compact_bundle_omits_verbose_handoff_headings(monkeypatch, tmp_path):
    monkeypatch.setattr(resume_pipeline, 'build_world_model_snapshot', lambda **kwargs: _world())
    handoff = tmp_path / 'NEXT_HANDOFF.md'
    handoff.write_text('# Start\n## Latest Handoff\n### Secret-looking body should not appear\n', encoding='utf-8')

    bundle = resume_pipeline.build_resume_pipeline_bundle(goal_store_path='goals/goals.example.json', handoff_path=handoff)
    compact = resume_pipeline.compact_resume_pipeline_bundle(bundle)

    assert compact['schema'] == 'kagioneko.resume_pipeline_compact.v1'
    assert compact['metadata_only'] is True
    assert compact['resume_pointer']['handoff']['latest_heading'] == 'Secret-looking body should not appear'
    assert 'recent_headings' not in compact['resume_pointer']['handoff']
    assert compact['tape_memory_write_plan']['would_write'] is False
    assert compact['tape_memory_write_plan']['write_enabled'] is False


def test_resume_pipeline_cli_compact_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(resume_pipeline, 'build_world_model_snapshot', lambda **kwargs: _world())
    handoff = tmp_path / 'NEXT_HANDOFF.md'
    handoff.write_text('# Start\n## Latest Handoff\nbody omitted\n', encoding='utf-8')

    resume_pipeline.main(['run', '--goal-store', 'goals/goals.example.json', '--handoff-path', str(handoff), '--compact', '--json'])

    out = capsys.readouterr().out
    assert 'kagioneko.resume_pipeline_compact.v1' in out
    assert 'recent_headings' not in out
    assert 'body omitted' not in out
