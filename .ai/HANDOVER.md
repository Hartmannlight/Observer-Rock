# Observer Rock Handover

## Purpose

This is the fast handoff entrypoint for a new chat or agent session.
It complements:

- `.ai/IMPLEMENTATION_ROADMAP.md`
- `.ai/TASK_BACKLOG.md`

Read this file first.

## Current Status

The project is still in the foundation phase, but it now has a broader
application and persistence base than the previous handoff described.

What exists today:

- typed config loading for `services.yml`, `analysis_profiles.yml`, and `monitors.yml`
- workspace composition with cross-file validation
- typed run domain model with status and timestamp invariants
- run use cases plus a thin `RunService`
- SQLite-backed persistent run repository
- first monitor orchestration in `MonitorExecutionService`
- concrete monitor payload builders for:
  - `MonitorSnapshot`
  - `MonitorAnalysisPlan`
  - `MonitorDefinition`
  - `MonitorExecutionPlan`
- typed document domain via `DocumentRecord` and `DocumentRepository`
- SQLite-backed persistent document repository
- typed artifact persistence via `ArtifactRef` and `ArtifactStore`
- filesystem-backed artifact storage at deterministic document/version paths
- persisted monitor payload artifacts for:
  - snapshot
  - analysis plan
  - definition
  - execution plan
- minimal analysis plugin protocol in `src/observer_rock/plugins/analysis.py`
- minimal `PluginRegistry` for analysis plugin registration and lookup
- analysis plugin name validation inside `MonitorExecutionService` when building analysis plans
- minimal analysis plugin execution through `MonitorExecutionService.execute_monitor_analysis(...)`
- persisted monitor analysis output artifacts through `MonitorExecutionService.execute_monitor_analysis_artifact(...)`
- read-side loading of the latest persisted monitor analysis output through `MonitorAnalysisArtifactReader.load_latest(...)`
- backlog items `P2-055` and `P2-056` completed
- maintained roadmap and backlog

What does not exist yet:

- no CLI
- no scheduler
- no source/fetch/normalize plugin implementations
- no rendering or notifier pipeline
- no end-to-end monitor execution pipeline beyond config/planning plus minimal analysis execution/artifact persistence

Verification state:

- recent slices added unit/component coverage for documents, artifact storage,
  plugin registry, and persisted monitor artifacts
- `tests/unit/plugins/test_registry.py` passes
- `tests/unit/test_monitor_execution_service_analysis.py` passes
- `tests/component/application/test_monitor_execution_service_sqlite.py -k analysis_output_artifact -p no:cacheprovider` passes
- `tests/component/application/test_monitor_execution_service_sqlite.py::test_reader_loads_latest_persisted_monitor_analysis_output -p no:cacheprovider` passes
- `tests/unit -p no:cacheprovider` passes
- `tests/component -p no:cacheprovider` passes
- `tests -p no:cacheprovider` passed in the last recorded full run
- `P2-055` is done; the initial unit entrypoint passed immediately as regression
  coverage, and focused component coverage exists for persisted analysis output
- `P2-056` is done; the project now has focused component coverage for reading
  the latest persisted analysis output through the new read-side workflow
- local Windows temp-path ACL issues are worked around by the workspace-local
  `tmp_path` fixture in `tests/conftest.py`

## Files To Read Next

If you are a new chat, read these in order:

1. `.ai/HANDOVER.md`
2. `.ai/IMPLEMENTATION_ROADMAP.md`
3. `.ai/TASK_BACKLOG.md`
4. `src/observer_rock/config/workspace.py`
5. `src/observer_rock/application/documents.py`
6. `src/observer_rock/application/artifacts.py`
7. `src/observer_rock/plugins/registry.py`
8. `src/observer_rock/plugins/analysis.py`
9. `src/observer_rock/application/services.py`
10. `src/observer_rock/application/monitoring.py`
11. `src/observer_rock/infrastructure/sqlite.py`
12. `src/observer_rock/infrastructure/artifacts.py`
13. `tests/unit/test_monitor_execution_service_analysis.py`
14. `tests/conftest.py`
15. `tests/component\application\test_monitor_execution_service_sqlite.py`

## Project Structure So Far

Key source files:

- `src/observer_rock/config/models.py`
- `src/observer_rock/config/workspace.py`
- `src/observer_rock/application/repositories.py`
- `src/observer_rock/application/use_cases.py`
- `src/observer_rock/application/services.py`
- `src/observer_rock/application/documents.py`
- `src/observer_rock/application/artifacts.py`
- `src/observer_rock/application/monitoring.py`
- `src/observer_rock/infrastructure/sqlite.py`
- `src/observer_rock/infrastructure/artifacts.py`
- `src/observer_rock/plugins/analysis.py`
- `src/observer_rock/plugins/registry.py`
- `tests/conftest.py`

Key test files:

- `tests/unit/test_monitor_execution_service_analysis.py`
- `tests/unit/application/test_document_record_invariants.py`
- `tests/unit/config/test_workspace_loader.py`
- `tests/unit/plugins/test_registry.py`
- `tests/unit/test_project_docs.py`
- `tests/component/application/test_sqlite_run_repository.py`
- `tests/component/application/test_sqlite_document_repository.py`
- `tests/component/application/test_filesystem_artifact_store.py`
- `tests/component/application/test_monitor_execution_service_sqlite.py`

