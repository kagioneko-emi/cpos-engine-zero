

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
    assert 'docs/AGENT_ADAPTER_INTEGRATION.md' in readme
    assert 'docs/AGENT_ADAPTER_SCHEMA.md' in readme
    assert 'examples/agent_adapter_client.py' in readme
    assert 'examples/payloads/' in readme
    assert '/demo/readiness' in readme
    assert '/demo/fixture' in readme
    assert 'Ready-to-Run Execution' in readme
    assert 'Competitive Demo Readiness' in notes
    assert 'Metadata-only demo fixture' in notes
    assert '320 passed' in notes
    assert 'Quick Competitive Demo' in checklist
    assert 'Competitive Demo Readiness' in checklist
    assert '320 passed' in checklist


def test_external_agent_5_min_guide_is_linked_and_safety_focused():
    readme = open('README.md', encoding='utf-8').read()
    guide = open('docs/EXTERNAL_AGENT_5_MIN_GUIDE.md', encoding='utf-8').read()

    assert 'docs/EXTERNAL_AGENT_5_MIN_GUIDE.md' in readme
    assert 'CPOS for Agents' in guide
    assert '/agent-adapter/intake' in guide
    assert 'examples/payloads/command_request.json' in guide
    assert 'examples/payloads/proposed_diff.json' in guide
    assert 'examples/payloads/execution_result.json' in guide
    assert 'invalid_raw_execution_result.json' in guide
    assert 'execute_automatically=false' in guide
    assert 'raw_outputs_stored=false' in guide
    assert 'execute external-agent commands' in guide
    assert 'does not require opening public ports' in guide


def test_announcement_copy_pack_is_linked_and_safety_focused():
    readme = open('README.md', encoding='utf-8').read()
    copy = open('docs/ANNOUNCEMENT_COPY_v0.1.0.md', encoding='utf-8').read()

    assert 'docs/ANNOUNCEMENT_COPY_v0.1.0.md' in readme
    assert 'GitHub Release: https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0' in copy
    assert 'https://zenn.dev/kagioneko/articles/cpos-engine-zero-v010' in copy
    assert 'Notion summary' in copy
    assert 'CPOS is' in copy
    assert 'CPOS is not' in copy
    assert 'External Agent Safety Layer' in copy
    assert 'does not auto-execute external commands' in copy
    assert 'fully autonomous unrestricted coding agent' in copy
    assert 'metadata-only' in copy
    assert 'Human Escalation' in copy


def test_local_runtime_inventory_is_linked_and_non_destructive():
    readme = open('README.md', encoding='utf-8').read()
    inventory = open('docs/LOCAL_RUNTIME_FILE_INVENTORY.md', encoding='utf-8').read()

    assert 'docs/LOCAL_RUNTIME_FILE_INVENTORY.md' in readme
    assert 'Local Runtime File Inventory' in inventory
    assert 'Do not delete files automatically' in inventory
    assert 'Do not run `rm -rf` without explicit confirmation' in inventory
    assert 'Do not print secrets' in inventory
    assert '.venv/' in inventory
    assert 'cpos/*.jsonl' in inventory
    assert 'certs/' in inventory
    assert 'hackathon_report.html' in inventory
    assert 'Never modify `authorized_keys`' in inventory
    assert 'prepublish_check' in inventory


def test_v0_1_1_summary_is_linked_and_complete():
    readme = open('README.md', encoding='utf-8').read()
    summary = open('docs/V0_1_1_SUMMARY.md', encoding='utf-8').read()

    assert 'docs/V0_1_1_SUMMARY.md' in readme
    assert 'v0.1.1 Stabilization Summary' in summary
    assert 'Adapter schema validation' in summary
    assert 'Adapter payload examples' in summary
    assert '5-minute external-agent safety-layer guide' in summary
    assert 'announcement copy pack' in summary.lower()
    assert 'Local runtime file inventory' in summary
    assert 'Dashboard wording polish' in summary
    assert '338 passed' in summary
    assert 'prepublish_check' in summary
    assert 'Do not tag, push, publish' in summary


def test_v0_1_1_release_notes_and_draft_are_linked_and_safety_focused():
    readme = open('README.md', encoding='utf-8').read()
    notes = open('RELEASE_NOTES_v0.1.1.md', encoding='utf-8').read()
    draft = open('GITHUB_RELEASE_DRAFT_v0.1.1.md', encoding='utf-8').read()

    assert 'RELEASE_NOTES_v0.1.1.md' in readme
    assert 'GITHUB_RELEASE_DRAFT_v0.1.1.md' in readme
    assert 'v0.1.1 Release Notes' in notes
    assert 'CPOS for Agents' in notes
    assert 'Adapter schema validation' in notes
    assert '338 passed' in notes
    assert 'prepublish_check' in notes
    assert 'CPOS Engine-Zero v0.1.1' in draft
    assert 'External Agent Adapter validation' in draft
    assert 'metadata-only' in draft
    assert 'execute_automatically' in draft
    assert 'Not enabled by default' in draft
    assert 'release_check --json' in draft


