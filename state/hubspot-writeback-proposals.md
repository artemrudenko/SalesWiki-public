# HubSpot Writeback Proposals

Use this queue for proposed HubSpot card fills, field updates, task creation and writeback decisions.

No proposal in this file is executed automatically. HubSpot remains the operational CRM source of truth.

## Fields

| Field | Meaning |
| --- | --- |
| `proposal_id` | Stable ID, usually `hs-prop-YYYYMMDD-<short-scope>-<sequence>`. |
| `date` | Proposal date. |
| `hubspot_object_type` | `company | contact | deal | task`. |
| `hubspot_id` | Existing HubSpot object ID, if known. |
| `target_field` | HubSpot field to fill/update. |
| `mode` | `propose-only | approved-writeback | system-writeback`. |
| `previous_value` | Current HubSpot value or `unknown`. |
| `proposed_value` | Proposed value to write or create. |
| `source` | SalesWiki card, raw path, URL or evidence source. |
| `confidence` | `high | medium | low`. |
| `approver` | Human approver or automation rule. |
| `status` | `draft | awaiting-approval | approved | rejected | written | blocked`. |
| `notes` | Conflict, dedupe, privacy or implementation notes. |

## Queue

| proposal_id | date | hubspot_object_type | hubspot_id | target_field | mode | previous_value | proposed_value | source | confidence | approver | status | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
