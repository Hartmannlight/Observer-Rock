# Observer Rock

Observer Rock is a plugin-based document monitoring and analysis framework with
an operator-first CLI. The current tree includes one complete vertical slice:

- fetch source records
- run one analysis profile
- render a notification payload
- persist source, analysis, and notification artifacts
- exercise the flow end to end with the local `examples/file_digest` workspace

## Current CLI

- `python -m observer_rock init-workspace --workspace <path>`
- `python -m observer_rock validate-workspace --workspace <path>`
- `python -m observer_rock list-monitors --workspace <path>`
- `python -m observer_rock run-monitor <monitor-id> --workspace <path>`
- `python -m observer_rock run-scheduler --workspace <path> [--tick <iso-timestamp>]`
- `python -m observer_rock inspect-artifacts <monitor-id> --workspace <path>`
- `python -m observer_rock query-documents --workspace <path> --profile <profile> --contains <text>`
- `python -m observer_rock document-history --workspace <path> --document <document-id> --profile <profile>`

## Recommended Operator Flow

Use the example workspace as the reference path:

```powershell
python -m observer_rock init-workspace --workspace my-workspace
python -m observer_rock validate-workspace --workspace examples/file_digest --tick 2026-03-14T12:05:00+00:00
python -m observer_rock list-monitors --workspace examples/file_digest --tick 2026-03-14T12:05:00+00:00
python -m observer_rock run-monitor local-file-digest --workspace examples/file_digest
python -m observer_rock inspect-artifacts local-file-digest --workspace examples/file_digest
python -m observer_rock query-documents --workspace examples/file_digest --profile digest_v1 --contains meeting-2026-03-14
python -m observer_rock document-history --workspace examples/file_digest --document local-file-digest:meeting-2026-03-14 --profile digest_v1
python -m observer_rock run-scheduler --workspace examples/file_digest --tick 2026-03-14T12:05:00+00:00
```

`init-workspace` creates a runnable starter workspace with one monitor, starter
input data, local file output, and a workspace-local README.

`validate-workspace` checks that configuration loads, cross-file references are
valid, required secrets are present, and relative paths resolve as expected.

`list-monitors` shows the configured monitors and whether each one is due for a
given scheduler tick.

`run-monitor` executes one monitor and prints the persisted source, analysis,
and notification document versions plus the artifact root.

`inspect-artifacts` prints the latest persisted source, analysis, and
notification artifacts for one monitor and reports whether each stage is
available, missing, or broken.

`query-documents` searches the first document-intelligence index built from
persisted analysis results and returns matching indexed documents for one
analysis profile and text filter. It supports `--monitor` to scope the search
to one monitor and `--all-versions` to include document history instead of only
the latest version.

`document-history` shows the stored versions for one indexed document and
compares the newest version with the previous one.

`run-scheduler` executes all due monitors for a tick and prints per-monitor
results, the due or skipped decision for every configured monitor, plus a
scheduler summary.

## Example Workspace

The first real operator slice lives in `examples/file_digest`. See
`examples/file_digest/README.md` for the concrete walkthrough.

For a more realistic discovery-plus-recheck pattern, see
`examples/indexed_file_watch/README.md`.

For starting a new workspace quickly, prefer `init-workspace` instead of
copying example files by hand.

It uses only built-in local plugins:

- `builtin_json_file` as the source
- `builtin_indexed_file` as an index-plus-document source with budgeted rechecks
- `builtin_summary` as the analysis
- `builtin_digest` as the renderer
- `file_notifier` as the notifier

No external API keys are required for that example.

## Workspace Files

- `services.yml` defines service plugins and secret references such as `token_env`
- `analysis_profiles.yml` defines reusable analysis profiles
- `monitors.yml` defines schedules, source plugins, analyses, and outputs
- `.observer_rock/` stores runtime state, persisted documents, and artifacts

## Change Tracking

Observer Rock now supports a budgeted recent-document recheck policy on each
monitor. This is designed for sources where full historical refetches would be
too expensive or would violate fair-use expectations.

Example:

```yaml
monitors:
  - id: council-watch
    schedule: "*/30 * * * *"
    source:
      plugin: website_source
    change_tracking:
      recheck_recent_documents: 20
      recheck_budget_per_run: 2
      recheck_every_n_runs: 6
```

Meaning:

- only the last `20` known documents remain in the recheck window
- only `2` of those documents are scheduled for recheck at a time
- rechecks only happen every `6`th monitor run

The scheduler persists a small local cursor in `.observer_rock/documents.db`
and rotates through the configured recent-document window instead of reloading
all recent documents in one burst.

Source plugins can opt into this policy by accepting the optional
`fetch_context` keyword argument on `fetch()`. The context includes:

- `run_iteration`
- `recheck_enabled`
- `recheck_document_ids`
- `recent_documents`

Plugins that do not accept `fetch_context` continue to work unchanged.

The built-in `builtin_indexed_file` source is the first concrete source that
uses this contract. It reads a cheap index file every run, fetches only unseen
documents from the configured discovery window, and adds the scheduled
`recheck_document_ids` from the recent-document budget.

Source plugins may optionally emit `document_identity` and `title` on source
records. Observer Rock uses `document_identity` as the stable document key when
present. If explicit identity is missing, it falls back to `title` before using
the technical `source_id`. That lets one real-world document survive changing
feed entries or URLs more often than a source-id-only strategy.

## Secrets

Secrets should be referenced by environment variable, not committed inline.

Example:

```yaml
services:
  discord_alerts:
    plugin: discord
    token_env: DISCORD_TOKEN
    channel_id: "12345"
```

If a required secret is missing, the CLI exits with a configuration error before
runtime execution begins.
