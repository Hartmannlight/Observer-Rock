# Observer Rock Task Backlog

This backlog now tracks delivery packages instead of micro-invariants.

## Active

- `D1` Cleanup and delivery reset
  - Status: done
  - Scope: temp artifact hygiene, slimmer handover docs, ignore runtime state, remove obvious unused artifacts

- `D2` Stabilize one operator-facing vertical slice
  - Status: done
  - Scope: one example source plugin, one renderer, one notifier, one example workspace, one end-to-end test

## Next

- `D3` Improve operator usability
  - Status: implementation mostly done; closure pending
  - Scope: better CLI output, `list-monitors`, `validate-workspace`, `init-workspace`, clearer example config, setup notes, failure-path docs

- `D4` Production-hardening for the first slice
  - Status: in progress
  - Scope: runtime observability, retry boundaries, better scheduler ergonomics, artifact inspection helpers

## Later

- `D5` Plugin contract suite
  - Status: later
  - Scope: reusable tests for source, analysis, renderer, and notifier plugins once those seams stabilize

- `D6` Second real monitor integration
  - Status: later
  - Scope: prove the framework after the first vertical slice by adding a second source with minimal new core code

## Closed Foundation

- typed config and workspace composition
- run lifecycle and SQLite persistence
- document repository and artifact storage
- source and analysis plugin execution
- `run-monitor` CLI
- `run-scheduler` CLI tick and due-check behavior
