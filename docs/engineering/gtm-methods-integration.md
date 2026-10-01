---
title: GTM Methods Integration
status: active-pilot
updated: 2026-09-18
---

# GTM Methods integration

SalesWiki consumes reusable sales and marketing method notes through a thin,
project-local adapter. The separate private GTM Methods repository owns generic
source manifests, decision lenses, synthetic evaluation cases and portable
skills. SalesWiki owns all customer facts, access decisions, citations,
freshness, scoring and approval behavior.

## Initial reference

- Repository: private `GTM-Methods` checkout.
- Pinned release: `v0.1.0`.
- Commit: `a4d5a7adaf07f278ed15f7f7c895b09309a8a420`.
- Included candidate methods: evidence-first call preparation and
  evidence-first campaign brief.
- No runtime fetch, package installation or full-text source import occurs.

The pin is provenance for the pilot, not a dependency that the MCP gateway,
worker or Answer Contract reads at runtime.

## Adapter contract

`saleswiki-method-library` exists in both `.agents/skills/` and
`.claude/skills/`. It permits a method to influence only response shape and
synthetic evaluation after the usual boundary has produced the authorized,
cited facts:

```text
policy filtering -> deterministic cited Answer Contract
-> optional method-informed presentation
```

The adapter must not add source text as a fact, infer an account attribute,
alter permissions, modify source selection, suppress `missing`, change scoring
or trigger a write. The local candidates remain under `wiki/methods/` so their
SalesWiki use, limitations and tracking are visible in the vault.

## Upgrade or promotion

To adopt a later GTM Methods release, record the release and commit, examine
licence exceptions, map a named decision to a role × task pair, and run the
synthetic prompt checks before changing a profile. Promote a portable skill to
the user-level installation only after safe, useful results in at least two
independent consumer projects.

See [[0033-licensed-method-library-is-not-a-fact-store]],
[[0034-external-gtm-methods-with-local-policy-adapter]],
[[method-library-intake]] and [[prompt-development-contract]].
