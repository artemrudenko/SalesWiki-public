---
type: call
entity_id: synthetic-call-alpha-discovery
template_version: 1
created: 2026-05-29
updated: 2026-05-29
source_id: synthetic-source-call-1
raw_path: tests/fixtures/synthetic-vault/raw/calls/synthetic-alpha-discovery.txt
content_hash: synthetic-hash
ingest_run_id: synthetic-20260529-call-001
company: "[[Company - Synthetic Alpha]]"
deal: "[[Deal - Synthetic Alpha - Pilot]]"
date: 2026-05-29
participants:
  - "[[Person - Synthetic Buyer]]"
participant_match_status: matched
transcript: tests/fixtures/synthetic-vault/raw/calls/synthetic-alpha-discovery.txt
recording:
transcript_status: manual-notes
language: en
analyst: synthetic-agent
freshness: fresh
access: sales-confidential
profile_lock: locked
deletion_status: active
tags:
  - call
---

# Call: Synthetic Alpha / 2026-05-29 / Discovery

Synthetic fixture call for validating call propagation and raw-path indexing.

## Controlled Profile

- Company: [[Company - Synthetic Alpha]]
- Deal: [[Deal - Synthetic Alpha - Pilot]]

## Linked Entities

- Company: [[Company - Synthetic Alpha]]
- Deal: [[Deal - Synthetic Alpha - Pilot]]
- Participants: [[Person - Synthetic Buyer]]
- Leads: [[Lead - Synthetic Alpha - Buyer]]

## Evidence

- Transcript: tests/fixtures/synthetic-vault/raw/calls/synthetic-alpha-discovery.txt

## Updates Needed

- Company page: [[Company - Synthetic Alpha]]
- Lead page: [[Lead - Synthetic Alpha - Buyer]]
- Deal page: [[Deal - Synthetic Alpha - Pilot]]
- People pages: [[Person - Synthetic Buyer]]

## Review Needed

- None.

## Change History

| Date | Change | Source/request |
| --- | --- | --- |
| 2026-05-29 | Created synthetic fixture | tests/fixtures |
