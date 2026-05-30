import pytest

import cpos.prepublish_check as prepublish_check


def test_prepublish_check_combines_publish_guard_release_and_secret_scan(monkeypatch, tmp_path):
    monkeypatch.setattr(prepublish_check, 'run_guard', lambda **kwargs: {'ok': True, 'name': 'guard', 'kwargs': kwargs})
    monkeypatch.setattr(prepublish_check, 'run_release_check', lambda: {'ok': True, 'name': 'release'})
    monkeypatch.setattr(prepublish_check, 'scan_paths', lambda paths, excludes: [])

    result = prepublish_check.run_prepublish_check(repo=tmp_path, expected_remote='https://example.invalid/repo.git')

    assert result['ok'] is True
    assert result['failures'] == []
    assert result['destructive_actions_performed'] is False
    assert result['checks']['github_publish_guard']['kwargs']['expected_remote'] == 'https://example.invalid/repo.git'
    assert result['checks']['release_check']['name'] == 'release'
    assert result['checks']['secret_scan']['count'] == 0


def test_prepublish_check_reports_each_failed_subcheck(monkeypatch, tmp_path):
    monkeypatch.setattr(prepublish_check, 'run_guard', lambda **kwargs: {'ok': False, 'failures': [{'error': 'unexpected_remote'}]})
    monkeypatch.setattr(prepublish_check, 'run_release_check', lambda: {'ok': False, 'failures': [{'error': 'working_tree_not_clean'}]})
    monkeypatch.setattr(prepublish_check, 'scan_paths', lambda paths, excludes: [{'path': 'x', 'line': 1, 'pattern': 'private_key_pem'}])

    result = prepublish_check.run_prepublish_check(repo=tmp_path)

    assert result['ok'] is False
    assert result['failures'] == ['github_publish_guard', 'release_check', 'secret_scan']
    assert result['checks']['secret_scan']['ok'] is False


def test_prepublish_check_cli_json_exits_nonzero_on_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        prepublish_check,
        'run_prepublish_check',
        lambda **kwargs: {
            'ok': False,
            'repo': '.',
            'expected_remote': 'x',
            'checks': {},
            'failures': ['secret_scan'],
            'destructive_actions_performed': False,
        },
    )

    with pytest.raises(SystemExit):
        prepublish_check.main(['--json'])

    assert '"ok": false' in capsys.readouterr().out
