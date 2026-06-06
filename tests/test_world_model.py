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
        lambda repo=None, **kwargs: {
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


def test_world_model_optional_sensors_are_compact_and_gated(monkeypatch, tmp_path):
    monkeypatch.setattr(world_model, '_repo_root', lambda: tmp_path)
    monkeypatch.setattr(world_model, 'observe_git_repo', lambda repo: _event(metadata={'ahead': 0, 'behind': 0}))
    monkeypatch.setattr(world_model, 'observe_time_session', lambda repo: _event(source='time', event_type='normal_session_time', metadata={'extra_confirmation_for_high_stakes': False}))
    monkeypatch.setattr(world_model, 'run_release_check', lambda: {'ok': True, 'git_status_lines': [], 'tracked_bad_artifacts': [], 'missing_files': [], 'failures': []})
    monkeypatch.setattr(world_model, 'inventory_db_paths', lambda root: _event(source='db_inventory', event_type='db_source_inventory_available', risk='high', metadata={
        'candidate_count': 2,
        'sensitive_skipped_count': 1,
        'reflection_candidate_count': 1,
        'candidates': [{'path': 'should_not_be_in_compact'}],
        'db_files_opened': False,
        'table_names_read': False,
        'row_contents_read': False,
    }))
    monkeypatch.setattr(world_model, 'observe_android_emilia_bridge', lambda refs: _event(source='android_emilia', event_type='android_emilia_bridge_detected', risk='medium', metadata={
        'existing_count': 1,
        'reference_count': 1,
        'references': [{'path': 'should_not_be_in_compact'}],
        'content_read': False,
        'phone_data_read': False,
        'diary_text_read': False,
        'sensor_stream_read': False,
        'upload_triggered': False,
        'phone_control_enabled': False,
    }))

    snapshot = world_model.build_world_model_snapshot(
        tmp_path,
        include_db_inventory=True,
        db_root=tmp_path,
        include_android_emilia=True,
        android_references={'android_app_repo': str(tmp_path / 'android')},
    )

    assert_snapshot_safety(snapshot)
    assert 'db_inventory' in snapshot['optional_sensors']
    assert 'android_emilia' in snapshot['optional_sensors']
    db_meta = snapshot['optional_sensors']['db_inventory']['metadata']
    android_meta = snapshot['optional_sensors']['android_emilia']['metadata']
    assert db_meta['candidate_count'] == 2
    assert db_meta['sensitive_skipped_count'] == 1
    assert 'candidates' not in db_meta
    assert android_meta['existing_count'] == 1
    assert 'references' not in android_meta
    names = {risk['name'] for risk in snapshot['known_risks']}
    assert 'db_sensitive_paths_observed' in names
    assert 'android_emilia_bridge_observed' in names
    assert snapshot['overall_risk'] == 'high'


def test_world_model_optional_sensors_are_absent_by_default(monkeypatch, tmp_path):
    monkeypatch.setattr(world_model, '_repo_root', lambda: tmp_path)
    monkeypatch.setattr(world_model, 'observe_git_repo', lambda repo: _event(metadata={'ahead': 0, 'behind': 0}))
    monkeypatch.setattr(world_model, 'observe_time_session', lambda repo: _event(source='time', event_type='normal_session_time', metadata={'extra_confirmation_for_high_stakes': False}))
    monkeypatch.setattr(world_model, 'run_release_check', lambda: {'ok': True, 'git_status_lines': [], 'tracked_bad_artifacts': [], 'missing_files': [], 'failures': []})

    snapshot = world_model.build_world_model_snapshot(tmp_path)

    assert snapshot['optional_sensors'] == {}


def test_world_model_goal_store_validation_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(world_model, '_repo_root', lambda: tmp_path)
    monkeypatch.setattr(world_model, 'observe_git_repo', lambda repo: _event(metadata={'ahead': 0, 'behind': 0}))
    monkeypatch.setattr(world_model, 'observe_time_session', lambda repo: _event(source='time', event_type='normal_session_time', metadata={'extra_confirmation_for_high_stakes': False}))
    monkeypatch.setattr(world_model, 'run_release_check', lambda: {'ok': True, 'git_status_lines': [], 'tracked_bad_artifacts': [], 'missing_files': [], 'failures': []})
    monkeypatch.setattr(world_model, 'validate_goal_store_file', lambda path, include_merged_summary=True: {
        'schema': 'kagioneko.goal_store_validation.v1',
        'ok': True,
        'goal_count': 1,
        'merged_goal_count': 9,
        'external_goal_ids': ['demo_goal'],
        'errors': [],
        'write_enabled': False,
        'autonomous_goal_updates': False,
        'self_preservation_goals': False,
    })

    snapshot = world_model.build_world_model_snapshot(tmp_path, goal_store_path=tmp_path / 'goals.json')

    assert_snapshot_safety(snapshot)
    validation = snapshot['goal_store_validation']
    assert validation['schema'] == 'kagioneko.goal_store_validation.v1'
    assert validation['ok'] is True
    assert validation['goal_count'] == 1
    assert validation['merged_goal_count'] == 9
    assert validation['external_goal_ids'] == ['demo_goal']
    assert validation['error_count'] == 0
    assert validation['write_enabled'] is False
    assert validation['execute_automatically'] is False


def test_world_model_goal_store_validation_failure_adds_risk(monkeypatch, tmp_path):
    monkeypatch.setattr(world_model, '_repo_root', lambda: tmp_path)
    monkeypatch.setattr(world_model, 'observe_git_repo', lambda repo: _event(metadata={'ahead': 0, 'behind': 0}))
    monkeypatch.setattr(world_model, 'observe_time_session', lambda repo: _event(source='time', event_type='normal_session_time', metadata={'extra_confirmation_for_high_stakes': False}))
    monkeypatch.setattr(world_model, 'run_release_check', lambda: {'ok': True, 'git_status_lines': [], 'tracked_bad_artifacts': [], 'missing_files': [], 'failures': []})
    monkeypatch.setattr(world_model, 'validate_goal_store_file', lambda path, include_merged_summary=True: {
        'schema': 'kagioneko.goal_store_validation.v1',
        'ok': False,
        'goal_count': 1,
        'errors': [{'code': 'write_enabled_forbidden', 'field': 'write_enabled'}],
        'write_enabled': False,
        'autonomous_goal_updates': False,
        'self_preservation_goals': False,
    })

    snapshot = world_model.build_world_model_snapshot(tmp_path, goal_store_path=tmp_path / 'bad.json')

    validation = snapshot['goal_store_validation']
    assert validation['ok'] is False
    assert validation['error_count'] == 1
    assert validation['error_codes'] == ['write_enabled_forbidden']
    names = {risk['name'] for risk in snapshot['known_risks']}
    assert 'goal_store_validation_failed' in names
    assert snapshot['overall_risk'] == 'medium'
