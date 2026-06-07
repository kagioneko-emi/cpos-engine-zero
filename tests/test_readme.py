

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



def test_world_model_snapshot_command_is_linked_and_safe():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    world_model = open('cpos/world_model.py', encoding='utf-8').read()

    assert 'cpos.world_model snapshot --json' in readme
    assert 'World Model snapshot MVP' in handoff
    assert 'kagioneko.world_model_snapshot.v1' in world_model
    assert 'metadata_only' in world_model
    assert 'raw_diff_stored' in world_model
    assert 'secret_values_stored' in world_model
    assert 'execute_automatically' in world_model
    assert 'kagioneko/cognitive-agent-os-lab' in world_model



def test_goal_manager_command_is_linked_and_safe():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()
    world_model = open('cpos/world_model.py', encoding='utf-8').read()

    assert 'cpos.goals list --json' in readme
    assert 'Goal Manager MVP' in handoff
    assert 'kagioneko.goal.v1' in goals
    assert 'write_enabled' in goals
    assert 'autonomous_goal_updates' in goals
    assert 'self_preservation_goals' in goals
    assert 'goal_summary' in world_model



def test_db_inventory_sensor_command_is_linked_and_path_only():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    sensor = open('cpos/sensors/db_inventory_sensor.py', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert 'cpos.sensors.db_inventory_sensor --root . --json' in readme
    assert 'DB inventory sensor MVP' in handoff
    assert 'DB files are not opened' in handoff
    assert 'row_contents_read' in sensor
    assert 'table_names_read' in sensor
    assert 'db_files_opened' in sensor
    assert 'sensitive_skipped' in sensor
    assert 'goal_id="db_inventory_sensor"' in goals
    assert 'state="done"' in goals



def test_android_emilia_sensor_command_is_linked_and_observe_only():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    sensor = open('cpos/sensors/android_emilia_sensor.py', encoding='utf-8').read()
    doc = open('docs/ANDROID_EMILIA_SENSOR_BRIDGE.md', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert 'cpos.sensors.android_emilia_sensor --json' in readme
    assert 'Android Emilia bridge inventory sensor MVP' in handoff
    assert 'content is not read' in handoff
    assert 'phone_data_read' in sensor
    assert 'microphone_content_read' in sensor
    assert 'video_pipeline_triggered' in sensor
    assert 'phone_control_enabled' in sensor
    assert 'Concrete local paths belong in the private lab repo' in doc
    assert 'goal_id="android_emilia_bridge_sensor"' in goals
    assert 'state="done"' in goals



def test_world_model_optional_sensor_summaries_are_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    world_model = open('cpos/world_model.py', encoding='utf-8').read()

    assert '--include-db-inventory' in readme
    assert '--include-android-emilia' in readme
    assert 'World Model optional sensor summaries' in handoff
    assert 'Optional sensors are absent by default' in handoff
    assert 'not candidate path lists' in handoff
    assert '_compact_sensor' in world_model
    assert 'optional_sensors' in world_model



def test_reflection_evaluator_command_is_linked_and_safe():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    evaluator = open('cpos/reflection_evaluator.py', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert 'cpos.reflection_evaluator evaluate --json' in readme
    assert 'Reflection Evaluator MVP' in handoff
    assert 'proceed`, `ask`, `defer`, or `block`' in handoff
    assert 'kagioneko.reflection_evaluation.v1' in evaluator
    assert 'execute_automatically' in evaluator
    assert 'raw_db_rows' in evaluator
    assert 'authorized_keys' in evaluator
    assert 'reflection_evaluator_mvp' in goals



def test_goal_store_validator_is_linked_and_read_only():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    goal_store = open('cpos/goal_store.py', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()
    example = open('goals/goals.example.json', encoding='utf-8').read()

    assert 'cpos.goal_store validate --path goals/goals.example.json --json' in readme
    assert 'Goal Store Phase 1' in handoff
    assert 'validates only; no writes' in handoff
    assert 'kagioneko.goal_store_validation.v1' in goal_store
    assert 'write_enabled_forbidden' in goal_store
    assert 'self_preservation_goal_forbidden' in goal_store
    assert 'risky_text_detected' in goal_store
    assert 'goal_store_phase1' in goals
    assert 'kagioneko.goal_set.v1' in example



def test_world_model_goal_store_summary_is_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    world_model = open('cpos/world_model.py', encoding='utf-8').read()

    assert '--goal-store goals/goals.example.json' in readme
    assert 'World Model goal store validation summary' in handoff
    assert 'validation only; no writes' in handoff
    assert 'goal_store_validation_failed' in world_model
    assert 'goal_store_validation' in world_model
    assert '_compact_goal_store_validation' in world_model


def test_goal_store_summary_and_tape_memory_bridge_are_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    goal_store = open('cpos/goal_store.py', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()
    bridge = open('docs/TAPE_MEMORY_BRIDGE_DESIGN.md', encoding='utf-8').read()

    assert 'cpos.goal_store summary --path goals/goals.example.json --json' in readme
    assert 'kagioneko.goal_store_summary.v1' in goal_store
    assert 'build_goal_store_summary' in goal_store
    assert 'Goal Store summary/export' in handoff
    assert 'docs/TAPE_MEMORY_BRIDGE_DESIGN.md' in readme
    assert 'kagioneko.tape_memory_bridge_pointer.v1' in bridge
    assert 'metadata-only resume pointers' in bridge
    assert 'secret_values_stored' in bridge
    assert 'execute_automatically' in bridge
    assert 'goal_store_summary_export' in goals
    assert 'tape_memory_bridge_design' in goals


def test_resume_pointer_cli_and_world_model_link_are_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    resume_pointer = open('cpos/resume_pointer.py', encoding='utf-8').read()
    world_model = open('cpos/world_model.py', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert 'cpos.resume_pointer build --goal-store goals/goals.example.json --json' in readme
    assert '--include-resume-pointer' in readme
    assert 'Resume Pointer read-only CLI' in handoff
    assert 'kagioneko.tape_memory_bridge_pointer.v1' in resume_pointer
    assert 'tape_memory_write_enabled' in resume_pointer
    assert 'include_resume_pointer' in world_model
    assert 'resume_pointer_cli' in goals


def test_resume_pointer_reflection_and_handoff_digest_are_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    resume_pointer = open('cpos/resume_pointer.py', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert '--reflection-json eval.json --include-handoff-digest' in readme
    assert 'Resume Pointer Reflection metadata + safe handoff digest' in handoff
    assert 'kagioneko.safe_handoff_digest.v1' in resume_pointer
    assert 'full_handoff_stored' in resume_pointer
    assert 'body_included' in resume_pointer
    assert 'resume_pointer_reflection_handoff' in goals


def test_resume_pointer_validator_and_write_plan_are_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    resume_pointer = open('cpos/resume_pointer.py', encoding='utf-8').read()
    bridge = open('docs/TAPE_MEMORY_BRIDGE_DESIGN.md', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert 'cpos.resume_pointer validate --pointer-json pointer.json --json' in readme
    assert 'cpos.resume_pointer write-plan --pointer-json pointer.json --json' in readme
    assert 'Resume Pointer validator + tape-memory write dry-run plan' in handoff
    assert 'kagioneko.resume_pointer_validation.v1' in resume_pointer
    assert 'kagioneko.tape_memory_write_plan.v1' in resume_pointer
    assert 'would_write' in resume_pointer
    assert 'dry_run=true' in bridge
    assert 'would_write=false' in bridge
    assert 'resume_pointer_validator_dry_run' in goals


def test_resume_pipeline_bundle_is_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    pipeline = open('cpos/resume_pipeline.py', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert 'cpos.resume_pipeline run --goal-store goals/goals.example.json --json' in readme
    assert 'Integrated read-only resume pipeline bundle' in handoff
    assert 'kagioneko.resume_pipeline_bundle.v1' in pipeline
    assert 'tape_memory_write_plan_dry_run' in pipeline
    assert 'would_write' in pipeline
    assert 'resume_pipeline_bundle' in goals


def test_resume_pipeline_compact_and_v012_backlog_are_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    pipeline = open('cpos/resume_pipeline.py', encoding='utf-8').read()
    backlog = open('docs/backlog/V0_1_2_BACKLOG.md', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert '--compact' in readme
    assert 'kagioneko.resume_pipeline_compact.v1' in pipeline
    assert 'compact_resume_pipeline_bundle' in pipeline
    assert 'Resume Pipeline compact output and v0.1.2 backlog update' in handoff
    assert 'Resume Pipeline stabilization' in backlog
    assert 'fast resume without raw logs' in backlog
    assert 'resume_pipeline_compact' in goals


def test_resume_pipeline_secret_scan_and_summary_are_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    pipeline = open('cpos/resume_pipeline.py', encoding='utf-8').read()
    summary = open('docs/V0_1_2_RESUME_PIPELINE_SUMMARY.md', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert '--scan-compact' in readme
    assert 'docs/V0_1_2_RESUME_PIPELINE_SUMMARY.md' in readme
    assert 'kagioneko.resume_pipeline_compact_secret_scan.v1' in pipeline
    assert 'compact payload secret-pattern scan' in summary
    assert 'would_write=false' in summary
    assert 'Resume Pipeline compact secret scan + summary doc' in handoff
    assert 'resume_pipeline_secret_scan_summary' in goals


def test_vault_backed_notion_helper_is_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    helper = open('cpos/notion_vault_client.py', encoding='utf-8').read()
    doc = open('docs/VAULT_BACKED_NOTION_HELPER.md', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert 'cpos.notion_vault_client page' in readme
    assert 'Vault-backed Notion helper' in handoff
    assert 'secret/notion' in helper
    assert 'VAULT_ADDR' in helper
    assert '--execute' in doc
    assert 'Do not hardcode Notion tokens' in doc
    assert 'vault_backed_notion_helper' in goals


def test_v012_readiness_rotate_and_zenn_publish_docs_are_linked():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    readiness = open('docs/V0_1_2_READINESS_REVIEW.md', encoding='utf-8').read()
    rotate = open('docs/NOTION_CREDENTIAL_ROTATE_RUNBOOK.md', encoding='utf-8').read()
    zenn = open('docs/ZENN_COGNITIVE_AGENT_OS_PUBLISH_CHECKLIST.md', encoding='utf-8').read()

    assert 'docs/V0_1_2_READINESS_REVIEW.md' in readme
    assert 'docs/NOTION_CREDENTIAL_ROTATE_RUNBOOK.md' in readme
    assert 'docs/ZENN_COGNITIVE_AGENT_OS_PUBLISH_CHECKLIST.md' in readme
    assert 'v0.1.2 readiness / Notion rotate runbook / Zenn publish checklist' in handoff
    assert 'does not authorize a release' in readiness
    assert 'does not rotate credentials by itself' in rotate
    assert 'This document does not publish the article' in zenn


def test_zenn_to_notion_bridge_dry_run_is_documented():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    bridge = open('cpos/notion_zenn_bridge.py', encoding='utf-8').read()
    doc = open('docs/ZENN_TO_NOTION_BRIDGE_DRY_RUN.md', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()

    assert 'cpos.notion_zenn_bridge bridge' in readme
    assert 'Zenn-to-Notion dry-run bridge' in handoff
    assert 'kagioneko.notion_zenn_bridge.v1' in bridge
    assert 'old_helper_modified' in bridge
    assert 'does not read Vault' in doc
    assert 'zenn_to_notion_bridge_dry_run' in goals


def test_tape_memory_real_write_gate_design_is_linked():
    readme = open('README.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()
    bridge = open('docs/TAPE_MEMORY_BRIDGE_DESIGN.md', encoding='utf-8').read()
    gate = open('docs/TAPE_MEMORY_REAL_WRITE_GATE_DESIGN.md', encoding='utf-8').read()

    assert 'docs/TAPE_MEMORY_REAL_WRITE_GATE_DESIGN.md' in readme
    assert 'tape-memory real write gate design' in handoff
    assert 'Real write gate design' in bridge
    assert 'WRITE TAPE MEMORY RESUME POINTER' in gate
    assert 'Shorthand such as `ぷす`, `ok`, or `go` must not be accepted' in gate
    assert 'dry_run = true' in gate
    assert 'would_write = false' in gate
    assert 'write_enabled = false' in gate
    assert 'This writer does not exist yet' in gate


def test_tape_memory_mock_writer_gate_is_documented():
    readme = open('README.md', encoding='utf-8').read()
    bridge = open('docs/TAPE_MEMORY_BRIDGE_DESIGN.md', encoding='utf-8').read()
    gate = open('docs/TAPE_MEMORY_REAL_WRITE_GATE_DESIGN.md', encoding='utf-8').read()
    goals = open('cpos/goals.py', encoding='utf-8').read()
    writer = open('cpos/tape_memory_mock_writer.py', encoding='utf-8').read()

    assert 'cpos.tape_memory_mock_writer write' in readme
    assert 'local_mock_file_for_tests_only' in bridge
    assert 'Test-only mock writer' in gate
    assert 'real_tape_memory_write = false' in gate
    assert 'ぷす`, `ok`, or `go` are rejected' in gate
    assert 'CONFIRMATION_PHRASE = "WRITE TAPE MEMORY RESUME POINTER"' in writer
    assert 'tape_memory_mock_writer_gate' in goals


def test_v0_1_2_release_drafts_are_linked_and_safety_scoped():
    readme = open('README.md', encoding='utf-8').read()
    notes = open('RELEASE_NOTES_v0.1.2.md', encoding='utf-8').read()
    draft = open('GITHUB_RELEASE_DRAFT_v0.1.2.md', encoding='utf-8').read()
    handoff = open('NEXT_HANDOFF.md', encoding='utf-8').read()

    assert 'RELEASE_NOTES_v0.1.2.md' in readme
    assert 'GITHUB_RELEASE_DRAFT_v0.1.2.md' in readme
    assert 'Draft only' in notes
    assert 'does not authorize a tag' in notes
    assert 'Fast resume without raw logs' in draft
    assert 'no real tape-memory writes' in draft
    assert 'Not an AGI-completion claim' in draft
    assert 'v0.1.2 release draft prep' in handoff


def test_v0_1_2_readiness_review_is_current():
    review = open('docs/V0_1_2_READINESS_REVIEW.md', encoding='utf-8').read()

    assert '428 passed' in review
    assert 'test-only local mock writer gate' in review
    assert 'local_mock_file_for_tests_only' in review
    assert 'Zenn-to-Notion dry-run bridge' in review
    assert 'v0.1.2 release notes draft' in review
    assert 'not an AGI-completion claim' in review
    assert 'does not authorize a release' in review
