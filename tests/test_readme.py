

def test_readme_contains_safe_autonomy_demo_flow():
    readme = open('README.md', encoding='utf-8').read()
    assert 'Safe Autonomy Demo Flow' in readme
    assert 'GitHub PR dry-run' in readme
    assert 'Sandbox execution review' in readme
    assert 'Diff intake checklist' in readme
    assert 'Raw stdout/stderr are never persisted' in readme
    assert 'policy_rejected' in readme
    assert 'Runtime state, caches, virtualenvs, and secret files are ignored' in readme


def test_security_policy_documents_never_persist_data():
    security = open('SECURITY.md', encoding='utf-8').read()
    assert 'Data We Never Persist' in security
    assert 'Raw stdout/stderr' in security
    assert 'Raw diff text' in security
    assert 'Request bodies' in security
    assert '.venv/' in security
    assert 'root/runtime `*.jsonl`' in security


def test_oss_release_checklist_contains_artifact_and_secret_checks():
    checklist = open('OSS_RELEASE_CHECKLIST.md', encoding='utf-8').read()
    assert 'tracked bad-artifact check' in checklist
    assert 'git remote -v' in checklist
    assert 'cpos.secret_scan' in checklist
    assert 'No raw stdout/stderr' in checklist
    assert 'Never stage / never publish' in checklist
    assert '.venv/' in checklist
    assert 'runtime `*.jsonl`' in checklist
