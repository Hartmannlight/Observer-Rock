# File Digest Example

This example runs one complete local Observer Rock slice:

- read records from `input/feed.json`
- summarize them with the built-in analysis path
- render a digest
- write the notification payload to `output/digest.txt`

If you want to see budgeted recent-document rechecks in action, use
`examples/indexed_file_watch` instead. That example separates discovery from
document fetches and uses the new `change_tracking` window.

## Run It

From the repository root:

To create a fresh workspace with the same starter pattern elsewhere:

```powershell
python -m observer_rock init-workspace --workspace my-workspace
```

Inspect the workspace first:

```powershell
python -m observer_rock validate-workspace --workspace examples/file_digest --tick 2026-03-14T12:05:00+00:00
python -m observer_rock list-monitors --workspace examples/file_digest --tick 2026-03-14T12:05:00+00:00
```

Expected validation output:

```text
Workspace VALID root=.../examples/file_digest tick=2026-03-14T12:05:00+00:00
Summary plugin_imports=0 services=2 analysis_profiles=1 monitors=1
service local_model plugin=noop_model token_source=none path=none
service local_output plugin=file_notifier token_source=none path=.../examples/file_digest/output/digest.txt
analysis-profile digest_v1 plugin=builtin_summary model_service=local_model
monitor local-file-digest due=DUE schedule='*/5 * * * *' source=builtin_json_file source_path=.../examples/file_digest/input/feed.json analyses=digest_v1 outputs=digest_v1->builtin_digest->local_output
```

Expected listing output:

```text
python -m observer_rock list-monitors --workspace examples/file_digest --tick 2026-03-14T12:05:00+00:00
Configured monitors (1) at 2026-03-14T12:05:00+00:00
local-file-digest DUE schedule='*/5 * * * *' source=builtin_json_file analyses=digest_v1 outputs=digest_v1->builtin_digest->local_output
```

Run one monitor directly:

```powershell
python -m observer_rock run-monitor local-file-digest --workspace examples/file_digest
```

Inspect the stored history for one indexed document:

```powershell
python -m observer_rock document-history --workspace examples/file_digest --document local-file-digest:meeting-2026-03-14 --profile digest_v1
```

Expected success output:

```text
local-file-digest COMPLETED source=local-file-digest-source-data@v1 analysis=local-file-digest-analysis-output@v1 notifications=local-file-digest-notifications@v1 artifacts=examples/file_digest/.observer_rock/artifacts
```

Expected side effects:

- `examples/file_digest/output/digest.txt` contains the rendered digest
- `examples/file_digest/.observer_rock/artifacts/` contains persisted source, analysis, and notification artifacts
- `examples/file_digest/.observer_rock/runs.db` and `documents.db` contain run metadata

To evaluate schedules instead of running one monitor directly:

```powershell
python -m observer_rock run-scheduler --workspace examples/file_digest --tick 2026-03-14T12:05:00+00:00
```

Expected scheduler output:

```text
local-file-digest COMPLETED source=local-file-digest-source-data@v1 analysis=local-file-digest-analysis-output@v1 notifications=local-file-digest-notifications@v1 artifacts=examples/file_digest/.observer_rock/artifacts
Scheduler summary tick=2026-03-14T12:05:00+00:00 configured=1 due=1 completed=1
```

## Config Layout

- `services.yml`: output and model services
- `analysis_profiles.yml`: reusable analysis profile definitions
- `monitors.yml`: monitor schedule, source, analyses, and outputs

## Budgeted Rechecks

For real remote sources, a monitor can limit how aggressively it rechecks older
documents for changes:

```yaml
change_tracking:
  recheck_recent_documents: 20
  recheck_budget_per_run: 2
  recheck_every_n_runs: 6
```

This means Observer Rock keeps only the latest `20` known documents in the
recheck window, schedules at most `2` of them per recheck pass, and only does
that pass every `6`th run. The goal is to keep change detection incremental and
fair-use-friendly instead of reloading whole histories on every schedule tick.

The example is intentionally local-only:

- `local_model` uses `noop_model`
- `local_output` uses `file_notifier`
- no external API keys are required

## Secrets

Real notifier or model services can resolve secrets from environment variables.
The service config pattern is:

```yaml
services:
  discord_alerts:
    plugin: discord
    token_env: DISCORD_TOKEN
    channel_id: "12345"
```

Set the environment variable before running Observer Rock. Do not commit raw
tokens into `services.yml`.

## Troubleshooting

Common operator-facing failures already have direct CLI error messages:

- missing `services.yml`
- missing `analysis_profiles.yml` when a monitor declares analyses
- invalid YAML in `services.yml`, `analysis_profiles.yml`, or `monitors.yml`
- unknown monitor id
- plugin import or registration failures from `plugin_import_paths`
- missing service references in `analysis_profiles.yml`
- missing analysis profile references in `monitors.yml`
- missing environment secrets referenced by `token_env`

If a monitor fails during runtime, Observer Rock keeps partial state when that
is useful for debugging:

- source artifacts may exist even if analysis fails
- analysis artifacts are only persisted after analysis completes
- notification artifacts are only persisted after output delivery completes
