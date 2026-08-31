---
status: Superseded
date: 2026-06-24
deciders: SalesWiki maintainers
superseded_by: ADR-0019
---

# ADR-0014: Docker packaging deferred for the MVP

## Status

Superseded by [ADR-0019](0019-public-preview-and-docker-starter-path.md).
This remains as historical context for the local MVP.

## Context

The target deployment topology separates a read/propose-only gateway from a
single-writer worker, so the gateway can be the controlled door to the data.
Docker Compose is one way to express that boundary, read-only mounts and
out-of-repo secret injection.

But the deployment doc's own central principle is that a gateway enforces access
*only if it is the sole path to the bytes* — containers do not by themselves
close the real side doors (git clone, a shared Obsidian vault, shell on the
host). For the first local, read-only, single-operator prototype there are no
hosted users, no connectors and no secrets, so Docker would add iteration cost
while reducing little risk. The whole repo is also deliberately standard-library
only (no required packages for the vault, health check, indexes, core or
worker), so it already runs anywhere Python 3 runs.

## Decision

We defer Docker packaging for the MVP and run the gateway and worker as plain
Python 3 processes. Docker Compose (two services, `saleswiki-mcp` read-only +
`saleswiki-worker` as the single writer, secrets injected from the environment)
remains the documented target topology for a shared/semi-shared Phase 2
deployment, to be adopted when there are hosted users, connectors or secrets to
isolate. Kubernetes is explicitly out of scope.

## Revisit note (2026-08-20)

The public preview now ships a Docker starter path for repeatable checks and
demo runtime (`ADR-0019`). That does not change the production boundary: real
multi-user deployment still needs SSO, secret management, backups and incident
operations.

## Consequences

**Positive**
- Lowest-friction setup: `python3` is the only dependency; contributors and the
  single operator iterate without a container toolchain.
- The gateway/worker split and read-only/single-writer boundary are still
  designed and documented, so adopting Compose later is configuration, not
  redesign.
- Avoids the false comfort of "it's containerized, so it's secure" while the
  real side doors are still open.

**Negative / trade-offs**
- No enforced per-service filesystem isolation until Compose lands; the
  read-only/single-writer boundary is conventional rather than OS-enforced.
- Reproducible staging runs and isolated connector credentials wait for Phase 2.
- Closing the side doors (no shell/git/shared-vault access) must be handled
  operationally in the meantime.

## Alternatives considered

- **Dockerize from day one** — rejected: adds toolchain/iteration cost with no
  hosted users, connectors or secrets to protect at MVP stage.
- **Kubernetes** — rejected: far beyond the needs of a small-team, two-service
  deployment.
- **Containers as the security boundary** — rejected as a misconception:
  isolation enforces nothing while direct file access remains; closing side
  doors is what makes the gateway sufficient.

## References

- [ADR-0019](0019-public-preview-and-docker-starter-path.md)
- `docs/DEPLOYMENT.en.md`
- `docs/engineering/permissioned-knowledge-architecture.md`
- `saleswiki_mcp/worker.py` (single-writer worker)
- `AGENTS.md` (standard-library-only setup), `CLAUDE.md`
