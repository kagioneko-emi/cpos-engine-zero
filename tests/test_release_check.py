import subprocess
from types import SimpleNamespace

import cpos.release_check as release_check


class _Completed:
    def __init__(self, stdout='', returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def test_release_check_ok(monkeypatch, tmp_path):
    monkeypatch.setattr(release_check, '_repo_root', lambda: tmp_path)
    monkeypatch.setattr(release_check, '_current_remote_url', lambda: 'https://github.com/kagioneko/cpos-engine-zero.git')
    monkeypatch.setattr(release_check, '_git_status_lines', lambda: [])
    monkeypatch.setattr(release_check, '_tracked_bad_artifacts', lambda: [])
    for path in release_check.REQUIRED_FILES:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text('x', encoding='utf-8')

    result = release_check.run_release_check()

    assert result['ok'] is True
    assert result['failures'] == []


def test_release_check_detects_problems(monkeypatch, tmp_path):
    monkeypatch.setattr(release_check, '_repo_root', lambda: tmp_path)
    monkeypatch.setattr(release_check, '_current_remote_url', lambda: 'https://example.invalid/repo.git')
    monkeypatch.setattr(release_check, '_git_status_lines', lambda: [' M README.md'])
    monkeypatch.setattr(release_check, '_tracked_bad_artifacts', lambda: ['pointers.jsonl'])
    monkeypatch.setattr(release_check.Path, 'exists', lambda self: False)

    result = release_check.run_release_check()

    assert result['ok'] is False
    errors = {failure['error'] for failure in result['failures']}
    assert 'unexpected_remote' in errors
    assert 'working_tree_not_clean' in errors
    assert 'bad_artifacts_tracked' in errors
    assert 'missing_required_files' in errors


def test_release_check_cli_json(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(release_check, 'run_release_check', lambda: {'ok': True, 'remote_url': 'x', 'git_status_lines': [], 'tracked_bad_artifacts': [], 'missing_files': [], 'failures': []})

    release_check.main(['--json'])

    out = capsys.readouterr().out
    assert '"ok": true' in out
