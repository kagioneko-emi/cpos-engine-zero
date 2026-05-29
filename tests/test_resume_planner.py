import json
import subprocess
import sys
from pathlib import Path

from cpos.promotion_executor import approve_execution_review, create_execution_review
from cpos.resume_planner import build_next_action_proposals, create_resume_proposal_review, pending_resume_reviews, approve_resume_review
from tests.test_promotion_executor import approved_promotion
from cpos.task_tape import TaskTapeStore


def ready_execution(tmp_path):
    manager, promotion = approved_promotion(tmp_path)
    store = TaskTapeStore(tmp_path / 'tasks.jsonl', tmp_path / 'checkpoints.jsonl')
    created = create_execution_review(manager, store, promotion.pointer_id)
    approve_execution_review(store, created['task_id'])
    return store, created['task_id']


def test_resume_planner_creates_and_approves_review(tmp_path):
    store, task_id = ready_execution(tmp_path)
    plan = build_next_action_proposals(store, task_id)
    assert plan['ok'] is True
    assert plan['proposal']['execute_automatically'] is False
    assert plan['proposal']['proposals'][0]['action_id'] == 'inspect_promotion_plan'

    created = create_resume_proposal_review(store, task_id)
    assert created['ok'] is True
    assert pending_resume_reviews(store)[0]['task_id'] == task_id
    approved = approve_resume_review(store, task_id, action_id='inspect_promotion_plan')
    assert approved['ok'] is True
    assert approved['approved_action_id'] == 'inspect_promotion_plan'
    assert pending_resume_reviews(store) == []
    assert any(e.event == 'resume_action_ready' for e in store.events())


def test_resume_planner_cli(tmp_path):
    store, task_id = ready_execution(tmp_path)
    root = Path(__file__).resolve().parents[1]
    common = ['--task-tape-path', str(tmp_path / 'tasks.jsonl'), '--task-checkpoint-path', str(tmp_path / 'checkpoints.jsonl')]
    planned = subprocess.run([sys.executable, '-m', 'cpos.resume_planner', *common, 'plan', task_id], cwd=str(root), check=True, capture_output=True, text=True)
    assert json.loads(planned.stdout)['ok'] is True
    created = subprocess.run([sys.executable, '-m', 'cpos.resume_planner', *common, 'create-review', task_id], cwd=str(root), check=True, capture_output=True, text=True)
    assert json.loads(created.stdout)['ok'] is True
