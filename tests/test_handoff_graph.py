from cpos.handoff_graph import build_handoff_graph
from cpos.handoff_inbox import approve_handoff
from cpos.handoff_promotion import create_promotion_pointer
from cpos.pointer_os import PointerManager
from cpos.promotion_executor import approve_execution_review, create_execution_review
from cpos.resume_planner import create_resume_proposal_review
from cpos.task_tape import TaskTapeStore
from tests.test_handoff_inbox import create_handoff
from tests.test_promotion_executor import approved_promotion


def test_build_handoff_graph_links_handoff_to_resume(tmp_path):
    manager = PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl")
    handoff = create_handoff(manager)
    approve_handoff(manager, handoff.pointer_id, reviewer="Tester")
    promotion = create_promotion_pointer(manager, handoff.pointer_id, reviewer="Promoter")
    store = TaskTapeStore(tmp_path / "tasks.jsonl", tmp_path / "checkpoints.jsonl")
    execution = create_execution_review(manager, store, promotion.pointer_id)
    approve_execution_review(store, execution["task_id"])
    create_resume_proposal_review(store, execution["task_id"])

    graph = build_handoff_graph(manager, store)

    assert graph["ok"] is True
    assert graph["counts"]["handoffs"] == 1
    assert graph["counts"]["promotions"] == 1
    assert graph["counts"]["execution_reviews"] == 1
    assert graph["counts"]["resume_reviews"] == 1
    assert graph["handoffs"][0]["pointer_id"] == handoff.pointer_id
    assert graph["handoffs"][0]["promotions"][0]["pointer_id"] == promotion.pointer_id
    assert graph["execution_reviews"][0]["promotion_pointer_id"] == promotion.pointer_id
    assert graph["resume_reviews"][0]["task_id"] == execution["task_id"]

    filtered = build_handoff_graph(manager, store, source_pointer_id=handoff.pointer_id)
    assert filtered["counts"]["handoffs"] == 1
    assert filtered["counts"]["promotions"] == 1


def test_build_handoff_graph_filters_by_review_status(tmp_path):
    manager = PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl")
    pending = create_handoff(manager, "ptr://handoff/pending")
    approved = create_handoff(manager, "ptr://handoff/approved")
    approve_handoff(manager, approved.pointer_id, reviewer="Tester")
    create_promotion_pointer(manager, approved.pointer_id, reviewer="Promoter")
    store = TaskTapeStore(tmp_path / "tasks.jsonl", tmp_path / "checkpoints.jsonl")

    graph = build_handoff_graph(manager, store, review_status="approved")

    assert graph["review_status"] == "approved"
    assert graph["counts"]["handoffs"] == 1
    assert graph["handoffs"][0]["pointer_id"] == approved.pointer_id
    assert graph["counts"]["promotions"] == 1


def test_handoff_graph_includes_detail_safe_metadata(tmp_path):
    manager, promotion = approved_promotion(tmp_path)
    store = TaskTapeStore(tmp_path / "tasks.jsonl", tmp_path / "checkpoints.jsonl")
    execution = create_execution_review(manager, store, promotion.pointer_id)
    approve_execution_review(store, execution["task_id"])
    create_resume_proposal_review(store, execution["task_id"])

    graph = build_handoff_graph(manager, store)

    promo = graph["handoffs"][0]["promotions"][0]
    assert "blocked_inputs" in promo
    assert "guardrails" in promo
    execution_row = graph["execution_reviews"][0]
    assert "blocked_inputs" in execution_row
    resume_row = graph["resume_reviews"][0]
    assert "first_action_title" in resume_row
    assert resume_row["execute_automatically"] is False
