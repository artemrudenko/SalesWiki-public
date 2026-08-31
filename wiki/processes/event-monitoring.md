# Event Monitoring

Use this process to track exhibitions, conferences, summits, webinars and industry events.

For configurable pilot limits, required outputs and action thresholds, follow `event-research-profile.md` and `schemas/event-research-profile.json`.

## What To Collect

For each event:

- official event website
- agenda and session pages
- speaker list
- exhibitor list
- sponsor list
- partner list
- award/finalist pages
- press releases from organizers
- posts from participating companies and executives
- side events and networking sessions

## Entities To Extract

- Event
- Company
- Person
- Topic
- Sponsor level
- Exhibitor booth/stand
- Session
- Participation type
- Date/time
- Location
- Source

## Research Questions

- Which target accounts are participating?
- Which companies are sponsoring?
- Which executives are speaking?
- Which topics are gaining attention?
- Which competitors are present?
- Which sessions indicate buying intent or category movement?
- Which leads should sales contact before or after the event?
- Which topics should marketing turn into content or campaigns?

## Update Rules

1. Save raw event pages or references under `raw/events/`.
2. Create or update `wiki/entities/events/Event - <Name>.md`.
3. Create participation notes when a company/person role matters.
4. Link companies, people, leads, deals, campaigns and ICP pages.
5. Add event-derived signals to company and person pages.
6. Add outreach tasks for relevant owners.
7. Append the update to `wiki/log.md`.

## Freshness Rules

- Active event watchlist: check weekly.
- Event less than 30 days away: check twice per week.
- Event week: check daily if sales is using it for outreach.
- Post-event: run a wrap-up within 5 business days.

## Outputs

Useful outputs for employees:

- event brief
- target account attendee list
- speaker/executive list
- sponsor intelligence
- topic trend summary
- pre-event outreach list
- post-event follow-up list
- event ROI and action report

For event outcome tracking, follow `event-roi-action-loop.md`.

## Collection Method

Default to public web fetch and official source references. Use `playwright-cli` only when the `web-research` connector contract allows it: JavaScript-rendered pages, filters, tabs, pagination, expandable agendas or screenshot/PDF evidence. Do not use browser automation for mass scraping, restricted social automation, paywall bypass or form submission without explicit approval.
