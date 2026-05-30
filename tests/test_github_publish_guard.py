import subprocess

from cpos.github_publish_guard import run_guard


def git(repo, *args):
    result = subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result


def init_repo(tmp_path):
    git(tmp_path, 'init')
    git(tmp_path, 'remote', 'add', 'origin', 'https://github.com/example/project.git')
    (tmp_path / 'README.md').write_text('# demo\n', encoding='utf-8')
    (tmp_path / 'SECURITY.md').write_text('# security\n', encoding='utf-8')
    git(tmp_path, 'add', 'README.md', 'SECURITY.md')
    git(tmp_path, '-c', 'user.email=a@example.invalid', '-c', 'user.name=a', 'commit', '-m', 'init')


def test_github_publish_guard_ok(tmp_path):
    init_repo(tmp_path)

    result = run_guard(repo=tmp_path, expected_remote='https://github.com/example/project.git')

    assert result['ok'] is True
    assert result['destructive_actions_performed'] is False


def test_github_publish_guard_detects_dirty_untracked_and_bad_tracked(tmp_path):
    init_repo(tmp_path)
    (tmp_path / 'pointers.jsonl').write_text('{}\n', encoding='utf-8')
    git(tmp_path, 'add', 'pointers.jsonl')
    git(tmp_path, '-c', 'user.email=a@example.invalid', '-c', 'user.name=a', 'commit', '-m', 'bad runtime')
    (tmp_path / '.env').write_text('TOKEN=do-not-use\n', encoding='utf-8')
    (tmp_path / 'README.md').write_text('# changed\n', encoding='utf-8')

    result = run_guard(repo=tmp_path, expected_remote='https://github.com/wrong/project.git')

    assert result['ok'] is False
    errors = {failure['error'] for failure in result['failures']}
    assert 'unexpected_remote' in errors
    assert 'working_tree_not_clean' in errors
    assert 'tracked_forbidden_or_runtime_artifacts' in errors
    assert 'review_or_ignore_before_publish' in errors
    assert 'pointers.jsonl' in result['tracked_bad_artifacts']
    assert '.env' in result['untracked_risky_files']


def test_github_publish_guard_can_allow_dirty_and_skip_untracked(tmp_path):
    init_repo(tmp_path)
    (tmp_path / '.env').write_text('TOKEN=do-not-use\n', encoding='utf-8')
    (tmp_path / 'README.md').write_text('# changed\n', encoding='utf-8')

    result = run_guard(
        repo=tmp_path,
        expected_remote='https://github.com/example/project.git',
        require_clean=False,
        include_untracked_risky=False,
    )

    assert result['ok'] is True
    assert result['git_status_lines']
