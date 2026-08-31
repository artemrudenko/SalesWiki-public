---
status: Accepted
date: 2026-08-20
deciders: SalesWiki maintainers
supersedes: ADR-0014
---

# ADR-0019: Public preview ships with a Docker starter path, not production hosting

## Status

Accepted. Supersedes ADR-0014 for the public repository.

## Context

The original MVP deferred Docker because the first target was a local,
single-operator prototype. That was correct for speed, but the public repository
has a different requirement: a new user must be able to verify the project
without reconstructing the maintainer's machine.

The project still is not a production multi-user service. Docker should provide
repeatable local checks and an MCP stdio demo runtime, not imply that hosted
identity, connector secrets, backups and incident response are solved.

## Decision

Ship a minimal Docker starter path:

- `Dockerfile` builds the project with the pinned Python/MCP runtime.
- `docker-compose.yml` exposes `check`, `health`, `test`, `demo` and `mcp-ae`
  services.
- `.dockerignore` excludes local state, virtualenvs, private settings, secrets
  and demo runtime output from the build context.
- `docs/DEPLOYMENT.en.md` documents local and Docker usage, and explicitly marks
  production SSO/operations as future work.

Production hosting remains out of scope for the public preview.

## Consequences

**Positive**

- New users can run a repeatable smoke path.
- CI and local Docker use the same public-release review.
- The repository is easier to evaluate without installing Obsidian or an MCP
  client first.

**Negative / trade-offs**

- Docker may create false confidence if readers miss the production gap.
- The MCP stdio server is still normally launched by an MCP client, not as an
  HTTP service.
- Real deployments still need identity, secret management, connector scoping,
  backup/restore and incident response.

## Alternatives considered

- **No Docker** — rejected for public preview: too much setup ambiguity for new
  users.
- **Full production Compose** — rejected: would overstate maturity and force
  identity/secrets decisions before product value is proven.
- **Hosted SaaS** — rejected: outside the scope of a shareable starter kit.

## References

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `docs/DEPLOYMENT.en.md`
- `docs/ROADMAP.en.md`
