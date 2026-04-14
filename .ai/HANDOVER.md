# Observer Rock Handover

## Purpose

This is the fast handoff entrypoint for a new chat or agent session.
It complements:

- `.ai/IMPLEMENTATION_ROADMAP.md`
- `.ai/TASK_BACKLOG.md`

Read this file first.

## Current Status

`P2` is complete in the current tree.
`P3` is started and now has a real first operator-facing slice plus broad CLI
and workspace-validation coverage.

The project now has a full foundation plus the first real upstream
source-to-analysis slice:

- typed config loading for `services.yml`, `analysis_profiles.yml`, and `monitors.yml`
- workspace composition with cross-file validation
- typed run domain model with status and timestamp invariants
- run use cases plus a thin `RunService`
- SQLite-backed persistent run repository
- `MonitorExecutionService` as the main orchestration seam
- concrete monitor payload builders for:
  - `MonitorSnapshot`
  - `MonitorAnalysisPlan`
  - `MonitorDefinition`
  - `MonitorExecutionPlan`
  - `MonitorSourceData`
  - `MonitorAnalysis`
- typed document domain via `DocumentRecord` and `DocumentRepository`
- SQLite-backed persistent document repository
- typed artifact persistence via `ArtifactRef` and `ArtifactStore`
- filesystem-backed artifact storage at deterministic document/version paths
- analysis plugin protocol in `src/observer_rock/plugins/analysis.py`
- source plugin protocol in `src/observer_rock/plugins/source.py`
- `PluginRegistry` support for both analysis and source plugins
- analysis plugin execution through `MonitorExecutionService.execute_monitor_analysis(...)`
- source fetch + normalization through `MonitorExecutionService.execute_monitor_source(...)`
- persisted monitor artifacts for:
  - snapshot
  - analysis plan
  - definition
  - execution plan
  - source data
  - analysis output
- read-side loading of the latest persisted monitor source data through
  `MonitorSourceArtifactReader.load_latest(...)`
- read-side loading of the latest persisted monitor analysis output through
  `MonitorAnalysisArtifactReader.load_latest(...)`
- analysis execution from latest persisted source data through
  `MonitorExecutionService.execute_monitor_analysis_artifact_from_latest_source_data(...)`
- one canonical source-to-analysis workflow through
  `MonitorExecutionService.execute_monitor_source_to_analysis_artifacts(...)`
- one minimal operator-facing CLI for running that canonical workflow
- config-driven loading of built-in and external plugin modules
- broad regression and failure-path coverage around CLI, workspace validation,
  plugin loading, and persisted artifact read-side behavior
- maintained roadmap and backlog

## What Exists Today

There is now a minimal operator-facing CLI surface:

- `observer_rock.cli.main(...)`
- `python -m observer_rock run-monitor <monitor-id>`

The current CLI can execute the canonical source-to-analysis workflow for a
named monitor using the current working directory as the default workspace.
It also maps operator-facing configuration failures to clean usage errors,
including unknown monitor ids, missing workspace config files, invalid YAML,
workspace validation failures, and invalid configured plugin import modules.

Current command surface:

- `python -m observer_rock run-monitor <monitor-id>`

Current runtime defaults:

- workspace default: current working directory
- runtime state root: `<workspace>/.observer_rock/`
- run database: `<workspace>/.observer_rock/runs.db`
- document database: `<workspace>/.observer_rock/documents.db`
- artifacts root: `<workspace>/.observer_rock/artifacts/`

### Config and workspace

The workspace loads typed services, analysis profiles, and monitors, then
validates cross-file references between profiles, services, and monitor
analyses.

`services.yml` may also define a top-level `plugin_import_paths:` list next to
`services:`. Those entries are Python module import paths, not file paths, for
example:

```yaml
plugin_import_paths:
  - external_analysis_plugin
services:
  openai_strong:
    plugin: openai
```

