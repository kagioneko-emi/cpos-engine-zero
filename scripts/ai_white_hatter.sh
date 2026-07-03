#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-"$ROOT_DIR/.venv/bin/python"}"
HOST="${HOST:-127.0.0.1:8080}"
GOAL_STORE="${GOAL_STORE:-goals/goals.example.json}"
TASK_FILE="${TASK_FILE:-docs/AI_WHITE_HATTER_TASK.example.yaml}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

usage() {
  cat <<'EOF'
AI White-Hatter helper

Usage:
  scripts/ai_white_hatter.sh <command>

Commands:
  all         Run the full read-only workflow
  status      Read current world model and goal state
  validate    Validate the goal store and show summary
  compare     Inspect existing docs and compare stored templates
  review      Read local review queues from the CPOS HTTP API
  pipeline    Run the read-only evaluation/pointer pipeline
  demo        Read demo readiness from the CPOS HTTP API
  dashboard   Show dashboard-ready AI White-Hatter summary
  task <file> Read, validate, and summarize a task file (YAML or JSON)
  task-json   Emit machine-readable task output (use with task <file>)
  compare-task <left> <right> Compare two task files
  compare-many <base> [candidates...] Compare one task against many task files
  create-task <file> Create a new task scaffold
  clone-task <source> <file> Clone an existing task to a new file
  help        Show this help

Environment:
  PYTHON_BIN   Override Python interpreter (default: .venv/bin/python)
  GOAL_STORE   Goal store path (default: goals/goals.example.json)
  HOST         Local CPOS API host:port (default: 127.0.0.1:8080)
  TASK_FILE    Task file used by dashboard mode (default: docs/AI_WHITE_HATTER_TASK.example.yaml)
EOF
}

run_python() {
  (
    cd "$ROOT_DIR"
    PYTHONPATH=. "$PYTHON_BIN" "$@"
  )
}

cmd_status() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" status; }
cmd_validate() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" validate; }
cmd_compare() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" compare; }
cmd_review() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" review; }
cmd_pipeline() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" pipeline; }
cmd_demo() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" demo; }
cmd_dashboard() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" dashboard --task-file "$TASK_FILE"; }
cmd_task() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" task "$1"; }
cmd_task_json() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" task-json "$1"; }
cmd_compare_task() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" compare-task "$1" "$2"; }
cmd_compare_many() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" compare-many "$@"; }
cmd_create_task() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" create-task "$@"; }
cmd_clone_task() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" clone-task "$@"; }
cmd_all() { run_python -m cpos.ai_white_hatter --goal-store "$GOAL_STORE" --host "$HOST" all; }

main() {
  local cmd="${1:-help}"
  case "$cmd" in
    all)
      cmd_all
      ;;
    status)
      cmd_status
      ;;
    validate)
      cmd_validate
      ;;
    compare)
      cmd_compare
      ;;
    review)
      cmd_review
      ;;
    pipeline)
      cmd_pipeline
      ;;
    demo)
      cmd_demo
      ;;
    dashboard)
      cmd_dashboard
      ;;
    task)
      shift
      cmd_task "${1:-}"
      ;;
    task-json)
      shift
      cmd_task_json "${1:-}"
      ;;
    compare-task)
      shift
      left="${1:-}"
      shift || true
      right="${1:-}"
      cmd_compare_task "$left" "$right"
      ;;
    compare-many)
      shift
      base="${1:-}"
      shift || true
      cmd_compare_many "$base" "$@"
      ;;
    create-task)
      shift
      cmd_create_task "$@"
      ;;
    clone-task)
      shift
      cmd_clone_task "$@"
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
