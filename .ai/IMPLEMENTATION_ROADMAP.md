# Observer Rock Implementation Roadmap

## Summary

Observer Rock now has a stable framework base plus a minimal operator CLI. The
project should not spend its next phase only on more CLI hardening. The next
phase is to finish the first slice just enough for trust, then return to the
original product direction: a document-monitoring system with stored,
queryable, structured knowledge.

## Architecture Overview

- current package layout under `src/observer_rock/`:
  - `application/` for orchestration services and domain-style records
  - `config/` for typed config models and YAML loading
  - `infrastructure/` for SQLite and filesystem-backed adapters
  - `plugins/` for source and analysis plugin seams
  - `cli/` for operator-facing commands
- already present in the first slice:
  - renderer support
  - notifier support
  - one stable example workspace and e2e slice
- still missing as product capabilities:
  - stable document identity and content version behavior
  - first-class retrieval of persisted analyses and artifacts
  - explicit rule evaluation over structured results
  - a query-facing service layer for archive and search use cases
  - validation through a second real source

## TDD Workflow

1. Define one delivery slice with visible operator value.
2. Write the smallest useful set of failing tests for that slice.
3. Implement the full slice end-to-end.
4. Run the focused suite for that slice.
5. Run the full suite once before closing the package.
6. Update status, plan, and backlog only at package boundaries.

## Test Architecture

- current test layout under `tests/`:
  - `unit/` for config, plugin, and application behavior
  - `component/` for SQLite/filesystem-backed integration slices
  - `conftest.py` for shared fixtures and workspace-local temp paths
- already present:
  - `e2e/` for a minimal end-to-end monitor run
- should grow next with the product direction:
  - query and archive retrieval slices
  - version-change and re-analysis slices
  - multi-output decision slices over one stored analysis result

Prefer in-memory fakes over mocks. Keep I/O boundaries thin.

## Delivery Workflow

1. Read `.ai/STATUS.md` and `.ai/DELIVERY_PLAN.md`.
2. Pick one unblocked delivery package from `.ai/TASK_BACKLOG.md`.
3. Stay on that package until it is implemented, tested, and documented.
4. Ask the user only when blocked by a real product decision or an external dependency.
5. Use subagents only for independent side work, not for the main architecture path.

## Milestones

### Milestone 0

Repository foundation, test tooling, roadmap, and backlog. Completed.

### Milestone 1

Typed config loading and workspace composition. Completed.

### Milestone 2

Application services, SQLite persistence, artifact storage, and the first
plugin-backed monitor analysis slices. Completed.

### Milestone 3

Operator-facing CLI surface for monitor execution and scheduler ticks.
Substantially complete in the current tree.

### Milestone 4

Finish one vertical operator slice and make it trustworthy in practice:

- artifact inspection
- scheduler ergonomics
- runtime observability
- retry boundaries

Current status: complete in the current tree.

### Milestone 5

Introduce document intelligence and archive retrieval:

- stable document identity
- content-version detection
- structured analysis persistence for retrieval
- first query/search workflow over stored results

Recommended delivery shape for this milestone:

- add the smallest useful retrieval path first instead of a broad search layer
- prefer one clear operator question, for example "show documents where analysis
  X found topic Y", over a generic query language
- keep the first access path CLI-driven if that is the fastest route to a real
  archive workflow

Suggested implementation focus inside the milestone:

- domain records for document identity and document version boundaries
- repository queries that can load documents, versions, and analysis results
- one application service that translates stored analysis data into a usable
  archive/query response
- one CLI command that exposes that service for operators

Tests that should define this milestone:

- unit tests for identity and version classification rules
- component tests for persisted retrieval of document and analysis records
- e2e or high-level CLI coverage for the first archive query workflow

Concrete first slice for this milestone:

- operator question:
  "show documents where analysis profile `<profile>` contains text `<term>`"
- first operator path:
  `python -m observer_rock query-documents --profile <profile> --contains <term>`
- first supported workspace:
  the existing `examples/file_digest` workspace after at least one successful
  monitor run

Why this is the right first slice:

- it proves retrieval from stored analysis results instead of another run path
- it stays narrow enough to ship as one package without inventing a query
  language
- it works with the current built-in summary shape, where analysis outputs store
  per-record text under `items[].summary`

Required design correction inside this slice:

- the current persistence model versions monitor artifacts such as
  `<monitor-id>-analysis-output`, but does not yet model real document identity
- Package 5 must introduce a document-level identity that survives across runs
  and can group repeated observations of the same source record
- content-version detection should decide whether a source record produces a new
  document version or maps to an existing one

Suggested execution order inside Package 5:

1. introduce document identity and version records for observed source items
2. persist source-to-document mappings during monitor execution
3. persist analysis results attached to document identity and version, not only
   to monitor-run artifacts
4. add repository retrieval queries for document plus analysis lookup
5. expose the first archive command in the CLI
6. cover the new path with focused unit, component, and CLI-level tests

Current status:

- the first archive command now exists as
  `python -m observer_rock query-documents --profile <profile> --contains <text>`
- successful monitor runs now index queryable document records and projected
  analysis text
- the remaining Package 5 work is to improve identity quality and retrieval
  depth beyond the first source-record-based slice

### Milestone 6

Turn structured analysis into product decisions:

- explicit rule evaluation
- multiple outputs from one analysis result
- stronger renderer and notifier separation

### Milestone 7

Validate the architecture with a second real integration:

- second source with minimal new core code
- evidence that the current seams generalize

### Milestone 8

Prepare a product access layer:

- document, analysis, run, and search services
- later CLI query, API, or MCP exposure on top of those services

## Definition Of Done

A delivery package is done only when:

- the relevant slice-level tests started red and ended green
- the focused suite passes
- the full suite passes before merge or push
- code and docs are updated together
- the package leaves the project closer to a usable product, not only a cleaner abstraction

## Open Risks

- the project can still lose its original product direction if work remains too
  focused on CLI ergonomics and runtime polish
- the framework can still consume time without shipping user-visible value if
  work returns to abstraction-first slicing instead of document intelligence
- temp and cache artifacts can still pollute local analysis if cleanup discipline
  regresses