The runtime loads built-ins first, then each configured module before monitor
execution. External plugin modules must be importable in the runtime environment
and expose a callable `register_plugins(registry)` entrypoint that registers one
or more source and/or analysis plugins on `PluginRegistry`.

In Docker or other autonomous deployments, ship the plugin package inside the
image or mount it into the container and make its parent directory importable
via installation or `PYTHONPATH`; the config should still reference the module
name, not a host-local file path.

The CLI/runtime also temporarily adds the workspace directory to `sys.path`
before loading configured plugin modules, so workspace-local plugin packages
can be used in addition to installed packages.

### Run layer

`RunService.execute_run(...)` wraps lifecycle transitions and returns a
structured `RunExecutionResult` with `run`, `outcome`, `value`, and `error`.

### Monitor layer

`MonitorExecutionService` can:

- resolve a monitor by id from `WorkspaceConfig`
- execute monitor-scoped work inside the run lifecycle
- build snapshot, analysis-plan, definition, and execution-plan payloads
- fetch and normalize source data via registered source plugins
- execute configured analysis plugins and pass normalized source data to them
- persist source data and analysis outputs as versioned JSON artifacts
- read the latest persisted source data and use it for analysis
- run one canonical source-to-analysis workflow that persists both steps in order
- validate referenced analysis plugin names when a `PluginRegistry` is supplied

The canonical source-to-analysis path now keeps the in-memory source result
available for the analysis step instead of immediately reloading that freshly
written source artifact from disk. That behavior matters because one recent CLI
coverage slice exposed a real gap there.

### Persistence layer

`SqliteRunRepository` persists run records.
`SqliteDocumentRepository` persists versioned `DocumentRecord` rows keyed by
`(document_id, version)`.
`FilesystemArtifactStore` writes bytes to:

- `<root>/<document_id>/v<version>/<artifact_name>`

and returns typed `ArtifactRef` metadata.

Current monitor document ids:

- `<monitor_id>-snapshot`
- `<monitor_id>-analysis-plan`
- `<monitor_id>-definition`
- `<monitor_id>-execution-plan`
- `<monitor_id>-source-data`
- `<monitor_id>-analysis-output`

## What Does Not Exist Yet

- no broader CLI surface beyond the current minimal monitor runner
- no scheduler
- no packaged concrete production plugins beyond built-ins/test-focused modules
- no rendering pipeline
- no notifier pipeline
- no Docker/example plugin package walkthrough
- no broader operator-facing end-to-end flow beyond the current monitor runner

## Verification State

Recent slices added broad unit/component coverage for source execution,
source artifact persistence, source read-side loading, persisted-source-driven
analysis, the canonical source-to-analysis workflow, CLI execution,
workspace-validation failures, plugin-loading failures, plugin runtime
failures, and persisted artifact read-side behavior after both success and
partial failure.

Known green checks from the latest work:

- `tests/unit/plugins/test_registry.py` passes
- `tests/unit/cli/test_run_monitor.py` passes
- `tests/unit/cli/test_run_monitor_cli.py` passes
- `tests/unit/cli/test_module_entrypoint_smoke.py` passes
- `tests/unit/cli/test_module_entrypoint_run_monitor.py` passes
- `tests/unit/cli/test_module_run_monitor_subprocess.py` passes
- `tests/unit/test_monitor_execution_service_analysis.py` passes
- `tests/unit/test_monitor_execution_service_source.py` passes
- `tests/component/application/test_monitor_execution_service_sqlite.py -k source_to_analysis_workflow -p no:cacheprovider` passes
- `tests/component/application/test_monitor_execution_service_sqlite.py -k persisted_source_data -p no:cacheprovider` passes
- `tests/component/application/test_monitor_execution_service_sqlite.py -k source_artifact_document_versions -p no:cacheprovider` passes
- fresh full suite passes:
  - `python -m pytest tests -q -p no:cacheprovider`
  - result: `145 passed, 2 warnings`
