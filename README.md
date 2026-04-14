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

## Recommended Operator Flow

Use the example workspace as the reference path:

```powershell
python -m observer_rock init-workspace --workspace my-workspace
python -m observer_rock validate-workspace --workspace examples/file_digest --tick 2026-03-14T12:05:00+00:00
python -m observer_rock list-monitors --workspace examples/file_digest --tick 2026-03-14T12:05:00+00:00
python -m observer_rock run-monitor local-file-digest --workspace examples/file_digest
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

`run-scheduler` executes all due monitors for a tick and prints per-monitor
results plus a scheduler summary.

## Example Workspace

The first real operator slice lives in `examples/file_digest`. See
`examples/file_digest/README.md` for the concrete walkthrough.

For starting a new workspace quickly, prefer `init-workspace` instead of
copying example files by hand.

It uses only built-in local plugins:

- `builtin_json_file` as the source
- `builtin_summary` as the analysis
- `builtin_digest` as the renderer
- `file_notifier` as the notifier

No external API keys are required for that example.

## Workspace Files

- `services.yml` defines service plugins and secret references such as `token_env`
- `analysis_profiles.yml` defines reusable analysis profiles
- `monitors.yml` defines schedules, source plugins, analyses, and outputs
- `.observer_rock/` stores runtime state, persisted documents, and artifacts

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
