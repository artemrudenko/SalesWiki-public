---
name: saleswiki-method-library
description: Apply a source-backed GTM method note to SalesWiki task framing or synthetic prompt evaluation without weakening the Answer Contract, authorization, citations or scoring rules.
---

# SalesWiki Method Library

Use this skill when a user asks to introduce, evaluate or apply a reusable sales
or marketing method in SalesWiki. The external GTM Methods project supplies
generic method packages; this is the SalesWiki-specific adapter.

## Boundary

Treat method notes as response-shape and evaluation guidance, never as facts
about an entity, a deal, a person, a campaign or a market. They cannot change
access policy, redaction, retrieval, citations, freshness, `missing`, scoring,
approval rules or the Answer Contract.

Follow the existing runtime sequence:

```text
authorization -> permitted cited facts -> deterministic Answer Contract
-> optional method-informed presentation
```

Do not put a textbook excerpt or generic framework into the factual Answer
Contract. Do not turn an educational model into a claim about a customer.

## Working with a method

1. Read `wiki/processes/method-library-intake.md` and the relevant local method
   note under `wiki/methods/`.
2. Confirm its status. A `candidate` may guide only synthetic evaluation and a
   narrow presentation-profile experiment; an `adopted` note still cannot
   bypass the boundary above.
3. Name one role × task pair and the concrete decision it should improve.
4. Add or update synthetic scenarios before changing a presentation profile.
5. Render and test the exact prompt using the prompt-development contract.
6. Record the source, method version, result and limitations in the normal
   SalesWiki tracking flow.

The initial external reference is GTM Methods `v0.1.0`
(`a4d5a7adaf07f278ed15f7f7c895b09309a8a420`). It is a versioned source of
generic methods, not a runtime dependency or a source of customer data.

## When to stop

Ask for explicit direction before importing full source text, changing a method
status to `adopted`, altering scoring, changing access behavior, or promoting a
skill to the user-level installation. A missing source, licence exception or
synthetic-evaluation regression is a reason to leave the method as `candidate`.
