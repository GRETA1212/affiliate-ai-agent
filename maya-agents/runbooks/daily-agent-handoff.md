# Maya.exe daily agent handoff protocol

This file defines who owns each stage of the operating loop and what must exist before the next agent may act.

## 1. Trend Scout → Orchestrator

**Input:** current Italy beauty / beauty-tech / creator-tool evidence.

**Must output:**
- opportunity name
- evidence date
- source(s)
- demand signal
- buyer-intent signal
- repeatability angle
- monetization angle
- risk/unknowns
- confidence

**Block:** no current evidence = no trend claim.

## 2. Orchestrator → Product Scout / Content Strategist

The Orchestrator selects no more than two new experiments per day during the validation phase.

A selected experiment must have:
- one primary hypothesis
- one audience problem/curiosity
- one measurable success metric
- one content ID

## 3. Product Scout → Commerce & Compliance

Only needed when a specific product/listing is involved.

**Must output:** exact product, seller/merchant, exact destination URL, current price if used publicly, commission if relevant, seller-quality evidence, sample status, and evidence date.

**Block automatically when:**
- listing is not verified
- seller is unclear
- discount is unverified
- planned script requires a test that did not happen
- planned claim is medical/efficacy-related without adequate evidence

## 4. Content Strategist → Script Producer

**Must output:**
- content ID
- audience problem
- Hook A
- Hook B
- story arc
- proof/demo required
- destination page
- success metric

Script Producer may not invent missing proof.

## 5. Script Producer → Commerce & Compliance

**Must output:** spoken script, shot list, on-screen text, caption, CTA, disclosure, product proof needed.

Commerce & Compliance returns one state only:
- `approved`
- `blocked`
- `needs_human_review`

Any spend, KYC/tax/bank action, new paid subscription, new affiliate agreement, paid ad launch, or material health/legal claim requires human approval.

## 6. Approved creative → Publishing Planner

Publishing Planner creates platform-specific entries.

### Required tracking

TikTok:
`utm_source=tiktok&utm_medium=organic&utm_campaign=launch&utm_content=<content_id>`

YouTube:
`utm_source=youtube&utm_medium=organic&utm_campaign=launch&utm_content=<content_id>`

Never claim a link is clickable where the platform does not support that behavior.

## 7. Publishing Planner → Human publish action

The system prepares the exact caption/title/CTA, but publishing remains a human-controlled action until a legitimate connected publishing tool exists.

Record the real publication timestamp immediately after posting.

## 8. Human/platform data → Analytics Agent

Collect after comparable windows, initially 24h and 72h when practical.

Required values where the platform exposes them:
- views
- watch time / retention
- engagement
- follows gained
- profile visits
- site sessions
- affiliate clicks
- orders
- leads
- revenue

Unknown values remain blank/unknown. Never replace missing values with zero.

## 9. Analytics Agent → Growth Optimizer

Before revenue exists, rank primarily by:
- site sessions per 1,000 views
- retention/watch quality
- follows/profile intent as supporting signals

After revenue exists, rank primarily by:
- revenue per 1,000 views
- order conversion
- lead value where relevant

## 10. Growth Optimizer → Orchestrator

For enough comparable observations:
- top quartile: propose 3 controlled variations
- bottom quartile: pause unless a documented strategic reason exists
- change one major creative variable at a time when testing causality

## 11. Orchestrator → next-day queue

The next-day queue contains only:
- production-ready items
- blocked items with the exact missing evidence
- human approvals required
- one or two new experiments
- follow-ups to current winners

# Daily operating cadence

**Morning:** Trend Scout + Orchestrator choose opportunities.

**Production block:** Content Strategist → Script Producer → Compliance.

**Publish block:** Publishing Planner prepares TikTok/YouTube versions; human publishes.

**Measurement block:** Analytics updates real data.

**Optimization block:** Growth Optimizer chooses scale/pause/next test.

# North-star rule

The system is not rewarded for producing more content. It is rewarded for finding repeatable content that produces measurable attention, intent, leads, orders, or revenue without misleading viewers.
