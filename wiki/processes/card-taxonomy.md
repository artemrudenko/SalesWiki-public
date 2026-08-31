# Card Taxonomy

SalesWiki cards should be standardized by type. Cards of the same type must follow the same required section structure so agents can update them reliably and employees know where to look.

## Design Principle

Create a card type only when it has at least one of these:

- its own lifecycle
- its own owner
- repeated reuse across companies, deals or campaigns
- recurring monitoring need
- evidence value
- direct sales/marketing action value

Do not create a separate card for every passing note. Use source cards, logs or live intelligence sections for lightweight details.

## Card Layers

## 1. Commercial Entities

These are the main business objects.

- Company
- Person
- Lead
- Deal
- Account Plan
- Call
- Event
- Campaign
- Report
- Product
- Customer Success

## 2. Evidence And Source Entities

These preserve evidence and prevent unsupported conclusions.

- News
- Article
- Event Participation
- Source
- Claim
- Raw file/reference

## 3. Market And Messaging Knowledge

These make the wiki useful for marketing, sales enablement and positioning.

- ICP
- Buyer Persona
- Topic
- Pain Point
- Objection
- Use Case
- Competitor Intel
- Case Study
- Private Case
- Asset
- Outreach Sequence
- Channel
- Content Brief
- Content Calendar Item
- Scoring Model
- Enrichment Record

`Channel`, `Content Brief` and `Content Calendar Item` are marketing-operations cards (templates under `wiki/entities/channels/`, `content-briefs/`, `content-calendar/`; status values in `schemas/property-vocabularies.json`). They feed the `marketing-insights` dashboard.

## 4. Operating Entities

These drive execution and learning.

- Task
- Experiment
- Monitoring Run (state/queue file, not a Controlled-Profile card)
- Manual Intake Request (state/queue file, not a Controlled-Profile card)
- Deletion Request (state/queue file, not a Controlled-Profile card)

## Global Required Sections

Every reusable entity card should include:

- YAML properties
- `Controlled Profile`
- `Live Intelligence` when the card receives recurring updates
- type-specific conclusion/readout section
- `Linked Entities`
- `Evidence`
- `Review Needed`
- `Change History`

Exceptions:

- lightweight queue/state files can use tables instead of full card sections
- raw source files remain raw and do not need this structure

## Required Sections By Type

## Company

- Controlled Profile
- Live Intelligence
- What They Do
- Strategic Conclusions
- Current Signals
- Website Intelligence
- External News
- Key People
- Relationship Map
- Leads
- Deals
- Calls and Meetings
- Pain Points and Hypotheses
- Evidence Cards
- Recommended Next Action
- Open Questions
- Review Needed
- Change History
- Sources

## Person

- Controlled Profile
- Live Intelligence
- Bio and Responsibilities
- Relationship And Messaging Conclusions
- Recent News and Signals
- Articles, Interviews And Public Appearances
- Relationship Map
- Monitoring Patterns
- Messaging Notes
- Relationship
- Sources
- Review Needed
- Change History

## Lead

- Controlled Profile
- Live Intelligence
- Why This Lead Matters
- Monitoring And Reminder
- Scoring
- Scoring Factors
- Evidence
- Outreach Context
- Activity
- Next Action
- Review Needed
- Change History

## Deal

- Controlled Profile
- Live Intelligence
- Current State
- Deal Readout
- Scoring
- Scoring Factors
- Buying Committee
- Timeline
- Calls and Notes
- Risks
- Next Best Action
- Sources
- Review Needed
- Change History

## Account Plan

- Controlled Profile
- Account Strategy
- Stakeholder Map
- Opportunity Map
- Signals And Triggers
- Messaging Strategy
- Action Plan
- Risks
- Evidence
- Review Needed
- Change History

## Call

- Controlled Profile
- Executive Summary
- Customer Context
- Linked Entities
- Buying Signals
- Objections and Risks
- Commitments
- Follow-Up Draft
- Updates Needed
- Review Needed
- Change History

## Event

- Controlled Profile
- Live Intelligence
- Why It Matters
- Event Intelligence
- Topics
- Exhibitors
- Sponsors
- Speakers
- Sessions And Agenda Signals
- Target Accounts Present
- Outreach Opportunities
- Competitor Intelligence
- Sources
- Tracking
- Review Needed
- Change History

## Campaign

- Controlled Profile
- Goal
- Target Accounts And Leads
- Messaging
- Performance
- Learnings
- Sales Handoff
- Sources
- Review Needed
- Change History

