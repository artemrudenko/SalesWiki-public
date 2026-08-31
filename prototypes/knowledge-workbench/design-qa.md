# Design QA — SalesWiki Knowledge Workbench

## Evidence

- Source visual truth: `/Users/artemrudenko/.codex/generated_images/01a02172-6723-7493-a4c5-7c29033486d2/exec-5465f626-89c3-40d7-8801-d69d7f8caa2e.png`
- Browser-rendered implementation: `/Users/artemrudenko/projects/Work/SalesWiki/prototypes/knowledge-workbench/implementation-1440x1024.png`
- Combined full-view comparison: `/Users/artemrudenko/projects/Work/SalesWiki/prototypes/knowledge-workbench/design-comparison.png`
- Combined large comparison: `/Users/artemrudenko/projects/Work/SalesWiki/prototypes/knowledge-workbench/design-comparison-focus.png`
- Intended CSS viewport: `1440 × 1024`
- Source pixels: `1487 × 1058`
- Implementation pixels: `1440 × 1024`
- Density: browser capture at device scale 1. The comparison page normalizes both artifacts to the same `1440 / 1024` aspect ratio; the 3% source-size difference is not treated as design drift.
- State: BluePeak Energy, full one-hop graph, company node selected, dark theme.

## Findings

No actionable P0, P1, or P2 differences remain.

- Fonts and typography: IBM Plex Sans and IBM Plex Mono reproduce the compact enterprise/investigator character of the reference. Heading scale, uppercase micro-labels, metadata density, truncation, and line height remain readable at the target viewport.
- Spacing and layout rhythm: the left rail, utility header, graph canvas, right context panel, and bottom evidence trace preserve the reference hierarchy. The implementation gives the graph slightly more working room and keeps all persistent controls visible at `1440 × 1024`.
- Colors and visual tokens: charcoal surfaces, blue selection/contact states, green evidence/deal states, amber competitive risk, and purple interaction links map to the reference. The implementation uses flat fills and borders; there are no substitute gradients or decorative CSS art.
- Image quality and asset fidelity: the target contains no required product photography, illustration, or per-company imagery. Visible symbols use Phosphor icons and the graph is rendered from typed data. No screenshot or generated asset is required at runtime.
- Copy and content: all text is coherent as a standalone SalesWiki experience. Synthetic account details are grounded in the repository demo contour. The implementation intentionally replaces the reference's long right-panel conclusion list with a shorter decision summary plus evidence and context; this is an acceptable product constraint that improves the one-minute scan goal without changing the visual hierarchy.
- Icons: all visible UI and entity icons use one library at consistent optical sizes. React Flow owns graph handles, arrows, and controls.
- Accessibility: controls are semantic buttons, form fields have labels, focus indicators are visible, text/background contrast is strong, and primary actions remain keyboard reachable.
- Responsiveness: the approved artifact is a dense desktop workbench. A `1280px` compact desktop rule preserves the two-panel hierarchy; narrower/mobile layouts are intentionally outside this prototype scope.

## Interaction verification

- Switched from BluePeak Energy to Atlas Foods; graph, detail panel, sources, conclusion, and score updated from the same reusable schema.
- Applied the People filter and verified the account-specific person node.
- Opened the governed proposal form, entered a change and source, submitted it, and received the review-queue success state.
- Opened Ask in context, entered a question, and received the current account conclusion with citation metadata.
- Verified empty-search recovery and node/evidence selection behavior during the implementation pass.
- Browser console errors and warnings checked: none.

## Production-state verification

- Loading waits for the access decision and contract check before showing graph content.
- Blocked, not-found, ambiguous and aggregate-only responses render dedicated safe states instead of entering the layout adapter.
- The blocked screen contains no deal, competitor, source or hidden entity detail.
- Stale and truncated payloads keep the usable graph visible while adding a dismissible explanation.
- Unsupported or malformed GraphView responses fail closed with a retry/reference state.
- The scenario selector is hidden in the normal product surface and appears only with `?dev=1` or an explicit `?state=` test URL.
- `Cmd/Ctrl+K` focuses account search and `Escape` closes the contextual overlays.
- A clean browser load of the final default and blocked states produced no console warnings or errors.

## Real MCP transport verification

- Started the loopback Workbench BFF with the tracked synthetic-demo profile
  and a server-resolved fixture actor.
- Loaded the UI with the same-origin `/api/v1/entity-graph` transport. The
  screen identifies the server-resolved demo person; with fixture persona
  switching enabled, it offers only the allowlisted synthetic people and never
  accepts a client-chosen role.
- BluePeak rendered 7 authorized nodes, 6 relationships and 7 evidence records
  returned by the real `saleswiki.entity_graph` MCP stdio tool.
- Switched to Atlas Foods using its stable entity ID; the same adapter and layout
  rendered the different company graph without account-specific UI code.
- Root decision copy comes from GraphView summary, technical boundary metadata
  is not shown as business context, and the clean browser load has no warnings or
  errors.

## Comparison history

### Pass 1

- Full-view and large combined comparisons found no P0/P1/P2 mismatch.
- No fidelity fix loop was required.
- Post-comparison build and interaction verification remained clean.

## Follow-up polish

- [P3] A production build may add a user-controlled relationship legend. The color/label mapping is already visible on edges, so this does not block comprehension.
- [P3] A production build should define tablet and mobile read-only views after real usage confirms which account details deserve priority.

## Visual iteration — 2026-08-30

- Replaced the browser-native account and synthetic-person selectors with dark
  product menus. The selected state, role and account code stay readable on the
  same dark surface as the workbench.
- The person menu opens inward from the right edge, preventing clipping at the
  supported desktop width.
- Updated the UI typography to DM Sans + Fragment Mono and introduced a subtle
  blue/green background treatment that preserves the investigation-workbench
  feel without adding decorative noise.
- Added a small “Workspace pulse” strip to Today. It states the visible action
  count, freshness and whether access is scoped before a user starts scanning
  cards.
- Browser check: account and person menus are fully visible, use readable
  contrast and leave the primary content recognisable behind the overlay.

## Implementation checklist

- [x] Data-driven account switching
- [x] Reusable typed nodes and relationships
- [x] Evidence trace and source status
- [x] Contextual node selection and filters
- [x] Governed proposal interaction
- [x] Contextual question interaction
- [x] Production build and Sites package tests
- [x] Browser interaction and console verification
- [x] Safe loading, access, missing-data and contract-error states
- [x] Injectable MCP client boundary with layout-neutral GraphView adaptation

final result: passed
# Layout and alignment audit — 2026-08-29

Scope: Today, Entity Explorer and the controlled-import review dialog at a
desktop width of 1280px.

Visual evidence: [`audit-2026-08-29-import-review.png`](audit-2026-08-29-import-review.png).

| Step | Health | Finding and resolution |
| --- | --- | --- |
| Today | Good | The daily cards share a clear left edge and title baseline. No change required. |
| Entity Explorer | Fixed | The grid had minimum row heights larger than a short desktop viewport, clipping the graph/evidence composition. The shell now has a bounded viewport height and a flexible graph row. The top bar now keeps the Polish starter and access state in one action group. |
| Import review | Fixed | Draft type, content and status are now aligned on stable grid tracks with a shared vertical center, making each proposed card easier to scan. |

Small labels in the graph and evidence panel were increased slightly for better
legibility. Screenshot review cannot prove keyboard focus order, contrast ratios
or responsive behaviour below the supported desktop minimum; those require a
separate accessibility and responsive test pass.
