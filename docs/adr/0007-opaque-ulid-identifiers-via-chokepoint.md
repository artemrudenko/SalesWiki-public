---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0007: Opaque typed ULID identifiers minted via a single chokepoint

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

Entity identity must stay consistent as the vault grows and as separate vaults (demo, pilot, imported team vaults) merge. Early cards used readable slug `entity_id`s derived from names, which break on rename and risk collisions or silent duplicates when the same real object is ingested twice or across vaults. There was no central record of which ids existed. The project needed ids that survive renames, are unique without a coordinating lock, dedupe by natural key, and have an auditable provenance trail. This was established in `wiki/processes/identifier-strategy.md` (variant C) and in the `data-engineering-contract.md` stable-ID requirement.

## Decision

We assign every entity an opaque, typed, time-sortable core id `entity_id = <type>_<ULID>`, minted once at creation and never re-derived from mutable data, with a separate readable `slug`/`aliases` surface for humans. Ids are minted only through one chokepoint — `saleswiki_mcp/ids.py` (`IdAllocator.mint`), invoked by `scripts/new_entity.py` (`create_entity`) — which dedupes by natural key (company→domain, person→email, deal→CRM id) and appends every allocation to the append-only ledger `state/id-ledger.jsonl`. On a duplicate-merge the loser's id becomes an `alias` of the canonical id so old references keep resolving. `health_check.check_id_ledger` validates the ledger (typed-ULID format, uniqueness, idempotent natural keys) when present. The permissioned demo keeps deterministic readable slug ids by design, since the slug must stay referenceable by fixtures and tests.

## Consequences

**Positive**
- Ids survive renames; references resolve by id first, then slug/alias.
- ULIDs are globally unique without a central lock and are lexicographically time-sortable.
- Natural-key dedup prevents silent duplicates; the append-only ledger gives provenance and a uniqueness backstop.

**Negative / trade-offs**
- Opaque ids are not human-readable, so a parallel slug/alias surface must be maintained.
- All card-creating flows must route through the chokepoint; hand-authoring `entity_id` is disallowed.
- Existing readable-slug production cards need a transition (kept valid as slug/alias; optional backfill) rather than a big-bang migration.

## Alternatives considered

- **Name/slug-derived ids** — rejected: break on rename and collide across vaults; this is the problem being replaced.
- **Plain sequential integers or UUIDv4** — rejected: sequential needs a coordinating counter (lock); UUIDv4 is not time-sortable and carries no type — ULID gives both unordered uniqueness and ordering.
- **Let any script mint ids ad hoc** — rejected: no dedup, no provenance, no uniqueness guarantee; a single chokepoint plus ledger is required.

## References

- [[identifier-strategy]] — `wiki/processes/identifier-strategy.md` (variant C)
- `saleswiki_mcp/ids.py` (`IdAllocator.mint`, `lookup`, `ulid`)
- `scripts/new_entity.py` (`create_entity` chokepoint)
- `state/id-ledger.jsonl`; `scripts/health_check.py` (check_id_ledger)
- [[data-engineering-contract]] — `wiki/processes/data-engineering-contract.md` (Stable IDs)
