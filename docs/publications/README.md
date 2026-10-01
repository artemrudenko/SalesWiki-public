# SalesWiki DEV publication kit

This folder contains the ready-to-edit five-part DEV Community series. The
articles explain the product and its trade-offs next to the code, diagrams and
installation instructions they reference.

## Recommended publishing order

1. `devto-01-why-saleswiki.md`: how scattered sales and marketing context
   becomes a decision someone can check.
2. `devto-02-permissioned-architecture.md`: how the same knowledge safely serves
   different roles and governed changes.
3. `devto-03-one-decision-pilot.md`: how to choose one repeated decision and
   test whether cited context improves it.
4. `devto-04-safe-private-pilot.md`: how to move from a synthetic demo to a
   private pilot without confusing their data boundaries.
5. `devto-05-vendor-first-integrations.md`: how CRM, document and chat context
   connects without moving vendor complexity into the core.

The five DEV articles use the same `series` value in front matter, so DEV can
group them. DEV supports no more than four tags per article. Its editor uses
Markdown with Jekyll front matter and supports uploaded images. See the
[official DEV editor guide](https://dev.to/p/editor_guide).

Use [`LINKEDIN_PARTS_02_05.md`](LINKEDIN_PARTS_02_05.md) for the matching short
posts, attachment files, alt text and publication sequence.

## Before publishing

- Add the public Git remote, push the release branch and verify the repository
  opens without authentication.
- Run the checklist in `../REPOSITORY_CONTENTS.en.md` against the exact staged snapshot.
- Use the Trace covers in `assets/publication/` at the recommended 2.38:1
  ratio. Check the actual URL in each article before publishing: some images
  are hosted on DEV and others in the public repository. Parts 3–5 have
  DEV-hosted covers. Part 3's diagram is also hosted on DEV. Parts 4 and 5
  currently use a table and text diagrams in place of their older pale images;
  `diagrams/saleswiki-data-boundary-article.{svg,png}` is a dark, mobile-checked
  replacement for Part 4 if it can be uploaded and verified in the editor.
- Keep `published: false` until the preview has been checked.
- Test every installation command from a fresh clone of the public repository.
- Recheck the public-preview limitations. Do not imply that fixture identity,
  connectors or hosted production operations are already complete.
- Each draft already contains a **Continue the series** section with readable
  previous/next labels. Never link to an unpublished DEV draft. When a part goes
  live, replace the matching labels in its adjacent published parts with the
  real DEV URL. This keeps every visible link working while the series grows.
- For a LinkedIn short post, use one primary destination that matches the post's
  action: the Workbench for a product tour, or the published DEV article for a
  writing-led post. The longer LinkedIn article can also link to the repository.

## Diagram files

Most architecture diagrams have four forms under `diagrams/`:

- `.mmd` is the Mermaid source.
- `.excalidraw` is editable at [excalidraw.com](https://excalidraw.com/).
- `.svg` is best for repository docs and high-resolution publishing.
- `.png` is ready for DEV and other publishing surfaces.

The Part 3 editorial decision loop has Mermaid source, SVG, and PNG. Its SVG
uses a vertical layout for mobile reading.

## Part 2 visual map

`diagrams/saleswiki-role-contexts.{mmd,svg,png}` belongs after the BluePeak Energy example in Part 2. It shows one shared account evidence map becoming two permitted, decision-specific views. **Alt text:** One shared account evidence map is filtered by policy into a sales-rep view for the next customer conversation and a marketing view for campaign context. Both answers retain citations, freshness, and what is missing.

## Editorial position

The series follows one learning journey: how can sales and marketing teams turn
scattered context into decisions they can trust? "Finding a solution" means
narrowing the options with cited, permitted evidence while leaving the final
choice with the person. Each article answers a narrower question about the
knowledge model, permission boundary, pilot or integrations.

The wiki model comes before the assistant in this story. One set of linked cards
holds the current shared understanding; raw evidence is preserved; proposals,
review records and history explain changes; role policy creates permitted views.
External systems can remain the source of their original records.

The strongest honest product claim is narrow: SalesWiki is a public-preview
starter kit for teams that need cited extraction, governed changes and an owned
Markdown data plane at the same time. It is not a CRM replacement or a finished
hosted enterprise product.
