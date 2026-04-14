# Observer Rock Status

## Current Reality

Observer Rock has a working framework core:

- typed loading for `services.yml`, `analysis_profiles.yml`, and `monitors.yml`
- cross-file workspace validation
- SQLite-backed run and document persistence
- filesystem-backed artifact storage
- plugin registry support for source and analysis plugins
- source-to-analysis execution through `MonitorExecutionService`
- operator-facing CLI commands:
  - `python -m observer_rock init-workspace --workspace <path>`
  - `python -m observer_rock validate-workspace`
  - `python -m observer_rock list-monitors`
  - `python -m observer_rock run-monitor <monitor-id>`
  - `python -m observer_rock run-scheduler`
  - `python -m observer_rock inspect-artifacts <monitor-id>`
  - `python -m observer_rock query-documents --profile <profile> --contains <text>`
  - `python -m observer_rock document-history --document <document-id> --profile <profile>`
- renderer and notifier plugin seams
- built-in vertical-slice plugins:
  - `builtin_json_file`
  - `builtin_summary`
  - `builtin_digest`
  - `file_notifier`
- runnable example workspace under `examples/file_digest`

## Verified State

- unit and component coverage around config loading, plugin loading, monitor
  execution, CLI behavior, workspace scaffolding, workspace validation, and persistence
- end-to-end coverage for the example file-digest workspace
- end-to-end coverage for `init-workspace -> validate-workspace -> list-monitors -> run-monitor`
- temporary test directories now clean themselves up through `tests/conftest.py`

## What Is Still Missing

- richer renderer and notifier options beyond the first working path
- richer query semantics beyond the first profile/text lookup
- broader document identity heuristics beyond explicit identity and title fallback
- rule-driven decisions on top of stored document history and analyses
- source-specific sparse revalidation plugins that actively use the new
  change-tracking fetch context beyond the first built-in indexed-file source

## Hardening Progress

Runtime observability has started:

- `run-monitor` now emits stage-level lifecycle output for workspace load, run start,
  source, analysis, notifications, and run completion
- runtime failures now carry explicit stage information for source, analysis, and
  notification paths
- `run-scheduler` now emits scheduler start and summary lines alongside per-monitor
  lifecycle output
- `run-scheduler` now shows which configured monitors were due or skipped for
  the evaluated tick
- analysis profiles now honor `retries` during monitor execution
- notifier services now honor `retries` during delivery attempts
- `inspect-artifacts` now exposes the latest persisted source, analysis, and
  notification artifacts for one monitor and reports missing or broken stages
- successful monitor runs now index source records as queryable documents with
  content-version tracking
- source records can now provide a stable `document_identity` separate from a
  changing technical `source_id`
- when explicit document identity is absent, indexing now falls back to `title`
  before using the raw `source_id`
- `query-documents` now returns the first archive-style retrieval path over
  persisted analysis projections
- `query-documents` now supports monitor-scoped lookup and latest-versus-history
  retrieval modes
- `query-documents` now renders readable excerpts instead of raw analysis JSON
- `document-history` now exposes version history for one stored document and
  compares the latest version against the previous one
- monitors can now declare budgeted recent-document change tracking via:
  - `recheck_recent_documents`
  - `recheck_budget_per_run`
  - `recheck_every_n_runs`
- runtime now persists per-monitor change-tracking state and passes source
  plugins an optional `fetch_context` with the current recheck plan
- built-in `builtin_indexed_file` now uses that `fetch_context` by separating
  cheap index discovery from selective document downloads

## Architectural Position

The core framework now includes one complete vertical slice plus the first
document-intelligence retrieval path and first document-history comparison path.
The next work should stay delivery-oriented:

1. build change-aware decisions on top of the new sparse revalidation path
2. then broaden source integrations beyond the first built-in indexed-file source
3. only then broaden abstractions or integrations again
