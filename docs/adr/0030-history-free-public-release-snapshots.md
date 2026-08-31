---
status: Accepted
date: 2026-08-31
deciders: SalesWiki maintainers
---

# ADR-0030: Publish history-free snapshots from the private source repository

## Status

Accepted

## Context

SalesWiki development can include local experiments, private coordination and
runtime configuration even when tracked content is intended to be public-safe.
Publishing the same Git history would unnecessarily widen the disclosure
surface. At the same time, public users need a cloneable, reproducible project.

## Decision

The private repository is the sole source of truth. The public repository is a
one-way release mirror made from a fresh, checked snapshot of tracked files at
a chosen private commit. `scripts/export_public_snapshot.py` first runs the
public-release review, then uses `git archive` to create a tree without `.git`
history or ignored local files. Maintainers inspect and test that tree before
making a new commit in the public repository.

Nothing is merged or pulled from the public repository back into private
development. Fixes discovered publicly are reimplemented and reviewed in the
private source repository, then included in the next snapshot.

## Consequences

**Positive**

- Public users receive a clean, reproducible repository.
- Private history, branches, ignored runtime state and local configuration do
  not cross the boundary.
- Every public release has an explicit source commit and review gate.

**Negative / trade-offs**

- Release is an intentional publish operation, not an automatic push.
- Public issue fixes need to be carried back deliberately.

## Alternatives considered

- **Make the working repository public** — rejected because past history and
  private development context become part of the public surface.
- **Bidirectional mirror** — rejected because it weakens the boundary and makes
  review of inbound public changes ambiguous.

## References

- `scripts/export_public_snapshot.py`
- `scripts/public_release_review.py`
- `docs/REPOSITORY_CONTENTS.en.md`
