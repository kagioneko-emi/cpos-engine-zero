import server


def test_dashboard_contains_handoff_and_resume_queue_sections():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'handoff-inbox-section' in html
    assert 'handoff-executions-section' in html
    assert 'resume-reviews-section' in html
    assert 'handoff-flow-section' in html
    assert 'handoff-inbox-count' in html
    assert 'handoff-execution-count' in html
    assert 'resume-review-count' in html
    assert 'footprint-bytes' in html
    assert 'rate-limit-backend' in html
    assert 'handoff-flow-status-filter' in html
    assert 'handoff-flow-source-filter' in html
    assert '/footprint' in html
    assert '/handoff-graph' in html
    assert 'renderHandoffFlow' in html


def test_dashboard_contains_queue_action_buttons():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'approveHandoff' in html
    assert 'rejectHandoff' in html
    assert 'approveExecution' in html
    assert 'rejectExecution' in html
    assert 'approveResume' in html
    assert 'rejectResume' in html
    assert '/handoff-inbox/${pointerId}/approve' in html
    assert '/handoff-executions/${taskId}/approve' in html
    assert '/resume-reviews/${taskId}/approve' in html


def test_dashboard_contains_handoff_detail_drilldown():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'handoff-flow-detail' in html
    assert 'showHandoffFlowDetail' in html
    assert 'Handoff Detail Drill-down' in html
    assert 'metadata-only / no raw handoff' in html
    assert 'Filter source' in html




def test_dashboard_contains_autonomy_loop_demo_panel():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'autonomy-loop-demo-section' in html
    assert 'autonomy-loop-demo-summary' in html
    assert 'autonomy-loop-demo-container' in html
    assert 'renderAutonomyLoopDemo' in html
    assert 'Autonomy Loop Demo Panel' in html
    assert 'Diff Draft → GitHub Diff Review → Sandbox Execution' in html
    assert 'raw_diff_stored=false' in html
    assert 'raw_outputs_stored=false' in html
    assert 'auto_execute=false' in html
    assert 'live_repo_patch=false' in html


def test_dashboard_contains_mcp_review_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'mcp-review-section' in html
    assert 'mcp-connector-count' in html
    assert '/mcp/connectors' in html
    assert 'renderMcpReview' in html
    assert 'disableMcpConnector' in html
    assert 'checkMcpTool' in html
    assert 'Text-first governance only' in html


def test_dashboard_contains_mcp_import_review_queue_actions():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert '/mcp/reviews?status=pending' in html
    assert 'mcp-pending-review-container' in html
    assert 'approveMcpReview' in html
    assert 'rejectMcpReview' in html
    assert 'MCP REVIEW PENDING' in html
    assert 'Approve Register' in html
    assert 'unsafe failed definitions are not stored' in html


def test_dashboard_contains_mcp_execution_review_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert '/mcp/executions' in html
    assert 'mcp-execution-review-container' in html
    assert 'MCP EXECUTION REVIEW' in html
    assert 'approveMcpExecution' in html
    assert 'rejectMcpExecution' in html
    assert 'metadata-only: args_values_stored' in html
    assert 'Approve Dry-run' in html


def test_dashboard_contains_github_pr_dry_run_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'github-pr-section' in html
    assert 'github-pr-count' in html
    assert '/github/pr-dry-runs' in html
    assert 'renderGithubPrDryRuns' in html
    assert 'approveGithubPrDryRun' in html
    assert 'rejectGithubPrDryRun' in html
    assert 'GITHUB PR DRY-RUN' in html
    assert 'no branch creation, no commits, no push' in html




def test_dashboard_contains_github_diff_review_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'github-diff-section' in html
    assert 'github-diff-summary' in html
    assert 'github-diff-container' in html
    assert '/github/diff-reviews' in html
    assert 'renderGithubDiffReviews' in html
    assert 'approveGithubDiffReview' in html
    assert 'rejectGithubDiffReview' in html
    assert 'approveDiffAndCreateSandboxExecutionReview' in html
    assert 'Approve → Sandbox Execution Review' in html
    assert '/sandbox/execution-driver/advance' in html
    assert 'raw_diff_stored=false' in html


