# Observer Rock Handover

Start here when opening a new chat or agent session.

## Read Order

1. `.ai/STATUS.md`
2. `.ai/DELIVERY_PLAN.md`
3. `.ai/TASK_BACKLOG.md`
4. `src/observer_rock/application/document_intelligence.py`
5. `src/observer_rock/infrastructure/sqlite.py`
6. `src/observer_rock/cli/runtime.py`
7. `src/observer_rock/cli/__init__.py`
8. `src/observer_rock/application/monitoring.py`
9. `src/observer_rock/plugins/builtin.py`
10. `examples/indexed_file_watch/README.md`

## Current Product State

Observer Rock now has:

- typed workspace config loading and cross-file validation
- SQLite-backed run and document persistence
- filesystem-backed artifact storage
- source and analysis plugin protocols plus registry loading
- canonical source-to-analysis execution path
- first robust operator hardening for runtime inspection and scheduler visibility
- operator-facing CLI commands:
  - `python -m observer_rock init-workspace --workspace <path>`
  - `python -m observer_rock validate-workspace`
  - `python -m observer_rock list-monitors`
  - `python -m observer_rock run-monitor <monitor-id>`
  - `python -m observer_rock run-scheduler`
  - `python -m observer_rock inspect-artifacts <monitor-id>`
  - `python -m observer_rock query-documents --profile <profile> --contains <text>`
  - `python -m observer_rock document-history --document <document-id> --profile <profile>`
- runnable example workspace under `examples/file_digest`
- runtime observability for monitor and scheduler execution
- retry boundaries for analysis profiles and notifier services
- artifact inspection for the latest persisted source, analysis, and notification outputs
- first document-intelligence indexing and archive query path over persisted analyses
- indexed document versions based on source content changes
- document identity priority:
  - explicit `document_identity`
  - fallback `title`
  - fallback technical `source_id`
- `query-documents` now supports:
  - monitor scoping
  - latest-only results by default
  - optional all-version history
  - readable excerpts for matches instead of only raw JSON
- `document-history` now supports:
  - per-document version history by analysis profile
  - latest-versus-previous comparison for source and analysis text
- monitors can now define budgeted recent-document rechecks and source plugins
  can consume an optional `fetch_context` to avoid broad historical reloads
- built-in `builtin_indexed_file` is the first source that actually uses that
  `fetch_context` to separate index discovery from selective document downloads

## Product Direction

Do not treat Observer Rock as "a better run-monitor CLI".

The actual product target is:

- a document-monitoring system
- that stores structured, queryable knowledge about observed documents
- and can later drive multiple downstream decisions, outputs, and integrations

The core question for upcoming work is not "can the monitor run?" but:

- can the system track the same real-world document over time?
- can it retrieve meaningful knowledge from stored analyses?
- can later rule/output layers build on that stored knowledge cleanly?

## Immediate Next Work

The project is in `D5 Document intelligence and queryability`.

The next real gaps are:

- stronger document identity and version semantics
- change-aware decisions on top of the new sparse revalidation contract
- then broader source integrations and rule-driven outputs on top of stored results

The best next slice is not more CLI surface polish. It is one of these:

1. improve retrieval quality from stored analyses
2. improve identity/version quality for sources with weak metadata

Recommended next slice:

- use the new indexed-file source to prove one change-aware operator decision
- keep it tied to one concrete operator question instead of inventing a broad rule system first

Concrete recommendation for the next chat:

- build one explicit decision path on top of `builtin_indexed_file`
- good first target:
  notify only for newly discovered documents and for rechecked documents whose
  content version actually changed
- avoid broad rule engines or multiple policy types in that slice

## Guardrails

- Stay in delivery packages, not micro-fixes.
- Do not drift back into scheduler/CLI polish unless it directly unlocks product value.
- Avoid abstraction-first work. The point of `D5` is product proof through retrieval.
- Keep the big picture visible:
  Observer Rock should become a searchable, document-centered monitoring knowledge layer, not only a framework with a demo CLI.

## Working Rules

- Favor one delivery package per session, not one micro-task per session.
- Keep TDD, but write tests for a coherent slice instead of one invariant at a time.
- Avoid broad repo scans. Do not recursively inspect `.venv`, `.git`,
  `test_tmp`, or `.observer_rock` unless the task explicitly requires it.
- Full test suite runs happen at the end of a delivery package, not after every
  tiny edit.

## Why This File Is Short

The project previously spent too much context on handover material and
micro-backlog bookkeeping. This file now points to the two live project docs:

- `.ai/STATUS.md` for current reality
- `.ai/DELIVERY_PLAN.md` for the next delivery steps
