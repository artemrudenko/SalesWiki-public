# Sales Team Feedback Requirements

This document converts sales-team feedback into SalesWiki requirements.

## Priority Readout

Near-term priorities:

1. AI research and outreach.
2. Lead monitoring, especially promising leads outside active pipeline.
3. Lead and deal scoring.
4. Call analysis with Google Meet recordings/transcripts.
5. KB cleanup and regular private case capture.
6. HubSpot enrichment with AI, Apollo.io and optional Crunchbase.
7. Sales assistant by stage, including client-specific intro decks later.
8. HoS reporting.

Lower priority for now:

- Exhibition parsing. Keep event monitoring model, but do not make it the first automation focus.
- LinkedIn high-volume posting automation. Coordinate with marketing before adding tooling.

## Lead Monitoring Requirement

Sales distinguishes two important lead groups.

### 1. Promising Leads Outside Active Pipeline

These are not active HubSpot Deals, but the contact/company is promising.

Need:

- keep them in work without over-pinging
- set reminders
- monitor company/person triggers
- look for news hooks
- check client-owned news and public updates
- optionally inspect LinkedIn context when allowed and available

Cadence:

- low-frequency monitoring
- usually monthly or trigger-based
- do not recommend outreach without a real trigger or reason

Output:

- reminder
- trigger summary
- suggested touch
- confidence
- source

### 2. Active Pipeline / Qualification / MQL Leads

These are often HubSpot Deals in qualification or MQL stages, including website leads, outbound leads or research-stage leads not yet SQL.

Need:

- more frequent monitoring
- warm-up over several months
- periodic pings when a trigger appears
- next-best-action suggestions
- score updates

Cadence:

- weekly for qualification/MQL
- more often if a high-intent trigger appears

Output:

- lead score
- deal score when a deal exists
- next best action
- missing information
- reminder/task

## Lead And Deal Scoring Requirement

A score should be assigned by an agent based on a defined model and available evidence.

Scores should work for:

- inbound leads
- outbound leads
- MQL/qualification leads
- deals
- promising contacts outside active pipeline

The score must include:

- numeric score
- grade/category
- scoring factors
- evidence
- confidence
- recommended next action
- date scored
- next review date

## Google Meet Call Analysis Requirement

Sales uses Google Meet in the corporate workspace. The system should support:

- importing Google Meet recordings
- importing Google Meet transcripts when available
- linking transcript/recording to company, people, deal and lead
- English call transcription as a primary path
- manual upload fallback

Internal meetings may not be reliably transcribed; mark those as `needs-transcript` or `manual-notes`.

## Client-Specific Sales Assistant Requirement

At each sales stage, the assistant should eventually provide:

- stage-specific checklist
- call prep
- follow-up draft
- next best action
- objection handling
- relevant case studies/assets
- client-specific intro presentation draft

Deck generation should be treated as a future asset workflow, not a first dependency.

## Account Manager Assistance

AM support should use:

- account plan
- relationship history
- active risks
- open opportunities
- delivery/project notes when available
- private internal cases
- renewal/upsell triggers

## HoS Reporting

Head of Sales reporting should include:

- pipeline risk
- stale deals
- promising leads without action
- MQL/qualification movement
- lead/deal score distribution
- source/channel signal quality
- follow-up compliance
- weekly signal digest

## LinkedIn Content Requirement

Marketing and sales should agree before implementing LinkedIn content tooling.

Near-term approach:

- marketing may generate content outputs separately
- leadgen team can receive approved content summaries and post manually
- avoid adding many external tools until workflow is confirmed

## KB And Private Case Capture Requirement

The team already has a Google Drive KB, but navigation and structure are becoming harder.

SalesWiki should support:

- structured KB cleanup
- regular case capture
- dictated case intake
- written case intake
- private case studies not for public publishing
- presales and delivery challenge notes

Private cases should include:

- project context
- unusual challenge
- solution/approach
- outcome
- reusable lesson
- related ICP/persona/use case
- access restrictions

## HubSpot Enrichment Requirement

Avoid dependence on expensive enrichment tools where possible.

Preferred direction:

- HubSpot as CRM source of truth
- Apollo.io for contact/company enrichment
- AI for research and summarization
- optional Crunchbase for company/funding data if available
- avoid Clay dependency unless explicitly approved later

## System Implications

Add or strengthen:

- lead scoring model
- deal scoring model
- lead monitoring cadence
- reminder/task workflow
- HubSpot sync/enrichment fields
- Google Meet call import process
- private case capture template
- HoS report template
- stage assistant playbook

