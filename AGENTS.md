# Observer Rock Agent Guide

## Start Here

When starting a new chat or agent session, read only these files first:

1. `.ai/HANDOVER.md`
2. `.ai/STATUS.md`
3. `.ai/DELIVERY_PLAN.md`
4. `.ai/TASK_BACKLOG.md`

Then read only the code files needed for the current delivery package.

## Working Style

- Work in delivery packages, not micro-tasks.
- Keep TDD, but apply it to a coherent slice of user-visible value.
- Do not stop after every tiny green test. Finish the current package or a meaningful sub-slice first.
- Ask the user only when blocked by a real product decision, missing external access, or conflicting requirements.
- Prefer one main agent on the critical path. Use subagents only for clearly separate side work.

## Context Discipline

- Do not broadly scan the whole repository unless necessary.
- Avoid recursive inspection of `.git`, `.venv`, `test_tmp`, `.observer_rock`, and cache directories.
- Prefer targeted reads of the specific files relevant to the current task.
- Keep project documentation short and live. Do not create sprawling handover notes.

## Documentation Rules

The live project docs are:

- `.ai/HANDOVER.md`
- `.ai/STATUS.md`
- `.ai/DELIVERY_PLAN.md`
- `.ai/TASK_BACKLOG.md`
- `.ai/IMPLEMENTATION_ROADMAP.md`

Rules for updating them:

- Update them only when a delivery package materially changes project reality, priorities, or working method.
- Do not append endless session logs.
- Prefer replacing outdated text over adding more text.
- Keep each file compact and high-signal.
- If no meaningful project state changed, leave the docs alone.

## Current Direction

- The next planned package is `D3 Improve operator usability`.
- The first real vertical slice already exists:
  - source
  - analysis
  - renderer
  - notifier
  - example workspace
  - e2e coverage
- Near-term work should improve operator experience, docs, and runtime clarity before expanding abstractions again.

## Verification

- Run focused tests during implementation.
- Run the full suite before closing a delivery package.
- Keep the workspace clean of temporary artifacts when practical.
