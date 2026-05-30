

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


def test_release_check_cli_documented_in_oss_checklist():
    checklist = open('OSS_RELEASE_CHECKLIST.md', encoding='utf-8').read()
    assert 'cpos.release_check' in checklist
    assert 'release-readiness CLI' in checklist


def test_readme_contains_architecture_at_a_glance():
    readme = open('README.md', encoding='utf-8').read()
    assert 'Architecture at a Glance' in readme
    assert 'Context Router' in readme
    assert 'Context Pointer' in readme
    assert 'Task Tape' in readme
    assert 'Review-Gated Execution Pipeline' in readme
    assert 'Persistence Boundary' in readme
    assert 'Never store: secrets, raw stdout/stderr, raw diff, request bodies' in readme


def test_release_notes_include_current_safe_autonomy_features():
    notes = open('RELEASE_NOTES_v0.1.0.md', encoding='utf-8').read()
    assert 'Safe autonomy loop' in notes
    assert 'Sandbox execution retry reviews' in notes
    assert 'Sandbox replan templates' in notes
    assert 'Sandbox diff intakes' in notes
    assert 'Release readiness CLI' in notes
    assert '228 passed' in notes
    assert 'ok=true' in notes


def test_readme_positioning_mentions_safe_autonomy_and_no_raw_persistence():
    readme = open('README.md', encoding='utf-8').read()
    assert 'safe autonomy' in readme
    assert 'relationship memory, task execution, and runtime state' in readme
    assert 'sandbox retry/replan loop' in readme
    assert 'raw diffs' in readme
