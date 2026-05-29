

def test_readme_contains_safe_autonomy_demo_flow():
    readme = open('README.md', encoding='utf-8').read()
    assert 'Safe Autonomy Demo Flow' in readme
    assert 'GitHub PR dry-run' in readme
    assert 'Sandbox execution review' in readme
    assert 'Diff intake checklist' in readme
    assert 'Raw stdout/stderr are never persisted' in readme
    assert 'policy_rejected' in readme
    assert 'Runtime state, caches, virtualenvs, and secret files are ignored' in readme
