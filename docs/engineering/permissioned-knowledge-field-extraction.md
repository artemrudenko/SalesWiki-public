---
title: Permissioned Knowledge - Field Extraction Contract
tags:
  - process
  - architecture
  - data-contract
  - mcp
status: draft
updated: 2026-06-03
---

# Permissioned Knowledge - Field Extraction Contract

Closes architectural risk #1 (read layer coupled to one card shape). The permissioned read tools no longer hardcode card section/bullet names; they read a declarative profile, `schemas/field-extraction.json`, so pointing the gateway at a differently-shaped vault is a config swap, not a code change.

## Problem

The extractors searched for fixed strings (e.g. `Strategic Conclusions` -> `Risk`) that exist in the synthetic demo cards but **not** in the production templates (a real Deal uses `Risks` / `Next Best Action`). On a real vault the read tools would silently return empty. Template and extractor could drift with nothing to catch it.

## Contract

`schemas/field-extraction.json` maps `card type -> logical field -> {section, label?}`:

```json
"deal": { "risk": {"section": "Risks", "label": "Risk"},
          "recommended_action": {"section": "Next Best Action", "label": "Recommended action"} }
```

- `formatter.field_value(body, spec)` extracts a whole section, or a labeled bullet within it.
- `CompanyBriefService` loads the profile (injectable via `field_map=`) and calls `self._field(card, key)`; all read tools use it - no hardcoded card strings remain (the only generic `extract_section` left is the company-brief fallback across linked cards).

## Guarantees (tested)

- `health_check` validates the profile structure (every `type.field` has a non-empty `section`; `label` is a string) - it cannot silently become malformed.
- `tests/test_field_extraction.py`:
  - **profile <-> demo coherence**: every mapped `(type, field)` resolves to non-empty content on the active demo cards (templates and extractor agree).
  - **production-shape decoupling**: a card with production-style sections (`Risks` / `Next Best Action`) extracts correctly via an override spec - proving the extractor is data-driven.
  - the service accepts an injected `field_map`; an unmapped field returns `""` (callers supply fallbacks), never an error.

## Pointing at a real vault

The active profile already targets production-template sections (the permissioned demo cards were reshaped to match: Deal -> `Deal Readout`/`Risks`/`Next Best Action`/`Scoring` (numeric score, win probability, ACV, days-in-stage)/`Controlled Profile` (stage), Call -> `Executive Summary`/`Follow-Up Draft`, Lead -> `Scoring` (numeric score, band, funnel stage MQL/SQL/nurture)/`Why This Lead Matters`/`Next Action`, Source -> `Source Summary` (market signal, surfaced to non-deal roles in target-account briefs), Event/Campaign target-account + `Outreach Opportunities`/`Messaging`, Pain -> `Messaging`). To serve a different vault, provide a profile whose sections/labels match its templates and inject it (or replace `schemas/field-extraction.json`). Optional next step before a real-vault pilot: a fixture vault built from the real `wiki/entities/*/_template.md` files plus its profile, run through the read-tool suite.

## See Also

- [[permissioned-knowledge-architecture]] (risk register / implementation status)
- [[permissioned-knowledge-architecture]] (Answer Contract, the output side)
- [[card-taxonomy]] (the production card shapes a real profile must match)
