# Observer Rock Handover

Start here when opening a new chat or agent session.

## Read Order

1. `.ai/STATUS.md`
2. `.ai/DELIVERY_PLAN.md`
3. `.ai/TASK_BACKLOG.md`
4. `src/observer_rock/cli/runtime.py`
5. `src/observer_rock/application/monitoring.py`

## Current Product State

Observer Rock already has the framework foundation:

- typed workspace config loading and cross-file validation
- SQLite-backed run and document persistence
- filesystem-backed artifact storage
- source and analysis plugin protocols plus registry loading
- canonical source-to-analysis execution path
- operator-facing CLI commands:
  - `python -m observer_rock run-monitor <monitor-id>`
  - `python -m observer_rock run-scheduler`

The project is not done yet. The main missing value is a full operator slice
with one real example source, a renderer, a notifier, and one stable e2e flow.

## Working Rules

- Favor one delivery package per session, not one micro-task per session.
- Keep TDD, but write tests for a coherent slice instead of one invariant at a time.
- Avoid broad repo scans. Do not recursively inspect `.venv`, `.git`,
  `test_tmp`, or `.observer_rock` unless the task explicitly requires it.
- Full test suite runs happen at the end of a delivery package, not after every
  tiny edit.

## Why This File Is Short

The project previously spent too much context on handover material and
micro-backlog bookkeeping. This file now points to the two live project docs:

- `.ai/STATUS.md` for current reality
- `.ai/DELIVERY_PLAN.md` for the next delivery steps