def test_dashboard_contains_sandbox_patch_plan_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-patch-section' in html
    assert 'sandbox-patch-count' in html
    assert '/sandbox/patch-plans' in html
    assert 'renderSandboxPatchPlans' in html
    assert 'approveSandboxPatchPlan' in html
    assert 'rejectSandboxPatchPlan' in html
    assert 'Sandbox Patch Plans' in html
    assert 'no live repo writes' in html


def test_dashboard_contains_sandbox_patch_execution_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-execution-section' in html
    assert 'sandbox-execution-count' in html
    assert '/sandbox/executions' in html
    assert 'renderSandboxPatchExecutions' in html
    assert 'approveSandboxPatchExecution' in html
    assert 'approveSandboxPatchExecutionAndRun' in html
    assert 'Approve + Run with Supplied Diff' in html
    assert '/sandbox/executions/${taskId}/run' in html
    assert 'raw output' in html
    assert 'rejectSandboxPatchExecution' in html
    assert 'SANDBOX PATCH EXECUTION' in html
    assert 'Isolated Runner Readiness' in html


def test_dashboard_contains_ready_to_run_execution_review_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'ready-to-run-execution-section' in html
    assert 'ready-to-run-execution-summary' in html
    assert 'ready-to-run-execution-container' in html
    assert '/sandbox/executions/ready-to-run' in html
    assert 'renderReadyToRunExecutions' in html
    assert 'READY-TO-RUN EXECUTION REVIEW' in html
    assert 'Ready-to-Run Execution — Final Human Run Gate' in html
    assert 'Final human run gate' in html
    assert 'Plan approval and actual run stay separate' in html
    assert 'transient_diff_required=true' in html
    assert 'Approve Execution Plan Only' in html
    assert 'Approve + Run with Supplied Diff' in html
    assert 'auto_execute=false' in html


def test_dashboard_contains_sandbox_patch_execution_results_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-execution-result-section' in html
    assert 'sandbox-execution-result-container' in html
    assert '/sandbox/executions/completed' in html
    assert 'renderSandboxPatchExecutionResults' in html
    assert 'Show in Sandbox Flow' in html
    assert 'Create Retry → Replan → Diff Intake + Focus Flow' in html
    assert 'focusSandboxFlow' in html
    assert 'success_path_visible=true' in html
    assert 'Sandbox Patch Execution Results' in html
    assert 'raw patch text or command output' in html


def test_dashboard_contains_sandbox_patch_execution_retry_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-retry-section' in html
    assert 'sandbox-retry-container' in html
    assert '/sandbox/execution-retries' in html
    assert 'renderSandboxPatchExecutionRetries' in html
    assert 'approveSandboxPatchExecutionRetry' in html
    assert 'rejectSandboxPatchExecutionRetry' in html
    assert 'SANDBOX RETRY REVIEW' in html
    assert 'no raw stdout/stderr' in html
    assert 'no automatic rerun' in html


def test_dashboard_contains_sandbox_patch_replan_templates_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-replan-section' in html
    assert 'sandbox-replan-container' in html
    assert '/sandbox/replan-templates' in html
    assert 'renderSandboxPatchReplanTemplates' in html
    assert 'SANDBOX REPLAN TEMPLATE' in html
    assert 'suggested_focus' in html
    assert 'next_review_chain' in html
    assert 'without diff text' in html


def test_dashboard_contains_sandbox_replan_diff_intake_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-diff-intake-section' in html
    assert 'sandbox-diff-intake-container' in html
    assert '/sandbox/diff-intakes' in html
    assert 'renderSandboxReplanDiffIntakes' in html
    assert 'SANDBOX DIFF INTAKE' in html
    assert 'required_human_inputs' in html
    assert 'target_api' in html
    assert 'raw diff text is never stored' in html


def test_dashboard_contains_sandbox_execution_driver_actions():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'renderSandboxPatchPlans' in html
    assert 'SANDBOX PATCH PLAN' in html
    assert 'createFailureReplanIntake' in html
    assert '/sandbox/execution-driver/replan-failure' in html
    assert 'Create Retry → Replan → Diff Intake + Focus Flow' in html
    assert 'focusSandboxFlow(taskId)' in html
    assert 'This will not rerun, patch, commit, push, or store raw outputs' in html


def test_dashboard_contains_execution_scoreboard_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-scoreboard-section' in html
    assert 'sandbox-scoreboard-summary' in html
    assert 'sandbox-scoreboard-container' in html
    assert 'renderSandboxExecutionScoreboard' in html
    assert 'Execution Scoreboard' in html
    assert 'Metadata-only throughput snapshot' in html


