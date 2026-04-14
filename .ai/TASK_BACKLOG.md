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
  - Status: done
  - Scope: runtime observability, retry boundaries, better scheduler ergonomics, artifact inspection helpers

- `D5` Document intelligence and queryability
  - Status: in progress
  - Scope: document identity, content versioning, persist structured analysis results for retrieval, first archive/query workflow
  - Delivery shape: one coherent package that turns stored monitor output into a first real archive question-answering path
  - Target outcome: operators can retrieve knowledge from persisted analyses and inspect document history instead of only running monitors or reading raw artifacts
  - Current extension: budgeted recent-document rechecks for fair-use-friendly source monitoring
  - Current proof point: `builtin_indexed_file` uses discovery-plus-recheck fetch planning end to end

## Later

- `D6` Rule-driven outputs and audience routing
  - Status: later
  - Scope: explicit rule evaluation, multiple outputs from one analysis result, stronger renderer/notifier separation, multiple interest paths

- `D7` Second real monitor integration
  - Status: later
  - Scope: prove the framework after the first vertical slice by adding a second source with minimal new core code

- `D8` Product access layer
  - Status: later
  - Scope: document, analysis, run, and search services that can later back richer CLI queries, API, or MCP access

- `D9` Plugin contract suite
  - Status: later
  - Scope: reusable tests for source, analysis, renderer, and notifier plugins once those seams stabilize across more than one real integration

## Closed Foundation

- typed config and workspace composition
- run lifecycle and SQLite persistence
- document repository and artifact storage
- source and analysis plugin execution
- `run-monitor` CLI
- `run-scheduler` CLI tick and due-check behavior
