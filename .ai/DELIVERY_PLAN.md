# Observer Rock Delivery Plan

## Goal

Deliver Observer Rock as a document-monitoring product, not only as a runnable
CLI slice.

The near-term plan is:

1. finish the first slice until operators can trust it
2. move from run execution to an abfragbare document and analysis layer
3. prove that one stored analysis can drive multiple decisions and outputs
4. validate the architecture with a second real source

## Delivery Packages

### Package 1: Repo Hygiene And Context Control

Done in the current tree:

- runtime state is now ignored via `.gitignore`
- temporary test workspaces are cleaned automatically
- handover docs are reduced to a small live set
- the backlog tracks delivery packages instead of micro-tasks

### Package 2: First Vertical Operator Slice

Done in the current tree:

- one example source plugin
- one renderer
- one notifier
- one example workspace
- one e2e test that exercises the full path

### Package 3: Operator Usability

Implemented in the current tree:

- tighten CLI output for monitor and scheduler runs
- add workspace inspection via `list-monitors`
- add workspace preflight via `validate-workspace`
- add workspace scaffolding via `init-workspace`
- add example setup docs
- add root-level operator docs
- document failure modes and secrets

Remaining closure question:

- close Package 3 formally once Package 4 artifact inspection lands

### Package 4: First Slice Robust Enough To Trust

Done in the current tree:

- runtime observability for monitor and scheduler execution
- retry boundaries for analysis and notification stages
- artifact inspection helpers for persisted run outputs
- scheduler visibility for due and skipped monitors
- package-level verification so the first slice is stable enough for real use

This package is intentionally the last major investment in slice hardening.
After it, priority shifts back to product capability.

### Package 5: Document Intelligence And Queryability

In progress:

- define stable document identity and content-version behavior
- persist structured analysis results for retrieval, not only for notification
- add a first query/search path over stored documents and analyses
- prove at least one archive-oriented operator workflow

This package is the key course correction back to the original project idea:
Observer Rock should become a searchable document-monitoring knowledge layer.

Planned delivery slice for Package 5:

- make one stored monitor workspace queryable through a first operator-facing
  archive command
- let operators answer one real question from persisted data, not only inspect
  raw artifacts
- keep scope tight around one retrieval path instead of building a general API

Delivered so far in the current tree:

- successful monitor runs now index source records into a first document-intelligence store
- content changes on a source record now create a new indexed document version
- `query-documents --profile <profile> --contains <text>` provides the first
  archive retrieval path over persisted analysis projections
- query results now show readable excerpts instead of only raw stored JSON
- `document-history --document <document-id> --profile <profile>` provides the
  first document-version history and latest-vs-previous comparison path
- monitors can now define a budgeted recent-document recheck window and runtime
  persists the cursor and recent-document state needed to rotate through it
- built-in `builtin_indexed_file` proves the sparse revalidation contract with
  an index-plus-document fetch model

Package 5 should be considered done when all of the following are true:

- document identity is stable enough to group repeated observations of the same
  real-world document
- content-version changes are detectable and persisted explicitly
- structured analysis results can be retrieved by document and analysis profile
- at least one focused query workflow works end to end on the example workspace
- at least one focused history workflow shows how a stored document changed over time
- the runtime has a fair-use-friendly way to limit historical rechecks instead
  of assuming full history reloads on every schedule tick
- at least one source actually uses that fair-use-friendly recheck contract end to end
- the package adds product value beyond execution and notification

### Package 6: Rule-Driven Outputs And Audience Routing

After queryability exists:

- make rule evaluation an explicit product capability
- support multiple decisions or outputs from the same stored analysis result
- strengthen the separation between analysis, renderer, and notifier
- support more than one notification or interest path on top of the same data

### Package 7: Second Real Source Integration

After Packages 4 through 6:

- add a second real source with minimal new core code
- validate that the current architecture generalizes beyond the example slice
- use the second source to expose missing seams instead of adding abstractions first

### Package 8: Product Access Layer

Later, only after the document and query model is stable:

- add a cleaner service layer for documents, analyses, runs, and search
- prepare for richer CLI queries, API, or MCP-style access
- expose stored knowledge deliberately instead of coupling access to internals

## Working Mode

- A session should aim to complete one delivery package or one meaningful chunk
  of a package.
- TDD stays in place, but tests should be written for a coherent slice, not for
  one tiny invariant at a time.
- Ask the user only when blocked by a real product decision.
- Use subagents only for parallel side work with separate ownership.
- Do not let scheduler polish or framework tidying displace product-facing
  packages around document identity, queryability, rules, and multi-source proof.
