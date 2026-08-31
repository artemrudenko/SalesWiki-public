# Obsidian Vault

SalesWiki is designed to work as an Obsidian vault from day one.

## Why Obsidian Fits

- The knowledge base is Markdown-first.
- `[[wikilinks]]` and backlinks naturally represent company, person, lead, deal and news relationships.
- Graph view gives a useful first relationship map without implementing a custom graph database.
- Properties/YAML frontmatter make notes both human-readable and machine-readable.
- The vault can still be processed later by agents, scripts, vector indexes or graph exports.

## Recommended Core Features

Enable these Obsidian core features:

- File explorer
- Search
- Backlinks
- Graph view
- Outgoing links
- Page preview
- Properties view
- Templates
- Daily notes, if the team wants daily research logs
- Bases, if available in your Obsidian installation, for the `.base` dashboards in `dashboards/`

## Agent Obsidian Skills

For agent-assisted work, install and use the Obsidian skills described in `wiki/processes/obsidian-skills.md`.

The practical split:

- Obsidian is the human UI for notes, properties, graph and dashboards.
- SalesWiki templates and process docs define the business rules.
- Agent skills help produce valid Obsidian artifacts, but do not decide governance or overwrite protected fields.

## Properties

Use properties for atomic workflow fields:

- `type`
- `status`
- `owner`
- `company`
- `person`
- `deal`
- `source`
- `created`
- `last_reviewed`
- `freshness`
- `confidence`
- `access`
- `tags`

Do not put long summaries or nested data in properties. Put analysis, tables and evidence in the page body.

## Links

Use links in two places:

- Properties, when the relationship is structured and useful for filtering.
- Body text, when the relationship should be visible to humans and obvious in graph exploration.

Examples:

- `Company: [[Company - Acme]]`
- `CEO: [[Person - Jane Doe]]`
- `Related deal: [[Deal - Acme - Expansion]]`

## Naming

Recommended page names:

- `Company - <Name>`
- `Person - <Name>`
- `Lead - <Company> - <Name>`
- `Deal - <Company> - <Opportunity>`
- `Call - <Company> - <YYYY-MM-DD> - <Topic>`
- `News - <YYYY-MM-DD> - <Short Headline>`
- `ICP - <Segment>`
- `Campaign - <Name>`

## Sharing

Start simple:

1. One shared vault for internal team use.
2. Access controlled by filesystem, Git repo, Obsidian Sync, or another approved sync layer.
3. Sensitive pages marked with `access: sales-confidential` or `access: personal-data`.
4. Sanitized summaries can be copied to public/internal pages when needed.

Obsidian Publish can work for curated read-only publishing, but do not publish raw calls, leads, deals or personal data.

## Future Extensions

Useful later, after the manual workflow proves itself:

- Dataview-like reports for hot leads, stale deals and recent news.
- Git-based review for sensitive changes.
- Agent-generated graph export in `indexes/graph/`.
- Vector index over `wiki/` for semantic search.
- Slack/CRM interface that reads from the vault and writes reviewed updates back.