## Buyer Persona

- Controlled Profile
- Role Summary
- Goals And KPIs
- Pains
- Buying Triggers
- Objections
- Messaging
- Useful Assets
- Discovery Questions
- Linked Entities
- Evidence
- Review Needed
- Change History

## Pain Point

- Controlled Profile
- Problem Definition
- Symptoms
- Impact
- Who Cares
- Evidence
- Messaging
- Discovery Questions
- Related Use Cases
- Linked Entities
- Review Needed
- Change History

## Objection

- Controlled Profile
- Objection Pattern
- Why It Happens
- Best Response
- Proof And Assets
- Discovery Questions
- Evidence
- Related Deals/Calls
- Review Needed
- Change History

## Use Case

- Controlled Profile
- Situation
- Target Persona
- Problem
- Proposed Value
- Proof
- Discovery Questions
- Assets
- Related Companies/Deals
- Review Needed
- Change History

## Competitor Intel

- Controlled Profile
- Positioning
- Strengths
- Weaknesses
- Where They Win
- Where They Lose
- Battlecard
- Evidence
- Related Deals
- Review Needed
- Change History

## Case Study

- Controlled Profile
- Customer Context
- Problem
- Solution
- Outcomes
- Proof Points
- Reusable Messaging
- Related ICP/Persona/Use Case
- Assets
- Review Needed
- Change History

## Private Case

- Controlled Profile
- Context
- Challenge
- Approach
- Outcome
- Reusable Lesson
- Linked Entities
- Review Needed
- Change History

## Scoring Model

- Controlled Profile
- Score Dimensions
- Score Bands
- Required Output
- Review Needed
- Change History

## Enrichment Record

- Controlled Profile
- Input Data
- Enriched Data
- Source Checks
- CRM Update Proposal
- Review Needed
- Change History

## Report

- Controlled Profile
- Summary
- Key Metrics
- HoS Reporting Blocks
- Highlights
- Risks
- Recommended Actions
- Evidence
- Follow-Up Tasks
- Review Needed
- Change History

## Outreach Sequence

- Controlled Profile
- Target Audience
- Trigger
- Messaging Angle
- Steps
- Personalization Inputs
- Assets
- Performance
- Learnings
- Review Needed
- Change History

## Experiment

- Controlled Profile
- Hypothesis
- Audience
- Method
- Metrics
- Results
- Learnings
- Decision
- Follow-Up
- Review Needed
- Change History

## Product

- Controlled Profile
- Live Intelligence
- What It Is
- Problems Solved And Value
- Key Features
- Pricing And Packaging
- Differentiation
- Proof
- Objections And Risks
- Linked Entities
- Evidence
- Review Needed
- Change History

## Customer Success

- Controlled Profile
- Live Intelligence
- Account Health
- Adoption And Usage
- Risks And Churn Signals
- Expansion Opportunities
- Renewal
- Stakeholders
- Linked Entities
- Evidence
- Review Needed
- Change History

## Where Conclusions Go

- Company-level conclusions stay in Company.
- Person-level conclusions stay in Person.
- Deal-level conclusions stay in Deal.
- Event-level conclusions stay in Event.
- Messaging and positioning reusable across accounts should become Buyer Persona, Pain Point, Objection, Use Case, Case Study or Competitor Intel.
- Evidence stays in News, Article, Call, Source, Claim or Event Participation.
- What we sell (positioning, features, pricing, differentiation) lives in Product; deal-specific economics stay in Deal.
- Post-sale conclusions (health, adoption, renewal, expansion, churn risk) live in Customer Success; new-business pursuit stays in Deal.

## Adding A New Card Type

When you introduce a new card type, update every touch-point so the type stays consistent across templates, vocabularies, navigation, dashboards and the health check. The canonical list also lives in `AGENTS.md`:

- the entity `_template.md` for the new type under `wiki/entities/<type>/`
- `wiki/processes/card-taxonomy.md` (this file): list the type and its required sections
- `wiki/processes/property-vocabularies.md`: allowed property values for the type
- `wiki/index.md`: add the template to the relevant index section
- a relevant dashboard, when the type should appear in a team view
- `REQUIRED_FILES` in `scripts/health_check.py`, only if it is a required doc

## Agent Rule

When creating or updating a card, agents must follow the template for that card type. If a section is not yet known, keep the section and leave it blank or mark `needs-research`; do not invent a custom structure.
