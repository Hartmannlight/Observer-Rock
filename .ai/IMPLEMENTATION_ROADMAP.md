# Observer Rock Implementation Roadmap

## Summary

Observer Rock now has a stable framework base plus a minimal operator CLI. The
next phase is not more foundation work. The next phase is to finish one usable
end-to-end monitoring slice quickly without dropping test discipline.

## Architecture Overview

- current package layout under `src/observer_rock/`:
  - `application/` for orchestration services and domain-style records
  - `config/` for typed config models and YAML loading
  - `infrastructure/` for SQLite and filesystem-backed adapters
  - `plugins/` for source and analysis plugin seams
  - `cli/` for operator-facing commands
- planned but not yet present in a usable form:
  - renderer support
  - notifier support
  - one stable example workspace and e2e slice
  - packaged production-facing plugins beyond test-focused built-ins

## TDD Workflow

1. Define one delivery slice with visible operator value.
2. Write the smallest useful set of failing tests for that slice.
3. Implement the full slice end-to-end.
4. Run the focused suite for that slice.
5. Run the full suite once before closing the package.
6. Update status, plan, and backlog only at package boundaries.

## Test Architecture

- current test layout under `tests/`:
  - `unit/` for config, plugin, and application behavior
  - `component/` for SQLite/filesystem-backed integration slices
  - `conftest.py` for shared fixtures and workspace-local temp paths
- planned but not yet present:
  - `e2e/` for a minimal end-to-end monitor run

Prefer in-memory fakes over mocks. Keep I/O boundaries thin.

## Delivery Workflow

1. Read `.ai/STATUS.md` and `.ai/DELIVERY_PLAN.md`.
2. Pick one unblocked delivery package from `.ai/TASK_BACKLOG.md`.
3. Stay on that package until it is implemented, tested, and documented.
4. Ask the user only when blocked by a real product decision or an external dependency.
5. Use subagents only for independent side work, not for the main architecture path.

## Milestones

### Milestone 0

Repository foundation, test tooling, roadmap, and backlog. Completed.

### Milestone 1

Typed config loading and workspace composition. Completed.

### Milestone 2

Application services, SQLite persistence, artifact storage, and the first
plugin-backed monitor analysis slices. Completed.

### Milestone 3

Operator-facing CLI surface for monitor execution and scheduler ticks.
Substantially complete in the current tree.

### Milestone 4

Finish one vertical operator slice:

- one example source
- one renderer
- one notifier
- one example workspace
- one stable end-to-end test

## Definition Of Done

A delivery package is done only when:

- the relevant slice-level tests started red and ended green
- the focused suite passes
- the full suite passes before merge or push
- code and docs are updated together
- the package leaves the project closer to a usable product, not only a cleaner abstraction

## Open Risks

- the framework can still consume time without shipping user-visible value if
  work returns to abstraction-first slicing
- temp and cache artifacts can still pollute local analysis if cleanup discipline
  regresses
