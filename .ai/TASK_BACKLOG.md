# Observer Rock Task Backlog

Template reminder for new items:

- Title: `PX-000 Short task name`
- Status: todo
- Priority: P0
- Depends on: none
- Touches: `src/...`, `tests/...`
- Why: one sentence explaining why this slice matters
- First failing test: `path/to/test.py::test_name`
- Test scope: unit | component | e2e
- Expected red signal: expected failing behavior before implementation
- Minimal production change: smallest code/doc change that should make it pass
- Acceptance criteria:
  - one observable outcome per line
- Verification commands:
  - `uv run pytest path/to/test.py -q`
- Completion notes:
  - short summary after the slice is done

## Now

No active item is curated here right now. Add a new slice only after writing the
first failing test and copying the template fields above.

## Next

No queued slice is intentionally committed here yet. Use this section only for
the next few unstarted items that are still genuinely pending.

## Later

Capture only genuinely deferred work here. Good candidates based on the current
tree are:

- add `tests/contracts/` once plugin behavior needs reusable contract suites
- add `tests/e2e/` only after a stable operator-facing workflow exists
- add `src/observer_rock/cli/` when there is a concrete command surface to test
- reconsider a separate `domain/` package only if pure business types start
  crowding `application/`

## Done

- P0-001 Create package skeleton
- P0-002 Create persistent roadmap and backlog
- P1-001 Load minimal services config
- P1-002 Compose workspace config from typed slices
- P1-003 Load minimal analysis profile config
- P1-004 Compose workspace config with services and analysis profiles
- P1-005 Load minimal monitors config
- P1-006 Compose workspace config with services, analysis profiles, and monitors
- P1-007 Add optional analyses to monitor definitions
- P1-008 Raise a clear workspace error when services.yml is missing
- P1-009 Validate monitor analysis profile references during workspace composition
- P1-010 Require analysis_profiles.yml when monitors declare analyses
- P1-011 Validate monitor analysis references only when analyses are declared
- P1-012 Reject duplicate monitor ids in monitors.yml
- P1-013 Reject blank monitor ids
- P1-014 Reject negative analysis profile retries
- P1-015 Reject blank analysis profile model_service values
- P1-016 Validate analysis profile model_service references during workspace composition
- P1-017 Reject blank service plugins
- P1-018 Reject blank monitor schedules
- P1-019 Reject blank monitor source plugins
- P1-020 Reject blank analysis profile plugins explicitly in tests
- P1-021 Reject duplicate analysis profile references within one monitor
- P1-022 Reject blank monitor analysis profiles
- P1-023 Validate analysis profile plugins via explicit non-empty service-style constraints
- P1-024 Keep workspace composition strict about analysis profile service references
- P1-025 Add non-empty constraints for service, monitor, and source plugin names
- P1-026 Add non-empty constraints for monitor schedules and ids
- P1-027 Reject blank optional prompt/schema references in analysis profiles
- P1-028 Reject blank optional service environment and channel references
- P1-029 Reject blank output_schema values explicitly in tests
- P1-030 Review regression-only items for possible backlog closure
- P2-001 Define repository contracts with in-memory fakes
- P2-002 Start run use case against a repository contract
- P2-003 Add monitor_id to started runs
- P2-004 Add a run lookup use case over the repository contract
- P2-005 Add a finish_run use case that transitions status
- P2-006 Add a list-runs contract to the in-memory repository
- P2-007 Add a failing-path test for finish_run on unknown run IDs
- P2-008 Add a list-runs use case over the repository contract
- P2-009 Add a status-filtered list-runs use case
- P2-010 Reject duplicate run ids on repository create
- P2-011 Add a monitor-filtered list-runs use case
- P2-012 Expose finish_run unknown-run behavior only as regression coverage
- P2-013 Add get_latest_run_for_monitor as a read-side use case
- P2-014 Keep list_runs ordering while filtering by monitor_id
- P2-015 Keep repository create() distinct from save() semantics
- P2-016 Add a combined status+monitor filter test for list_runs
- P2-017 Add count_runs as a filtered read-side use case
- P2-018 Extend get_latest_run_for_monitor with optional status filtering
- P2-019 Add monitor-aware get_run filtering
- P2-020 Add count_runs over the existing filtered list path
- P2-021 Extend get_latest_run_for_monitor with optional status filtering
- P2-022 Separate create/save semantics in the in-memory repository
- P2-023 Introduce a typed RunStatus for run records
- P2-024 Add has_run as a boolean read-side use case
- P2-025 Add terminal-state semantics to RunStatus
- P2-026 Separate regression coverage from implementation work for open lifecycle items
- P2-027 Add an explicit boolean existence use case over get_run
- P2-028 Add transition semantics to RunStatus
- P2-029 Normalize RunRecord status values to RunStatus at construction time
- P2-031 Add a SQLite-backed persistent run repository
- P2-032 Add a failed terminal state and fail_run use case
- P2-033 Add basic lifecycle timestamps to RunRecord
- P2-034 Add a thin RunService orchestration shell over run use cases
- P2-035 Add a first execute_run workflow on RunService
- P2-036 Make RunService workflow timestamps deterministic via an injectable clock
- P2-037 Enforce basic status/timestamp invariants in RunRecord
- P2-038 Return structured RunExecutionResult values from RunService.execute_run
- P2-039 Add a first MonitorExecutionService over WorkspaceConfig and RunService
- P2-040 Return structured MonitorExecutionResult values from MonitorExecutionService
- P2-041 Add a first concrete MonitorSnapshot payload and workflow
- P2-042 Add a concrete MonitorAnalysisPlan payload and workflow
- P2-043 Add an aggregated MonitorDefinition payload and workflow
- P2-044 Add a concrete MonitorExecutionPlan payload and workflow
- P2-045 Add a typed Document domain model and repository contract
- P2-046 Add a SQLite-backed persistent document repository
- P2-047 Add a first filesystem-backed artifact store
- P2-048 Persist a monitor snapshot artifact through MonitorExecutionService
- P2-049 Prove repeated monitor snapshot artifact executions advance document versions
- P2-050 Persist a monitor execution plan artifact through MonitorExecutionService
- P2-051 Persist a monitor definition artifact through MonitorExecutionService
- P2-052 Persist a monitor analysis plan artifact through MonitorExecutionService
- P2-053 Add the first minimal plugin registry slice
- P2-054 Validate monitor analysis plugins through PluginRegistry
- P2-055 Execute a minimal analysis plugin through MonitorExecutionService
- P2-056 Add a first downstream consumer for persisted monitor analysis output
