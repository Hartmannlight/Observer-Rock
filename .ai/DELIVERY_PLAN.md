# Observer Rock Delivery Plan

## Goal

Finish a usable first product slice quickly while keeping TDD and strong test
coverage.

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

The project now has one working product slice. The goal remains progress by
coherent delivery packages, not by framework-only micro-steps.

### Package 3: Operator Usability

Next:

- tighten CLI output
- add example setup docs
- document failure modes and secrets

### Package 4: Hardening

Only after Package 2 is real:

- logging improvements
- retry boundaries
- better scheduler ergonomics
- artifact inspection helpers

## Working Mode

- A session should aim to complete one delivery package or one meaningful chunk
  of a package.
- TDD stays in place, but tests should be written for a coherent slice, not for
  one tiny invariant at a time.
- Ask the user only when blocked by a real product decision.
- Use subagents only for parallel side work with separate ownership.
