---
status: Accepted
date: 2026-07-03
deciders: SalesWiki maintainers
---

# ADR-0018: Personal-data erasure vs git-as-storage

## Status

Accepted.

## Context

SalesWiki stores its durable state as Markdown in git, and the pilot-data contract
(`wiki/processes/pilot-data-contract.md`) requires the pilot vault to be its **own
git repository** "for history and recovery." Git is designed to make history
immutable — that is its value for evidence integrity (ADR-0002) and the audit
trail. But that same immutability is in direct tension with a data-subject's right
to erasure (GDPR Art. 17 and equivalents): a `git rm` of a card leaves every prior
version of that card — including any personal data in it — fully recoverable in the
history, on every clone. The deletion/redaction process contracts
(`wiki/processes/deletion-and-archiving.md`, `access-and-redaction-policy.md`) never
mention git, so the documented "delete/redact" workflow cannot actually erase
personal data that has entered a git-tracked vault.

This must be resolved **before any real personal data enters a vault**, not after.

## Decision

1. **Personal-data raw bodies never enter a git-tracked vault.** This extends
   ADR-0003 (personal-data is handles only): the git-tracked vault holds only
   pseudonymous refs/handles (`restricted://…`) and non-personal fields. The raw
   personal data lives in an external controlled store that supports **hard delete**
   (a database row, an object with a delete API, or an encrypted blob) — never a git
   commit.
2. **Erasure = delete the external record + revoke the handle.** A deletion request
   (`state/deletion-requests.md`) resolves by hard-deleting the external record and
   removing/tombstoning the handle in the vault. Because the vault never held the
   body, no history rewrite is needed for the body; the handle's history is
   non-personal.
3. **Audit log uses pseudonymous subject ids and a retention policy.** The audit
   chain logs the pseudonymous `sub` (not raw email), has a defined retention window,
   and is re-anchored (a fresh genesis) when records age out — so erasure and the
   tamper-evident chain do not conflict (auth-review M9).
4. **The pilot vault git rule is amended.** A vault that will hold personal-data
   **bodies** must NOT be a plain git repo relying on history for recovery; recovery
   for such data comes from the external store's backups (encrypted), not git
   history. A vault that holds only handles/refs may remain a git repo. The
   pilot-data contract is updated to state this.
5. **Crypto-shredding is the fallback** where a body unavoidably lands in an
   append-only medium (e.g. a backup): store it encrypted per-subject and erase by
   destroying that subject's key, rendering the ciphertext unrecoverable.

## Consequences

**Positive**
- Right-to-erasure becomes actually executable, not just documented.
- Keeps git's immutability where it belongs (non-personal evidence, handles, audit)
  and out of where it is a liability (personal-data bodies).
- No history-rewrite tooling on the hot path; erasure is a store delete + handle
  tombstone.

**Negative / trade-offs**
- Requires an external controlled store with a delete API before real PII is
  onboarded — a real dependency the MVP did not have.
- Backups must support crypto-shredding or per-subject deletion; plain immutable
  snapshots of PII are not compliant.
- Two-store model (git handles + external bodies) adds a join at read time (already
  the handles-only design in ADR-0003, so mostly aligned).

## Alternatives considered

- **`git filter-repo` / history rewrite on each erasure** — rejected: rewriting
  shared history is disruptive (every clone must re-sync), error-prone, and does not
  scale to routine erasure requests; misses copies already cloned.
- **Keep PII bodies in git, rely on `git rm`** — rejected: does not erase history;
  non-compliant.
- **No personal data in SalesWiki at all** — viable and safest for some teams (see
  [[buy-vs-build]]); this ADR is the path for teams that must hold personal-data
  handles.

## References

- ADR-0002 (raw evidence immutable), ADR-0003 (controlled profile / handles-only)
- `wiki/processes/pilot-data-contract.md`, `wiki/processes/deletion-and-archiving.md`
