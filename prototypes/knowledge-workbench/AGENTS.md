# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

## Approved direction

- Use the dark, graph-led Entity Explorer selected in the August 2026 design review.
- The UI must be data-driven. Never create or require a unique screenshot, illustration, or manually positioned design for each company.
- Render companies, people, deals, calls, competitors, and sources with reusable typed node components and a normalized relationship contract.
- Default to a focused one-hop account graph. The graph supports decisions; it is not a decorative global hairball.
- Keep evidence, freshness, confidence, citations, and access state visible near every conclusion.
- Never edit the source vault directly from the UI. Writes become proposals, then pass through review, an authorized worker, validation, and audit.
- Keep the main non-technical path short: choose an account, understand what matters, inspect evidence, ask in context, or propose an update.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.
