# SalesWiki DEV publication kit

This folder contains the ready-to-edit four-part DEV Community series. The
articles explain the product and its trade-offs next to the code, diagrams and
installation instructions they reference.

## Recommended publishing order

1. `devto-01-why-saleswiki.md`: how scattered sales and marketing context
   becomes a decision someone can check.
2. `devto-02-permissioned-architecture.md`: how the same knowledge safely serves
   different roles and governed changes.
3. `devto-03-install-and-pilot.md`: how to test one repeated decision between a
   synthetic demo and a private pilot.
4. `devto-04-vendor-first-integrations.md`: how CRM, document and chat context
   connects without moving vendor complexity into the core.

The four DEV articles use the same `series` value in front matter, so DEV can
group them. DEV supports no more than four tags per article. Its editor uses
Markdown with Jekyll front matter and supports uploaded images. See the
[official DEV editor guide](https://dev.to/p/editor_guide).

## Before publishing

- Add the public Git remote, push the release branch and verify the repository
  opens without authentication.
- Run the checklist in `../REPOSITORY_CONTENTS.en.md` against the exact staged snapshot.
- The DEV front matter points at the repository-hosted Trace cover images in
  `assets/publication/`. They use the recommended 2.38:1 cover ratio. The
  article diagrams use absolute public-repository URLs, so they remain visible
  after the Markdown is pasted into DEV. Upload copies to DEV if you prefer
  platform-hosted media.
- Keep `published: false` until the preview has been checked.
- Test every installation command from a fresh clone of the public repository.
- Recheck the public-preview limitations. Do not imply that fixture identity,
  connectors or hosted production operations are already complete.
- Add the published URL of part 1 to parts 2, 3 and 4, and link forward as each
  new part goes live.

## Diagram files

Each diagram has four forms under `diagrams/`:

- `.mmd` is the Mermaid source.
- `.excalidraw` is editable at [excalidraw.com](https://excalidraw.com/).
- `.svg` is best for repository docs and high-resolution publishing.
- `.png` is ready for DEV and other publishing surfaces.

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
