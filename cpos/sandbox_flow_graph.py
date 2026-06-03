from __future__ import annotations

from typing import Any

from .task_tape import TaskTapeStore


def _node(node_id: str, kind: str, *, status: str | None = None, label: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": node_id,
        "kind": kind,
        "status": status,
        "label": label or node_id,
        "metadata": metadata or {},
    }


def _edge(source: str | None, target: str | None, relation: str) -> dict[str, Any] | None:
    if not source or not target:
        return None
    return {"source": source, "target": target, "relation": relation}


def build_sandbox_flow_graph(store: TaskTapeStore, *, source_execution_task_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def add_node(item: dict[str, Any]) -> None:
        nodes[item["id"]] = item

    def add_edge(item: dict[str, Any] | None) -> None:
        if item is not None:
            edges.append(item)

    events = [event.to_dict() for event in store.events()]
    for event in events:
        name = event.get("event")
        task_id = event.get("task_id")
        payload = event.get("payload") or {}
        if not task_id:
            continue

        if name == "sandbox_patch_execution_completed":
            if source_execution_task_id and task_id != source_execution_task_id:
                continue
            add_node(_node(
                task_id,
                "sandbox_execution",
                status=event.get("status"),
                label="Sandbox Execution",
                metadata={
                    "failure_kind": payload.get("failure_kind"),
                    "success": payload.get("success"),
                    "patch_applied": payload.get("patch_applied"),
                    "workspace_copied": payload.get("workspace_copied"),
                    "raw_outputs_stored": False,
                },
            ))

        elif name == "review_required" and payload.get("review_type") == "sandbox_patch_execution_retry":
            plan = payload.get("plan") or {}
            source = plan.get("source_execution_task_id")
            if source_execution_task_id and source != source_execution_task_id:
                continue
            add_node(_node(task_id, "retry_review", status=event.get("status"), label="Retry Review", metadata={"failure_kind": plan.get("failure_kind"), "raw_outputs_stored": False}))
            add_edge(_edge(source, task_id, "creates_retry_review"))

        elif name == "sandbox_patch_replan_template_created":
            template = payload.get("template") or {}
            source = template.get("source_execution_task_id")
            if source_execution_task_id and source != source_execution_task_id:
                continue
            add_node(_node(task_id, "replan_template", status=event.get("status"), label="Replan Template", metadata={"failure_kind": template.get("failure_kind"), "diff_text_included": False, "raw_outputs_stored": False}))
            add_edge(_edge(template.get("retry_task_id"), task_id, "creates_replan_template"))

        elif name == "sandbox_replan_diff_intake_created":
            intake = payload.get("intake") or {}
            source = intake.get("source_execution_task_id")
            if source_execution_task_id and source != source_execution_task_id:
                continue
            add_node(_node(task_id, "diff_intake", status=event.get("status"), label="Diff Intake", metadata={"failure_kind": intake.get("failure_kind"), "raw_diff_stored": False, "execute_automatically": False}))
            add_edge(_edge(intake.get("replan_task_id"), task_id, "creates_diff_intake"))

        elif name == "sandbox_auto_fix_candidate_created":
            candidate = payload.get("candidate") or {}
            source = candidate.get("source_execution_task_id")
            if source_execution_task_id and source != source_execution_task_id:
                continue
            add_node(_node(task_id, "auto_fix_candidate", status=event.get("status"), label="Auto Fix Candidate", metadata={"failure_kind": candidate.get("failure_kind"), "strategy": candidate.get("candidate_strategy"), "confidence": candidate.get("confidence"), "raw_diff_stored": False, "raw_outputs_stored": False}))
            add_edge(_edge(candidate.get("replan_task_id"), task_id, "creates_auto_fix_candidate"))

        elif name == "review_required" and payload.get("review_type") == "sandbox_patch_generation":
            plan = payload.get("plan") or {}
            source = plan.get("source_execution_task_id")
            if source_execution_task_id and source != source_execution_task_id:
                continue
            add_node(_node(task_id, "patch_generation_review", status=event.get("status"), label="Patch Generation Review", metadata={"failure_kind": plan.get("failure_kind"), "strategy": plan.get("candidate_strategy"), "confidence": plan.get("confidence"), "raw_diff_stored": False, "execute_automatically": False}))
            add_edge(_edge(plan.get("candidate_task_id"), task_id, "creates_patch_generation_review"))

        elif name == "sandbox_patch_generation_linked_to_github_diff_review":
            source = payload.get("source_execution_task_id")
            if source_execution_task_id and source != source_execution_task_id:
                continue
            github_task_id = payload.get("github_diff_review_task_id") or task_id
            add_node(_node(github_task_id, "github_diff_review", status=event.get("status"), label="GitHub Diff Review", metadata={"failure_kind": payload.get("failure_kind"), "source_task_id": payload.get("source_task_id"), "diff_size_bytes": payload.get("diff_size_bytes"), "changed_file_count": payload.get("changed_file_count"), "raw_diff_stored": False, "execute_automatically": False}))
            add_edge(_edge(payload.get("patch_generation_task_id"), github_task_id, "creates_github_diff_review"))

        elif name == "sandbox_diff_review_draft_created":
            draft = payload.get("draft") or {}
            source = draft.get("source_execution_task_id")
            if source_execution_task_id and source != source_execution_task_id:
                continue
            add_node(_node(task_id, "diff_review_draft", status=event.get("status"), label="Diff Review Draft", metadata={"failure_kind": draft.get("failure_kind"), "target_api": draft.get("target_api"), "raw_diff_stored": False, "execute_automatically": False}))
            add_edge(_edge(draft.get("candidate_task_id"), task_id, "creates_diff_review_draft"))

        elif name == "sandbox_diff_review_draft_linked_to_github_diff_review":
            source = payload.get("source_execution_task_id")
            if source_execution_task_id and source != source_execution_task_id:
                continue
            github_task_id = payload.get("github_diff_review_task_id") or task_id
            add_node(_node(github_task_id, "github_diff_review", status=event.get("status"), label="GitHub Diff Review", metadata={"failure_kind": payload.get("failure_kind"), "source_task_id": payload.get("source_task_id"), "diff_size_bytes": payload.get("diff_size_bytes"), "changed_file_count": payload.get("changed_file_count"), "raw_diff_stored": False, "execute_automatically": False}))
            add_edge(_edge(payload.get("draft_task_id"), github_task_id, "creates_github_diff_review"))

    node_values = list(nodes.values())[:max(1, limit)]
    allowed_ids = {node["id"] for node in node_values}
    edge_values = [edge for edge in edges if edge["source"] in allowed_ids and edge["target"] in allowed_ids]
    by_kind: dict[str, int] = {}
    for node in node_values:
        by_kind[node["kind"]] = by_kind.get(node["kind"], 0) + 1

    return {
        "ok": True,
        "metadata_only": True,
        "source_execution_task_id": source_execution_task_id,
        "counts": {"nodes": len(node_values), "edges": len(edge_values), **by_kind},
        "nodes": node_values,
        "edges": edge_values,
        "raw_diff_stored": False,
        "raw_outputs_stored": False,
        "execute_automatically": False,
    }
