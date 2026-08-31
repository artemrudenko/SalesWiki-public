---
name: saleswiki-scoring-configurator
description: Guide a user-approved change to SalesWiki scoring models. Use when the user wants to change lead/deal scoring weights, score bands, penalties, caps, confidence rules or default scoring actions.
compatibility: Designed for Codex or any Agent Skills-compatible agent. Operates on schemas/scoring-models.json, scoring process docs and state/scoring-change-requests.md.
metadata:
  author: SalesWiki
  version: "1.0"
---

# SalesWiki Scoring Configurator

Use this skill only when the user explicitly asks to change scoring configuration.

## Authority

- Canonical config: `schemas/scoring-models.json`.
- Human explanation: `wiki/processes/scoring-models-v1.md`.
- Change process: `wiki/processes/scoring-configuration.md`.
- Change ledger: `state/scoring-change-requests.md`.

## Procedure

1. Read the current config and identify the affected model: `inbound-lead`, `outbound-lead`, `qualification-mql` or `deal`.
2. Ask only necessary questions to resolve ambiguity.
3. Prepare the proposed change and validate it before editing:
   - model weights sum to `100`
   - score bands cover `0-100` without gaps/overlap
   - caps/penalties are valid
   - model IDs and band IDs remain canonical
4. Show the user a concise before/after diff and ask for explicit approval.
5. Only after approval, edit `schemas/scoring-models.json`, update human docs, append `state/scoring-change-requests.md`, and run `python3 scripts/health_check.py`.

## Guardrails

- Do not change scoring config during ordinary scoring.
- Do not silently rebalance weights; ask the user where points should move.
- Do not create a new band or model without also updating vocabularies/docs/checks.
- Keep old model references visible through versioning and change ledger entries.