- current trace-based line coverage over `src/observer_rock` is approximately
  `96.51%` (`1301/1348` lines)
- lowest current project files by line coverage are:
  - `src/observer_rock/config/loader.py` (`72.31%`)
  - `src/observer_rock/application/artifacts.py` (`87.50%`)
  - `src/observer_rock/cli/__init__.py` (`89.09%`)
- focused combined verification around source/analysis seams passes:
  - `pytest tests/unit/test_monitor_execution_service_source.py tests/unit/test_monitor_execution_service_analysis.py tests/unit/plugins/test_registry.py tests/component/application/test_monitor_execution_service_sqlite.py -k "source_to_analysis_workflow or persisted_source_data or source_data or source_artifact or analysis_output_artifact or loads_latest or executes_analysis" -q -p no:cacheprovider`
- local Windows temp-path ACL issues are still worked around by the workspace-local
  `tmp_path` fixture in `tests/conftest.py`
- Windows path-length issues still exist when tests create very long `tmp_path`
  names, so keep new CLI test names short
- module-entrypoint tests currently emit this warning and it is known, not new:
  - `RuntimeWarning: 'observer_rock.__main__' found in sys.modules ...`

## Files To Read Next

If you are a new chat, read these in order:

1. `.ai/HANDOVER.md`
2. `.ai/IMPLEMENTATION_ROADMAP.md`
3. `.ai/TASK_BACKLOG.md`
4. `src/observer_rock/config/workspace.py`
5. `src/observer_rock/application/services.py`
6. `src/observer_rock/application/documents.py`
7. `src/observer_rock/application/artifacts.py`
8. `src/observer_rock/plugins/registry.py`
9. `src/observer_rock/plugins/source.py`
10. `src/observer_rock/plugins/analysis.py`
11. `src/observer_rock/application/monitoring.py`
12. `src/observer_rock/infrastructure/sqlite.py`
13. `src/observer_rock/infrastructure/artifacts.py`
14. `tests/unit/test_monitor_execution_service_source.py`
15. `tests/unit/test_monitor_execution_service_analysis.py`
16. `tests/unit/cli/test_run_monitor.py`
17. `tests/unit/cli/test_run_monitor_cli.py`
18. `tests/unit/cli/test_module_run_monitor_subprocess.py`
19. `tests/component/application/test_monitor_execution_service_sqlite.py`
20. `tests/conftest.py`

## Project Structure So Far

Key source files:

- `src/observer_rock/config/models.py`
- `src/observer_rock/config/loader.py`
- `src/observer_rock/config/workspace.py`
- `src/observer_rock/application/repositories.py`
- `src/observer_rock/application/use_cases.py`
- `src/observer_rock/application/services.py`
- `src/observer_rock/application/documents.py`
- `src/observer_rock/application/artifacts.py`
- `src/observer_rock/application/monitoring.py`
- `src/observer_rock/infrastructure/sqlite.py`
- `src/observer_rock/infrastructure/artifacts.py`
- `src/observer_rock/cli/__init__.py`
- `src/observer_rock/cli/runtime.py`
- `src/observer_rock/plugins/analysis.py`
- `src/observer_rock/plugins/builtin.py`
- `src/observer_rock/plugins/source.py`
- `src/observer_rock/plugins/registry.py`
- `tests/conftest.py`

Key test files:

- `tests/unit/cli/test_run_monitor.py`
- `tests/unit/cli/test_run_monitor_cli.py`
- `tests/unit/cli/test_module_entrypoint_smoke.py`
- `tests/unit/cli/test_module_entrypoint_run_monitor.py`
- `tests/unit/cli/test_module_run_monitor_subprocess.py`
- `tests/unit/test_monitor_execution_service_source.py`
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

Source and analysis now follow the same persistence contract as the earlier
planning payloads.

### 6. Source and analysis are still intentionally plugin-driven and narrow

The project now has explicit source and analysis plugin seams, but they remain
minimal by design:

