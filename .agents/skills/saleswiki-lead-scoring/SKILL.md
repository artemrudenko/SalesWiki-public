---
name: saleswiki-lead-scoring
description: Score a SalesWiki lead or deal using the active config in schemas/scoring-models.json. Use when asked to score, qualify, re-score or prioritize a lead, MQL, or deal, or to explain why a lead's score changed. Produces a score, band, confidence, factors, next action and a calibration-feedback entry.
compatibility: Designed for Codex or any Agent Skills-compatible agent. Operates on the SalesWiki Obsidian vault; reads the scoring process docs under wiki/processes/.
metadata:
  author: SalesWiki
  version: "1.0"
---

# SalesWiki Lead / Deal Scoring

Turn the active config in `schemas/scoring-models.json` plus the calibration rules in `score-calibration.md` into a repeatable scoring run. This skill applies scoring; it does not change model weights (that requires the `saleswiki-scoring-configurator` workflow and explicit user approval).

## When To Use

- "Score / qualify / prioritize this lead (or MQL / deal)."
- "Re-score after this call / stage change / trigger."
- "Why is this lead hot / why did the score drop?"

## Inputs You Need

Read the entity card and its linked evidence before scoring:

- the `Lead` or `Deal` card (frontmatter + `Live Intelligence`, `Evidence`, `Linked Entities`).
- linked `Company`, `Person`, `Call`, `News`, `Event Participation` cards for evidence.
- `schemas/scoring-models.json` (canonical weights, bands, penalties/caps, confidence rules and default actions).
- `wiki/processes/scoring-models-v1.md` (human explanation), `score-calibration.md` (decay, outcomes), `freshness-and-decay.md` (staleness windows), `global-property-dictionary.md` (scoring properties), `property-vocabularies.md` (allowed values).

## Pick The Model

| Situation | Model |
| --- | --- |
| New inbound contact, no deal | `inbound-lead` |
| Outbound / cold target | `outbound-lead` |
| HubSpot qualification / MQL stage | `qualification-mql` |
| Open opportunity / deal | `deal` |

## Score Procedure

1. Read the selected model from `schemas/scoring-models.json`.
2. Score each configured dimension 0–100 against evidence, then weight it:
   - `weighted = Σ(dimension_0_100 × configured_weight) / 100`.
3. Apply the configured penalties/caps/disqualification rules after weighting.
3. Apply **decay** (`freshness-and-decay.md`) to confidence/triggers, never to base weights:
   - MQL no activity 14 days → drop `score_confidence` one level.
   - Outside-pipeline no activity 30 days → remove trigger-strength contribution.
   - Public trigger older than 60 days → remove its boost.
4. Map to `score_band` using configured `score_bands`.
5. Set `score_confidence` using configured confidence rules plus available evidence.

## Write Back To The Card

Update only mutable scoring frontmatter (never controlled profile fields): `score`, `score_band`, `score_confidence`, `score_model` (e.g. `scoring-models-v1/qualification-mql`), `scored_at` (today), `next_review`, `score_decay`. In `Live Intelligence` / readout, record the required output:

- score, band, model ID/version, top positive factors, top negative factors, evidence links, confidence, recommended next action, owner, next review date.

If you propose changing a controlled field or the model itself, put it in `Review Needed` — do not apply it.

## Log Calibration Feedback

Append an entry to `state/score-feedback.md` with: card link, model name/version, score, band, confidence, top factors, recommended action, expected outcome, and `actual outcome` left blank until known (labels in `score-calibration.md`).

## Guardrails

- Do **not** edit scoring weights, bands, penalties or model versions. Agents may apply, explain, flag and *propose* recalibration only.
- If the user wants to change scoring configuration, switch to the `saleswiki-scoring-configurator` workflow.
- Do not overwrite non-empty controlled fields; respect `profile_lock`.
- HubSpot stays the source of truth for stage/owner/next activity — read it, don't silently overwrite it.
- After editing cards, run `python3 scripts/health_check.py`.

## Done When

Card frontmatter + readout updated, feedback logged, health check clean, and the answer to the user leads with band + next action + confidence + what's missing.
