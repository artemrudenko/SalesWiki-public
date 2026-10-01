---
title: "What should a sales knowledge base help someone decide? — SalesWiki, Part 3 of 5"
published: false
description: Pick one recurring sales or marketing decision and test whether a short answer with sources helps someone make it.
tags: sales, marketing, ai, productivity
series: Building SalesWiki in the open
cover_image: https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/vj8fblzquo30wjasg1xm.png
---

An assistant can summarize every account in a pipeline and still leave a salesperson with the same question: which account needs my attention today?

Earlier in this series, I wrote about why sales and marketing need shared knowledge and why different people should see different parts of it.

Now I want to learn whether that knowledge helps someone make one recurring decision with less searching and a clear view of the evidence. A larger wiki or a longer summary is not useful by itself.

For sales, the question might be which account to follow up with next. For marketing, it might be which customer signal should change a campaign plan. Each needs a different answer from the same shared account context. In this part, I use the sales question to design a small test before connecting more tools or moving real customer data.

## Start with a decision card

The test should fit on one page before anyone connects a customer system or uploads a call transcript.

| Question | Example: account follow-up priority |
| --- | --- |
| Person making the decision | Account executive |
| Repeated moment | Morning pipeline review |
| Decision | Which account should I follow up with next? |
| Facts the person may see | An account they own, dated call notes, confirmed next step |
| Useful output | A suggested next step with sources and any gaps |
| Human remains responsible for | Choosing what to do and contacting the customer |

This is narrower than asking an assistant to "improve sales." A specific decision tells us what information matters, who may see it, and how to tell whether the answer helped.

## Information has to earn a place in the answer

The test should not reward a longer account summary. I would use a simple rule instead:

| Evidence state | What the short answer should do |
| --- | --- |
| The person is not allowed to see it | Leave it out entirely |
| It is allowed but would not change this decision | Keep it in the linked account context, not in the short answer |
| It could matter but is old, incomplete, or contradictory | Say what needs checking |
| It is allowed, dated, and could change the decision | Include it with its source |

The short answer needs the last two rows: useful facts with sources, and gaps that could change the choice. This is a working rule for the test, not a relevance score that SalesWiki claims to calculate today. The question is whether a smaller set of checkable facts helps more than a complete-looking summary.

## A useful answer makes uncertainty visible

Imagine a made-up morning review of two accounts. BluePeak has a call note from yesterday and a confirmed next step due today. Cedar has a high score, but its last call note is old and nobody is named as the owner of the next step. Which account would you follow up with first?

I would not want an answer that puts Cedar first because of its score alone. A useful answer might point to BluePeak's dated next step and say that Cedar needs a quick check before its priority can be trusted. A person can then choose the action; the answer should make the reason easy to inspect.

SalesWiki's answer format keeps sources, dates, and missing facts beside the conclusion. It can narrow the search and suggest a direction. It should not hide the person's choice inside confident prose.

![A decision loop: choose one follow-up question, check permitted and dated facts, then either give a sourced direction or say what needs checking; a person makes the next move and sends corrections for review](https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/rhuwp7z4g81w7xkez8i2.png)

## Test the current workflow against the proposed one

I would compare the team's usual account records and notes with a short, sourced answer for the same decision. The team would keep its normal tools. There is no need to move everything into SalesWiki first.

Before trying it with real work, I would agree on the question, allowed sources, and what counts as a failed answer. An unsupported claim, someone seeing a restricted record, or a person unable to explain the suggested step would be a failure. A smoother prompt would not fix it.

Then record four observations:

1. How long it takes to prepare the decision.
2. Whether the person can point to a dated source for the action.
3. Whether an old or missing fact changes the choice.
4. Whether a correction to shared knowledge is needed, and how much review work it adds.

An old note should trigger a check, not quietly lower an account's priority. If
the same stale facts keep appearing, the pilot should also ask where the review
loop failed. Part 4 describes a small way to record that history without
copying customer details into a public project.

I would also ask what the person would have done without the answer. Faster preparation means little if it leads to a worse decision. If people only need faster document search, an existing search tool may be enough. If maintaining the shared facts takes more work than the decision is worth, that matters too.

## What the public demo can and cannot show

The public [Knowledge Workbench](https://knowledge-workbench-seven.vercel.app/) uses synthetic accounts. Its guided tour goes from a suggested priority to account context, linked evidence, an answer with sources, and a review path for corrections. It also shows how to treat a stale signal: check the dated evidence before acting or deprioritizing, and leave the cause unknown unless review history supports it. The demo does not contain that history or diagnose the cause.

The demo cannot show whether a real team would use this every day. It has no real user sign-in, live customer records, or hosted setup for a team. That is the job of a later private pilot, with a separate place for customer data. When facts are old or missing, saying what to check can be more useful than recommending an action.

## Continue only when the workflow earns it

I would consider a private pilot only if the small test supports these points:

1. The answer helps people make the chosen decision with less searching, without hiding a fact that could change it.
2. People can point to the sources, explain their choice, and say what would change their minds.
3. Corrections to shared knowledge are worth the review effort.
4. The time spent keeping the answer current is reasonable for the value of the decision.

The next part looks at how to run that private test without confusing synthetic demo data with customer data. It covers the public repository, local demo, private vault, and the safeguards still needed.

## Continue the series

**Previous:** [How I keep shared sales knowledge safe for different roles](https://dev.to/artemr_rudenko_0bf2c2c505/how-i-keep-shared-sales-knowledge-safe-for-different-roles-saleswiki-part-2-of-5-1ngl)

**Next:** *From synthetic demo to a safe private pilot.*
