from __future__ import annotations

from pathlib import Path

import cpos.world_model as world_model


def _event(source='git', event_type='git_clean', risk='low', metadata=None):
    return {
        'schema': 'kagioneko.sensor_event.v1',
        'source': source,
        'event_type': event_type,
        'summary': event_type,
        'risk': risk,
        'metadata': metadata or {},
        'metadata_only': True,
        'raw_request_stored': False,
        'raw_diff_stored': False,
        'raw_outputs_stored': False,
        'secret_values_stored': False,
        'execute_automatically': False,
    }


def assert_snapshot_safety(snapshot):
    assert snapshot['schema'] == 'kagioneko.world_model_snapshot.v1'
    assert snapshot['metadata_only'] is True
    assert snapshot['raw_request_stored'] is False
    assert snapshot['raw_diff_stored'] is False
    assert snapshot['raw_outputs_stored'] is False
    assert snapshot['secret_values_stored'] is False
    assert snapshot['execute_automatically'] is False


def test_world_model_snapshot_combines_git_time_release_and_boundary(monkeypatch, tmp_path):
    monkeypatch.setattr(world_model, '_repo_root', lambda: tmp_path)
    monkeypatch.setattr(world_model, 'observe_git_repo', lambda repo: _event(metadata={'ahead': 0, 'behind': 0}))
    monkeypatch.setattr(world_model, 'observe_time_session', lambda repo: _event(source='time', event_type='normal_session_time', metadata={'extra_confirmation_for_high_stakes': False}))
    monkeypatch.setattr(world_model, 'run_release_check', lambda: {'ok': True, 'git_status_lines': [], 'tracked_bad_artifacts': [], 'missing_files': [], 'failures': []})

    snapshot = world_model.build_world_model_snapshot(tmp_path)

    assert_snapshot_safety(snapshot)
    assert snapshot['repo']['path'] == str(tmp_path.resolve())
    assert snapshot['repo']['public_repo'] == 'kagioneko/cpos-engine-zero'
    assert snapshot['public_private_boundary']['private_lab_repo'] == 'kagioneko/cognitive-agent-os-lab'
    assert snapshot['release']['release_check_ok'] is True
    assert snapshot['release']['final_release_requires_explicit_confirmation'] is True
    assert 'release_work_still_requires_explicit_confirmation' in snapshot['suggested_next_actions']
    assert snapshot['overall_risk'] == 'medium'


def test_world_model_snapshot_flags_ahead_and_late_night(monkeypatch, tmp_path):
    monkeypatch.setattr(world_model, '_repo_root', lambda: tmp_path)
    monkeypatch.setattr(world_model, 'observe_git_repo', lambda repo: _event(event_type='git_ahead', risk='medium', metadata={'ahead': 1}))
    monkeypatch.setattr(world_model, 'observe_time_session', lambda repo: _event(source='time', event_type='late_night_session', risk='medium', metadata={'extra_confirmation_for_high_stakes': True}))
    monkeypatch.setattr(world_model, 'run_release_check', lambda: {'ok': False, 'git_status_lines': ['ahead'], 'tracked_bad_artifacts': [], 'missing_files': [], 'failures': [{'name': 'git_status'}]})

    snapshot = world_model.build_world_model_snapshot(tmp_path)

    assert_snapshot_safety(snapshot)
    names = {risk['name'] for risk in snapshot['known_risks']}
    assert 'unpushed_commits' in names
    assert 'late_night_high_stakes_caution' in names
    assert 'release_check_not_ready' in names
    assert snapshot['session']['late_night_extra_confirmation'] is True
    assert 'ask_before_push' in snapshot['suggested_next_actions']
    assert snapshot['overall_risk'] == 'medium'


def test_world_model_cli_json(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        world_model,
        'build_world_model_snapshot',
        lambda repo=None: {
            'schema': 'kagioneko.world_model_snapshot.v1',
            'overall_risk': 'low',
            'repo': {'path': str(Path(repo or '.'))},
            'metadata_only': True,
            'raw_request_stored': False,
            'raw_diff_stored': False,
            'raw_outputs_stored': False,
            'secret_values_stored': False,
            'execute_automatically': False,
        },
    )

    world_model.main(['snapshot', '--repo', str(tmp_path), '--json'])

    out = capsys.readouterr().out
    assert 'kagioneko.world_model_snapshot.v1' in out
    assert str(tmp_path) in out
