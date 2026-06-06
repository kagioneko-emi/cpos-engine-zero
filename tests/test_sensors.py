from __future__ import annotations

import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

from cpos.sensors.git_sensor import observe_git_repo, redact_remote_url
from cpos.sensors.time_session_sensor import observe_time_session


def git(repo, *args):
    result = subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result


def init_repo(tmp_path, remote='https://github.com/example/project.git'):
    git(tmp_path, 'init')
    git(tmp_path, 'remote', 'add', 'origin', remote)
    (tmp_path / 'README.md').write_text('# demo\n', encoding='utf-8')
    git(tmp_path, 'add', 'README.md')
    git(tmp_path, '-c', 'user.email=a@example.invalid', '-c', 'user.name=a', 'commit', '-m', 'init')


def assert_sensor_safety(event):
    assert event['schema'] == 'kagioneko.sensor_event.v1'
    assert event['metadata_only'] is True
    assert event['raw_request_stored'] is False
    assert event['raw_diff_stored'] is False
    assert event['raw_outputs_stored'] is False
    assert event['secret_values_stored'] is False
    assert event['execute_automatically'] is False


def test_git_sensor_reports_clean_metadata_only_repo(tmp_path):
    init_repo(tmp_path)

    event = observe_git_repo(tmp_path)

    assert_sensor_safety(event)
    assert event['source'] == 'git'
    assert event['event_type'] == 'git_clean'
    assert event['risk'] == 'low'
    assert event['metadata']['changed_status_count'] == 0
    assert event['metadata']['remote_url_redacted'] == 'https://github.com/example/project.git'
    assert event['metadata']['raw_status_stored'] is False


def test_git_sensor_reports_dirty_without_raw_diff(tmp_path):
    init_repo(tmp_path)
    (tmp_path / 'README.md').write_text('# changed\nsecret-looking text stays in file only\n', encoding='utf-8')

    event = observe_git_repo(tmp_path)

    assert_sensor_safety(event)
    assert event['event_type'] == 'git_dirty'
    assert event['risk'] == 'medium'
    assert event['metadata']['changed_status_count'] == 1
    assert 'secret-looking text' not in str(event)
    assert event['metadata']['raw_diff_stored'] is False


def test_git_sensor_redacts_credential_bearing_remote_url(tmp_path):
    token = 'dummycredential1234567890'
    init_repo(tmp_path, remote=f'https://x-access-token:{token}@github.com/example/project.git')

    event = observe_git_repo(tmp_path)

    assert_sensor_safety(event)
    assert event['event_type'] == 'remote_secret_risk_detected'
    assert event['risk'] == 'high'
    assert event['requires_human_review'] is True
    assert token not in str(event)
    assert '<redacted>' in event['metadata']['remote_url_redacted']
    assert event['metadata']['remote_secret_risk_detected'] is True


def test_redact_remote_url_handles_plain_and_token_urls():
    safe, safe_risk = redact_remote_url('https://github.com/example/project.git')
    risky, risky_flag = redact_remote_url('https://user:dummycredential1234567890@github.com/example/project.git')

    assert safe == 'https://github.com/example/project.git'
    assert safe_risk is False
    assert 'dummycredential1234567890' not in risky
    assert '<redacted>' in risky
    assert risky_flag is True


def test_time_session_sensor_marks_late_night_as_advisory_only(tmp_path):
    late = datetime(2026, 6, 6, 1, 30, tzinfo=ZoneInfo('Asia/Tokyo'))

    event = observe_time_session(tmp_path, now=late)

    assert_sensor_safety(event)
    assert event['source'] == 'time'
    assert event['event_type'] == 'late_night_session'
    assert event['risk'] == 'medium'
    assert event['requires_human_review'] is True
    assert event['metadata']['wellbeing_advisory'] is True
    assert event['metadata']['blocks_ordinary_work'] is False
    assert event['metadata']['extra_confirmation_for_high_stakes'] is True


def test_time_session_sensor_normal_time_is_low_risk(tmp_path):
    daytime = datetime(2026, 6, 6, 14, 0, tzinfo=ZoneInfo('Asia/Tokyo'))

    event = observe_time_session(tmp_path, now=daytime)

    assert_sensor_safety(event)
    assert event['event_type'] == 'normal_session_time'
    assert event['risk'] == 'low'
    assert event['requires_human_review'] is False