def test_v0_1_2_backlog_and_next_work_sequence_are_linked():
    readme = open('README.md', encoding='utf-8').read()
    backlog = open('docs/backlog/V0_1_2_BACKLOG.md', encoding='utf-8').read()
    sequence = open('docs/NEXT_WORK_SEQUENCE.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()

    assert 'docs/backlog/V0_1_2_BACKLOG.md' in readme
    assert 'ideas-only backlog' in backlog
    assert 'Adapter contract schema export' in backlog
    assert 'GitHub Actions safety checks' in backlog
    assert 'Final v0.1.1 release follow-through' in backlog
    assert '1 → 3 → 2' in sequence
    assert 'cpos-for-agents-v011-rc1.md' in handoff
    assert 'published: false' in handoff
    assert 'no implementation started' in handoff.lower()


def test_cognitive_agent_os_architecture_is_linked_and_safety_focused():
    readme = open('README.md', encoding='utf-8').read()
    arch = open('docs/COGNITIVE_AGENT_OS_ARCHITECTURE.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()

    assert 'docs/COGNITIVE_AGENT_OS_ARCHITECTURE.md' in readme
    assert 'Kagioneko Cognitive Agent OS' in arch
    assert 'not a claim that the system is AGI' in arch
    assert 'Sensor Layer' in arch
    assert 'Goal Manager' in arch
    assert 'Self-Evaluation Gate' in arch
    assert 'Unified Event Bus' in arch
    assert 'World Model' in arch
    assert 'Sleep / Consolidation' in arch
    assert 'Permission ladder' in arch
    assert 'VN-CPU / UNO should start at Level 0' in arch
    assert 'SENSOR_AND_GOAL_MANAGER_SPEC.md' in arch
    assert 'Cognitive Agent OS architecture draft' in handoff


def test_sensor_and_goal_manager_spec_is_linked_and_doc_only():
    readme = open('README.md', encoding='utf-8').read()
    spec = open('docs/SENSOR_AND_GOAL_MANAGER_SPEC.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()

    assert 'docs/SENSOR_AND_GOAL_MANAGER_SPEC.md' in readme
    assert 'Sensor and Goal Manager Spec' in spec
    assert 'documentation-only specification' in spec
    assert 'Base sensor event schema' in spec
    assert 'Git sensor' in spec
    assert 'Docker/process sensor' in spec
    assert 'Time/session sensor' in spec
    assert 'Goal schema' in spec
    assert 'Wellbeing advisory rules' in spec
    assert 'Human Escalation triggers' in spec
    assert 'Not implemented by this spec' in spec
    assert 'Sensor and Goal Manager spec draft' in handoff


def test_event_bus_and_world_model_spec_is_linked_and_doc_only():
    readme = open('README.md', encoding='utf-8').read()
    spec = open('docs/EVENT_BUS_AND_WORLD_MODEL_SPEC.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()

    assert 'docs/EVENT_BUS_AND_WORLD_MODEL_SPEC.md' in readme
    assert 'Event Bus and World Model Spec' in spec
    assert 'documentation-only specification' in spec
    assert 'Base event schema' in spec
    assert 'sensor_event' in spec
    assert 'goal_update' in spec
    assert 'world fact schema' in spec.lower()
    assert 'Staleness rules' in spec
    assert 'Relationship to CPOS Task Tape' in spec
    assert 'Relationship to Observatory' in spec
    assert 'Relationship to tape-memory' in spec
    assert 'implementation should wait for review' in spec
    assert 'Event Bus and World Model spec draft' in handoff


def test_cognitive_agent_os_roadmap_is_linked_and_doc_only():
    readme = open('README.md', encoding='utf-8').read()
    roadmap = open('docs/COGNITIVE_AGENT_OS_ROADMAP.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()

    assert 'docs/COGNITIVE_AGENT_OS_ROADMAP.md' in readme
    assert 'Kagioneko Cognitive Agent OS' in roadmap
    assert 'documentation-only' in roadmap
    assert 'Phase 1 — Read-only software sensors' in roadmap
    assert 'Phase 2 — Goal Manager MVP' in roadmap
    assert 'Phase 3 — World Model snapshot' in roadmap
    assert 'VN-CPU / UNO observe-only bridge' in roadmap
    assert 'Limited low-risk autonomy' in roadmap
    assert 'final release requires explicit user confirmation' in roadmap
    assert 'Cognitive Agent OS roadmap draft' in handoff



def test_android_emilia_and_db_inventory_docs_are_linked_and_safe():
    readme = open('README.md', encoding='utf-8').read()
    emilia = open('docs/ANDROID_EMILIA_SENSOR_BRIDGE.md', encoding='utf-8').read()
    db = open('docs/DB_REFLECTION_SOURCE_INVENTORY.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()

    assert 'docs/ANDROID_EMILIA_SENSOR_BRIDGE.md' in readme
    assert 'docs/DB_REFLECTION_SOURCE_INVENTORY.md' in readme
    assert 'observe-only' in emilia
    assert 'no microphone/camera content ingestion' in emilia
    assert 'no automatic upload/publish/video pipeline trigger' in emilia
    assert 'metadata_only' in emilia
    assert 'inventory-only' in db
    assert 'no row contents' in db
    assert 'no token/config values' in db
    assert 'DB reflection source inventory note' in handoff
    assert 'Android Emilia sensor bridge note' in handoff
