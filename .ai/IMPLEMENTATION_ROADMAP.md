# Observer Rock Implementation Roadmap

## Summary

Observer Rock is currently a small Python package for typed workspace config,
run/document persistence, artifact storage, and monitor-analysis orchestration.
The codebase should continue to grow in small TDD-sized slices so future agents
can keep changes safe and localized.

## Architecture Overview

- Current package layout under `src/observer_rock/`:
  - `application/` for use cases, orchestration services, repository contracts,
    document/artifact abstractions, and test helpers
  - `config/` for typed config models plus workspace and YAML loading
  - `infrastructure/` for SQLite and filesystem-backed adapters
  - `plugins/` for the current analysis-plugin seam and registry
- Planned but not yet present in `src/observer_rock/`:
  - `cli/` for operator-facing commands
  - any separate `domain/` package if pure business types outgrow
    `application/`
  - broader plugin families such as source, fetch, render, or notify plugins

## TDD Workflow

1. Write one failing test for one behavior.
2. Run the focused test and verify the expected failure.
3. Write the smallest change that makes the test pass.
4. Re-run the focused test and then the relevant suite.
5. Refactor only after green.
6. Update backlog status and notes before ending the session.

## Test Architecture

- Current test layout under `tests/`:
  - `unit/` for config, plugin, and application behavior
  - `component/` for SQLite/filesystem-backed integration slices
  - `conftest.py` for shared fixtures
- Planned but not yet present:
  - `contracts/` for plugin contract suites
  - `e2e/` for a minimal end-to-end monitor run

Prefer in-memory fakes over mocks. Keep transport and I/O boundaries thin.

## Package Boundaries For Testability

- business logic must not live in CLI commands
- renderers format data but do not send it
- notifiers send rendered payloads but do not decide business rules
- repositories are interface-first and replaceable with fakes
- config validation must run without booting the application

## Agent Workflow

1. Read this roadmap.
2. Read `.ai/TASK_BACKLOG.md`.
3. Pick the highest-priority unblocked task.
4. Implement it with a red-green-refactor cycle.
5. Run the listed verification commands.
6. Update task state and notes.
7. Add follow-up tasks if new work appears.

## Milestones

### Milestone 0

Repository foundation, test tooling, roadmap, and backlog. Completed.

### Milestone 1

Typed config loading and workspace composition. Completed.

### Milestone 2

Application services, SQLite persistence, artifact storage, and the first
plugin-backed monitor analysis slices. In progress in the current tree.

### Milestone 3

Broaden monitor orchestration, plugin contracts, and read-side workflows without
breaking the current package boundaries.

### Milestone 4

Add still-missing planned areas such as CLI entrypoints, contract suites, and a
minimal end-to-end slice when the current seams stabilize.

## Definition Of Done

A task is done only when:

- the relevant test started red and ended green
- the focused suite passes
- code and docs are updated together
- no hidden architecture decision is left inside the task

## Open Risks

- `application/` currently carries some domain-style records; splitting a
  dedicated `domain/` package too early would add churn without clear benefit
- `plugins/` is intentionally narrow today; new plugin families should not be
  documented as existing until package directories and tests are present
- local temp and cache artifacts are already accumulating in the repo root, so
  hygiene depends on keeping ignore rules aligned with the tools in use