def test_dashboard_contains_sandbox_flow_graph_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-flow-section' in html
    assert 'sandbox-flow-summary' in html
    assert 'sandbox-flow-container' in html
    assert 'sandbox-flow-source-filter' in html
    assert '/sandbox/flow-graph' in html
    assert 'renderSandboxFlowGraph' in html
    assert 'Sandbox Autonomy Flow Graph' in html
    assert 'failed execution → retry review' in html
    assert 'raw_outputs_stored=false' in html



def test_dashboard_contains_auto_fix_candidate_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-fix-candidate-section' in html
    assert 'sandbox-fix-candidate-container' in html
    assert '/sandbox/fix-candidates' in html
    assert 'renderSandboxAutoFixCandidates' in html
    assert 'createAutoFixCandidate' in html
    assert 'AUTO FIX CANDIDATE' in html
    assert 'Create Auto Fix Candidate' in html
    assert 'Create Patch Generation Review' in html
    assert 'createPatchGenerationReview' in html
    assert 'no raw diff text' in html




def test_dashboard_contains_patch_generation_review_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-patch-generation-section' in html
    assert 'sandbox-patch-generation-summary' in html
    assert 'sandbox-patch-generation-container' in html
    assert '/sandbox/patch-generations' in html
    assert 'renderSandboxPatchGenerationReviews' in html
    assert 'approvePatchGenerationReview' in html
    assert 'rejectPatchGenerationReview' in html
    assert 'createGithubDiffReviewFromPatchGeneration' in html
    assert 'validatePatchGenerationOutput' in html
    assert '/sandbox/patch-generations/${taskId}/validate-output' in html
    assert '/sandbox/patch-generations/${taskId}/advance-to-execution-review' in html
    assert 'Validate Generated Diff' in html
    assert 'Advance to Execution Review' in html
    assert 'advancePatchGenerationToExecutionReview' in html
    assert 'PATCH GENERATION REVIEW' in html
    assert 'git apply --check' in html
    assert 'validation harness stores only hashes' in html


def test_dashboard_contains_diff_review_draft_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-diff-draft-section' in html
    assert 'sandbox-diff-draft-container' in html
    assert '/sandbox/diff-drafts' in html
    assert 'renderSandboxDiffReviewDrafts' in html
    assert 'createDiffReviewDraft' in html
    assert 'DIFF REVIEW DRAFT' in html
    assert 'Create Diff Review Draft' in html
    assert 'Create GitHub Diff Review from Draft' in html
    assert 'createGithubDiffReviewFromDraft' in html
    assert '/sandbox/diff-drafts/${taskId}/create-github-diff-review' in html
    assert 'never stores raw diff text' in html


def test_dashboard_contains_competitive_demo_readiness_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'competitive-demo-readiness-section' in html
    assert 'competitive-demo-readiness-summary' in html
    assert 'competitive-demo-readiness-container' in html
    assert '/demo/readiness' in html
    assert '/demo/fixture' in html
    assert 'renderCompetitiveDemoReadiness' in html
    assert 'createCompetitiveDemoFixture' in html
    assert 'Create Metadata-only Demo Fixture' in html
    assert 'Competitive Demo Readiness' in html
    assert 'Fast resume + Human Escalation' in html
    assert 'approval_separated' in html
    assert 'raw_diff_stored' in html
    assert 'Ready-to-Run Gate' in html


def test_dashboard_contains_external_agent_adapter_wording_polish():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'External Agent Adapter — Metadata-only Review Queue' in html
    assert 'Safety ingress for Codex/Hermes/OpenClaw-style agents' in html
    assert 'Contract approval records metadata only; it does not run commands' in html
    assert 'EXTERNAL AGENT RESULT SCOREBOARD' in html
    assert 'redacted/status-only reports' in html
    assert 'EXTERNAL AGENT CONTRACT REVIEW' in html
    assert 'contract_approval_only=true' in html
    assert 'no_auto_execute=true' in html
    assert 'Approval records this contract only; execution remains separately gated.' in html


def test_dashboard_contains_human_escalation_wording_polish():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'Human Escalation — Assisted Autonomy Gates' in html
    assert 'Human decision queue with metadata-only decisions' in html
    assert 'metadata-only decisions' in html
    assert 'plan_approval_separate_from_run=true' in html
