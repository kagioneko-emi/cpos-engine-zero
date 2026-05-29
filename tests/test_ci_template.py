from pathlib import Path


def test_hardened_ci_workflow_template_is_not_active_github_workflow():
    path = Path("deploy/hardened/github-actions/cpos-hardened-preflight.example.yml")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "Not active unless copied to .github/workflows/" in text
    assert "cpos.secret_scan" in text
    assert "cpos.vault_render" in text
    assert "cpos.preflight --profile hardened" in text
    assert "pytest tests -q" in text