## Important Design Decisions Already Made

### 1. Foundation before MVP

The current code is reusable foundation, not throwaway scaffolding.
The project deliberately built typed config, contracts, orchestration seams,
and persistence before user-facing delivery flows.

### 2. Cross-file validation belongs in workspace composition

Per-file schema rules stay in config models/loaders.
Cross-file checks stay in `src/observer_rock/config/workspace.py`.

### 3. Keep use cases and services thin

Use cases remain the main application behavior seam.
`RunService` and `MonitorExecutionService` compose them; they should not absorb
unnecessary business logic.

### 4. Persistence seams are explicit and split by concern

- runs persist through `RunRepository` / `SqliteRunRepository`
- documents persist through `DocumentRepository` / `SqliteDocumentRepository`
- artifacts persist through `ArtifactStore` / `FilesystemArtifactStore`

Do not collapse document metadata and artifact bytes into one adapter.

### 5. Monitor artifact persistence is versioned by document id

Each persisted monitor payload creates or advances a document version and writes
one JSON artifact under that versioned document path.

Current document ids:

- `<monitor_id>-snapshot`
- `<monitor_id>-analysis-plan`
- `<monitor_id>-definition`
- `<monitor_id>-execution-plan`

### 6. Plugin registry now supports the first real analysis execution slice

`PluginRegistry` supports registering and resolving analysis plugins by name.
`MonitorExecutionService` still uses it for early validation while building
analysis plans, and now also for the minimal execution workflow that invokes
registered analysis plugins per configured monitor analysis.
The slice is intentionally narrow: plugin outputs are generic serializable
objects, and there is still no broader source/fetch/normalize pipeline.

### 7. Persisted analysis output now has a dedicated read-side seam

`MonitorAnalysisArtifactReader` is the first downstream consumer for persisted
analysis output. It resolves the latest version of
`<monitor_id>-analysis-output`, loads `monitor_analysis.json` from the artifact
store, and deserializes it back into typed `MonitorAnalysis` data.

## Current Behavior Snapshot

### Config and workspace

The workspace loads typed services, analysis profiles, and monitors, then
validates cross-file references between profiles, services, and monitor
analyses.

### Run layer

`RunService.execute_run(...)` wraps lifecycle transitions and returns a
structured `RunExecutionResult` with `run`, `outcome`, `value`, and `error`.

### Monitor layer

`MonitorExecutionService` can:

- resolve a monitor by id from `WorkspaceConfig`
- execute monitor-scoped work inside the run lifecycle
- build snapshot, analysis-plan, definition, and execution-plan payloads
- execute configured analysis plugins and return typed `MonitorAnalysis` outputs
- persist each of those payloads as a versioned JSON artifact
- validate referenced analysis plugin names when a `PluginRegistry` is supplied

Current accepted state:

- `src/observer_rock/application/monitoring.py` contains the minimal analysis
  execution, analysis artifact, and latest-analysis read-side workflows
- the focused unit entrypoint lives in
  `tests/unit/test_monitor_execution_service_analysis.py`
- focused component coverage exists for persisted analysis output in
  `tests/component/application/test_monitor_execution_service_sqlite.py`
- `tests/conftest.py` keeps temp-backed tests inside the workspace so the suite
  no longer depends on writable user-temp directories on this Windows setup

Unknown monitors still fail clearly.
Unknown analysis plugins become failed monitor executions with the underlying
`KeyError` captured in the execution result.

### Persistence layer

`SqliteRunRepository` persists run records.
`SqliteDocumentRepository` persists versioned `DocumentRecord` rows keyed by
`(document_id, version)`.
`FilesystemArtifactStore` writes bytes to:

- `<root>/<document_id>/v<version>/<artifact_name>`

and returns typed `ArtifactRef` metadata.

## What A New Chat Should Not Redo

Do not spend another long stretch on config-only polish or more persistence-only
seams unless a failing test exposes a real gap.

The project already has:

- config composition
- run persistence
- document persistence
- artifact persistence
- monitor planning payloads
- minimal analysis plugin registration, validation, execution, artifact persistence,
  and latest persisted-analysis read-side loading

Do not reopen `P2-055` or `P2-056` unless a failing test exposes a real
regression in the minimal analysis execution/persistence/read-side behavior.

## Recommended Next Direction

The next sensible focus is the first real source/fetch/normalize plugin path.

The application now covers config composition, run/document/artifact
persistence, monitor planning, minimal analysis execution, and a read-side
consumer for persisted analysis output. The clearest remaining gap is upstream:
introduce one concrete source/fetch/normalize workflow that produces monitor
input before analysis runs.

That next slice should stay narrow:

- one explicit source or fetch plugin contract
- one concrete normalization step
- focused unit/component coverage through the existing monitor execution seams

## Working Rules For The Next Chat

1. Keep using TDD.
2. Prefer one behavior per task.
3. Use `apply_patch` for edits.
4. Update `.ai/TASK_BACKLOG.md` after real progress.
5. Treat immediately-passing new tests as regression coverage and say so.
6. Ignore unrelated edits from other contributors unless they directly block your file.