- source plugins fetch raw payloads
- `MonitorExecutionService` normalizes them into `MonitorSourceData`
- analysis plugins receive normalized `source_data`
- outputs remain generic serializable objects

Do not over-generalize these protocols until there is real pressure from a
second concrete implementation.

### 7. Persisted read-side seams now exist for both upstream and downstream data

There are dedicated readers for:

- latest persisted source input: `MonitorSourceArtifactReader`
- latest persisted analysis output: `MonitorAnalysisArtifactReader`

The code now supports both:

- live source fetch -> analysis
- persisted source read -> analysis

### 8. There is now one canonical application-level source-to-analysis workflow

`MonitorExecutionService.execute_monitor_source_to_analysis_artifacts(...)`
is the clearest current "official" path for a monitor execution slice.

If a future chat needs one default workflow to build on, use this method rather
than re-assembling ad hoc source/analysis calls.

### 9. The CLI now validates the whole workspace before executing one monitor

`run-monitor <monitor-id>` does not validate only the chosen monitor.
The workspace is loaded and cross-file validated first, so a structural or
reference problem in another monitor can still block the run. This is now
explicitly covered by regression tests and should not surprise a future chat.

### 10. Operator-facing config/plugin failures should map to exit code 2

The current CLI contract is:

- usage/config/plugin loading errors => exit code `2`
- execution/runtime failures after a run actually starts => exit code `1`

Do not casually blur those paths in future work; the tests now depend on them.

## What A New Chat Should Not Redo

Do not spend another long stretch on:

- config-only polish
- persistence-only seams already covered by tests
- reopening `P2` slices that are now done
- re-litigating whether source/analysis belong in `P2`

The project already has:

- config composition
- run persistence
- document persistence
- artifact persistence
- monitor planning payloads
- source plugin registration, execution, normalization, and persistence
- read-side loading for latest persisted source data
- analysis plugin registration, execution, persistence, and read-side loading
- analysis execution from persisted source data
- a canonical source-to-analysis workflow

Do not reopen `P2-057` through `P2-062` unless a failing test exposes a real regression.

## Recommended Next Direction

The next work is still `P3`, but the very first CLI slice is already done.

The remaining meaningful directions are productization layers above the current
application seams, for example:

- broadening the CLI surface beyond `run-monitor`
- scheduler-triggered monitor execution
- packaged concrete production plugin implementations
- rendering/notifier pipeline
- Docker/example plugin packaging guidance
- a more operator-facing end-to-end workflow

If you need one pragmatic starting point for the next chat, prefer this order now:

1. decide the next operator-facing workflow beyond a single ad hoc `run-monitor`
2. add the smallest scheduler or broader CLI slice for that workflow
3. only then widen plugin implementations or downstream delivery features

## Suggested Next P3 Slice

The most sensible next slice is likely one of these, in this order:

1. add a scheduler-triggered execution slice that reuses the existing canonical
   monitor workflow
2. package one real built-in plugin or example external plugin distribution that
   proves the `plugin_import_paths` deployment story
3. broaden the CLI surface only if there is a concrete operator workflow to expose

Why this is the best next move:

- the minimal one-shot CLI already exists
- the next uncertainty is operationalization, not internal orchestration
- the plugin/deployment story now matters more than another internal seam
- scheduler or packaged-plugin work would validate whether the current surface is
  actually usable outside tests

## Working Rules For The Next Chat

1. Keep using TDD.
2. Prefer one behavior per task.
3. Use `apply_patch` for edits.
4. Update `.ai/TASK_BACKLOG.md` after real progress.
5. Treat immediately-passing new tests as regression coverage and say so.
6. Ignore unrelated edits from other contributors unless they directly block your file.
7. Treat `P2` as closed unless a regression test proves otherwise.
8. If you report coverage, note whether it came from `coverage.py` or the
   standard-library `trace` fallback; the current environment only has the
   latter installed.
