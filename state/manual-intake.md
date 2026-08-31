# Manual Intake Queue

Use this queue when a user manually asks to review a link, person, company, event, source, material or topic.

| request_id | date | requester | intake_type | input | desired_output | urgency | access | monitor_after | owner | status | result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |  |  |  |

## Quick Drop (no format required)

Paste a request below in plain text — no table, no YAML. An agent converts each
entry into a structured row above, processes it per
[[manual-intake]] (`wiki/processes/manual-intake.md`), and replaces the entry
with a one-line pointer to the result. Copy a starter if it helps:

```text
LINK: <url> — why it matters / what you want to know
COMPANY: <name, website> — what you want to know about them
AFTER CALL: <company or person> — what happened, free text
```

Example (delete after reading):

```text
LINK: https://example.com/competitor-pricing-update — check if this changes our RivalCorp battle card
```

### Drop here

<!-- new entries below this line -->
