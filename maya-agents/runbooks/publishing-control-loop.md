# Maya.exe Publishing Control Loop

Purpose: turn a finished Maya creative into a publishable, measurable release without inventing platform actions, product facts, or analytics.

## Inputs
- `maya-agents/data/publishing-queue.json`
- canonical content spec for the selected content ID
- final video asset ID/URL
- platform account access state
- website destination state
- Commerce & Compliance result
- latest analytics for previously published items

## State machine

`IDEA -> SCRIPTED -> RENDERING -> RENDERED -> PROOF_REVIEW -> READY_TO_PUBLISH -> PUBLISHED -> MEASURING -> LEARNED`

Blocking states:
- `BLOCKED_SITE`
- `BLOCKED_PLATFORM_ACCESS`
- `BLOCKED_COMPLIANCE`
- `BLOCKED_PROOF`

The agent must never skip a blocking state by guessing missing information.

## Per-release loop

1. **Resolve canonical content ID**
   - Read `launch-queue-v001-v010.md`.
   - Reject duplicate meanings for the same `V###` ID.
   - Experimental renders get `EXP-*` IDs until promoted deliberately.

2. **Resolve production asset**
   - Confirm final video exists and belongs to the selected content ID.
   - Record real asset/video ID.
   - Do not mark `rendered` while generation is still processing.

3. **Proof review**
   - Every factual or comparative statement in the script must have visible/source proof.
   - If proof is absent, remove/rewrite the claim or block publication.
   - Synthetic/virtual creator disclosure stays explicit.

4. **Commerce & compliance gate**
   - If no exact product listing is verified, publish only as pre-commerce content.
   - No price, discount, commission, product-use, efficacy, medical, or testing claims without evidence.
   - Affiliate links remain disabled until their destination and relationship are verified.

5. **Destination gate**
   - If CTA names a site page, verify it is live before publishing.
   - If the intended page is not live, use a truthful fallback CTA (profile/homepage/coming-soon) or block.

6. **Platform gate**
   - The planner may prepare captions, titles, tags, disclosure settings, UTM values and a posting checklist.
   - It may only mark `PUBLISHED` after the actual platform returns a successful publish result or a human records the real result.
   - Never manufacture a publish URL or timestamp.

7. **Measurement gate**
   - Capture actual metrics at comparable windows, initially 24h and 72h.
   - Unknown metrics remain null/unknown, never zero by assumption.

8. **Optimization handoff**
   - Analytics Agent computes retention/funnel metrics when inputs exist.
   - Growth Optimizer selects controlled variants.
   - Orchestrator may schedule at most two new content experiments per day until sufficient data exists.

## Platform package

For each approved release produce:
- master video asset reference
- TikTok caption
- YouTube Shorts title + description
- Instagram Reels caption when account is available
- AI/synthetic-media disclosure instruction
- affiliate/commercial disclosure instruction when applicable
- destination URL or truthful fallback
- `utm_campaign=launch`
- `utm_content=<content_id lowercase>`
- planned publish order
- metrics checkpoint fields

## Safety invariants

- Publishing content is reversible; financial, KYC, tax, account-owner and paid-ad actions are not autonomous.
- No spend or paid subscription without human approval.
- No public health/medical claims without review.
- No fake reviews, testimonials, product tests, prices, discounts, follower counts or sales results.
- No product link just because a commission is attractive.

## Current execution

- V001: rendered; publication blocked by site deployment + social publisher access.
- V002: HeyGen render `11f0491307c481b45fb469fb7f1bb86c`; proof review required after render.
- `EXP-BEAUTY-GADGET-01`: future experiment; not canonical V002.
