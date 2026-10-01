# Method Library Intake

The method library is a small, governed collection of reusable sales and
marketing decision lenses. It exists to make task framing and evaluation more
complete, not to turn a general textbook into an unbounded source of facts.

## Boundary

Method sources may inform:

- question checklists;
- response shape for a named role × task pair;
- synthetic evaluation rubrics;
- proposed taxonomy or playbook gaps.

They may not:

- establish a fact about an entity, deal, person, campaign or market;
- change access policy, redaction, citations, freshness or `missing`;
- change scoring weights or actions without the approved scoring-configuration
  flow;
- enter the Answer Contract as unlabelled factual content.

## License Gate

Before accepting a book, guide, course or report:

1. Record the canonical publisher URL, edition, author, publisher, collection
   date and exact license.
2. Separate `free to read` from permission to copy, adapt, redistribute or use
   in a generative system.
3. Prefer CC BY, CC0 or public-domain content for a public repository.
4. Treat CC BY-NC, CC BY-NC-SA, paid and restricted works as link-only until a
   private-store and commercial-use decision is explicitly approved.
5. Inspect exceptions for images, videos, case studies, assessments, linked
   tools and other third-party material.
6. Save a dated manifest under `raw/research/oer-method-library/`; do not
   revise that manifest after collection.

## Intake Outputs

For an accepted source, create or update:

1. a `Source - ...` card with canonical URL, source-access type, restrictions,
   raw manifest path, hash and review date;
2. an entry in `tracking/processed-sources.md`;
3. an ingest-run row and `wiki/log.md` entry;
4. a small method note under `wiki/methods/` only when a named decision and
   limitation are clear.

Do not create method notes merely because a source is available.

## Method Note Contract

Every note must state:

- status: `candidate`, `adopted` or `rejected`;
- one decision supported;
- a short, testable checklist;
- permitted prompt use;
- links to source cards and chapter/section references;
- limitations and facts the note may not infer.

## Prompt Change Gate

1. Name the role × task pair and the repeated decision.
2. Change only the presentation profile; never the access or fact boundary.
3. Add or update a synthetic scenario before enabling the change.
4. Render the exact prompt without a model call.
5. Run the presentation-contract test and compare baseline versus
   method-informed outputs on the pilot scenarios.
6. Keep the note `candidate` until a reviewer accepts the measured result.

See [[method-library-pilot]] and [[prompt-development-contract]].
