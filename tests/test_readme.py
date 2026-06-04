

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
    assert '320 passed' in notes
    assert 'ok=true' in notes


def test_readme_positioning_mentions_safe_autonomy_and_no_raw_persistence():
    readme = open('README.md', encoding='utf-8').read()
    assert 'safe autonomy' in readme
    assert 'relationship memory, task execution, and runtime state' in readme
    assert 'sandbox retry/replan loop' in readme
    assert 'raw diffs' in readme


def test_github_publish_safety_spec_references_vps_rules_and_skill_adapter():
    spec = open('docs/GITHUB_PUBLISH_SAFETY_SPEC.md', encoding='utf-8').read()
    assert '/home/mayutama/AGENTS.md' in spec
    assert '/home/mayutama/AI_RULES.md' in spec
    assert 'neko-agent' in spec
    assert 'claude-code-security' in spec
    assert 'Skill / MCP adapter contract' in spec
    assert 'must not stage, commit, push, delete' in spec


def test_oss_checklist_references_github_publish_safety_spec():
    checklist = open('OSS_RELEASE_CHECKLIST.md', encoding='utf-8').read()
    assert 'docs/GITHUB_PUBLISH_SAFETY_SPEC.md' in checklist
    assert 'no staging/commit/push/delete operations by itself' in checklist


def test_readme_documents_combined_prepublish_gate():
    readme = open('README.md', encoding='utf-8').read()
    assert 'cpos.prepublish_check' in readme
    assert 'cpos.github_publish_guard' in readme
    assert 'cpos.release_check' in readme
    assert 'cpos.secret_scan' in readme
    assert 'before any staging, commit, push, deletion, or history rewrite' in readme


def test_oss_checklist_includes_combined_prepublish_gate():
    checklist = open('OSS_RELEASE_CHECKLIST.md', encoding='utf-8').read()
    assert 'combined pre-publish safety gate' in checklist
    assert 'cpos.prepublish_check --json' in checklist


def test_publish_safety_user_guide_is_documented_and_friendly():
    readme = open('README.md', encoding='utf-8').read()
    guide = open('docs/PUBLISH_SAFETY_USER_GUIDE.md', encoding='utf-8').read()
    assert 'docs/PUBLISH_SAFETY_USER_GUIDE.md' in readme
    assert 'The one command' in guide
    assert 'How to read the result' in guide
    assert 'Do not push' in guide
    assert 'does not stage, commit, push, delete' in guide
    assert 'Move real secrets to Vault' in guide


def test_readme_documents_human_escalation_protocol():
    readme = open('README.md', encoding='utf-8').read()
    protocol = open('docs/HUMAN_ESCALATION_PROTOCOL.md', encoding='utf-8').read()
    assert 'assisted autonomy' in readme
    assert 'docs/HUMAN_ESCALATION_PROTOCOL.md' in readme
    assert 'Human escalation is not a weakness' in protocol
    assert 'cpos.human_escalation' in protocol
    assert 'does not stage, commit, push, delete, open ports, or read' in protocol


def test_pitch_highlights_competitive_demo_readiness_and_fast_resume():
    pitch = open('PITCH.md', encoding='utf-8').read()
    assert 'Competitive Demo Readiness' in pitch
    assert 'tape-memory-mcp' in pitch
    assert '/demo/readiness' in pitch
    assert '/demo/fixture' in pitch
    assert 'Ready-to-Run Gate' in pitch
    assert 'approval_separated' not in pitch  # pitch uses human-readable language
    assert 'Approval separated from execution' in pitch
    assert 'Hermes / OpenClaw / Claude Code-style agents' in pitch
    assert 'raw diffs, raw stdout/stderr' in pitch


def test_demo_capture_guide_documents_current_competitive_flow():
    guide = open('docs/DEMO_CAPTURE_GUIDE.md', encoding='utf-8').read()
    assert 'Competitive Demo Readiness' in guide
    assert '/demo/fixture' in guide
    assert '/demo/readiness' in guide
    assert 'Human Escalation Queue' in guide
    assert 'Patch Generation Reviews' in guide
    assert 'Ready-to-Run Execution Reviews' in guide
    assert 'Sandbox Autonomy Flow Graph' in guide
    assert 'metadata_only=true' in guide
    assert 'raw_diff_stored=false' in guide
    assert 'raw_outputs_stored=false' in guide
    assert 'does not execute tools, apply patches, mutate the live repo, commit, push, create PRs' in guide


def test_readme_release_notes_and_checklist_include_competitive_demo_updates():
    readme = open('README.md', encoding='utf-8').read()
    notes = open('RELEASE_NOTES_v0.1.0.md', encoding='utf-8').read()
    checklist = open('OSS_RELEASE_CHECKLIST.md', encoding='utf-8').read()

    assert 'Quick Competitive Demo' in readme
    assert '/demo/readiness' in readme
    assert '/demo/fixture' in readme
    assert 'Ready-to-Run Execution' in readme
    assert 'Competitive Demo Readiness' in notes
    assert 'Metadata-only demo fixture' in notes
    assert '320 passed' in notes
    assert 'Quick Competitive Demo' in checklist
    assert 'Competitive Demo Readiness' in checklist
    assert '320 passed' in checklist
