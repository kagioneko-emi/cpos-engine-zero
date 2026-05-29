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
    assert 'rejectSandboxPatchExecution' in html
    assert 'SANDBOX PATCH EXECUTION' in html
    assert 'Isolated Runner Readiness' in html


def test_dashboard_contains_sandbox_patch_execution_results_ui():
    client = server.app.test_client()
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'sandbox-execution-result-section' in html
    assert 'sandbox-execution-result-container' in html
    assert '/sandbox/executions/completed' in html
    assert 'renderSandboxPatchExecutionResults' in html
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
