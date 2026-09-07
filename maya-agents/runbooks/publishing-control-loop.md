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
- Postiz channel/integration IDs when social accounts are connected

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

6. **Postiz platform gate**
   - Postiz is the publishing buffer between Maya Agent OS and TikTok/YouTube/Instagram.
   - The guarded publisher defaults to `draft`; it does not publicly publish by default.
   - A public `schedule` or `now` operation requires explicit `--confirm-publish`.
   - Maya TikTok video payloads set `video_made_with_ai=true` and keep visible AI/virtual-creator disclosure text.
   - TikTok `--tiktok-upload-only` sends media to the TikTok app inbox for manual completion instead of direct posting.
   - Only mark `PUBLISHED` after Postiz returns a real `postId` and the target-platform result is actually successful.
   - Never manufacture a publish URL or timestamp.

7. **Measurement gate**
   - Capture actual metrics at comparable windows, initially 24h and 72h.
   - Unknown metrics remain null/unknown, never zero by assumption.
   - Postiz analytics may be ingested later, but platform/site/affiliate measurements remain the source of truth for business decisions.

8. **Optimization handoff**
   - Analytics Agent computes retention/funnel metrics when inputs exist.
   - Growth Optimizer selects controlled variants.
   - Orchestrator may schedule at most two new content experiments per day until sufficient data exists.

## Postiz setup

The implementation lives in:
- `backend/app/connectors/postiz.py`
- `backend/run_postiz_social.py`

Required backend environment variables:

```text
POSTIZ_API_KEY=
POSTIZ_API_BASE_URL=https://api.postiz.com/public/v1
```

Connect Maya's social accounts inside Postiz first, then inspect the real channel IDs:

```bash
cd backend
python run_postiz_social.py integrations
```

Create a review-first draft from a public HTTPS video URL:

```bash
python run_postiz_social.py publish \
  --mode draft \
  --content-id V001 \
  --integration-id <tiktok-integration-id> \
  --integration-id <youtube-integration-id> \
  --title "AI picked my 10-minute makeup look" \
  --caption "<approved caption>" \
  --media-url "https://cdn.example.com/maya-v001.mp4"
```

Schedule only after proof, destination and compliance gates pass:

```bash
python run_postiz_social.py publish \
  --mode schedule \
  --confirm-publish \
  --scheduled-at "2026-09-08T19:00:00+02:00" \
  --content-id V001 \
  --integration-id <tiktok-integration-id> \
  --title "AI picked my 10-minute makeup look" \
  --caption "<approved caption>" \
  --media-url "https://cdn.example.com/maya-v001.mp4"
```

Do not commit the Postiz API key. The command output records real Postiz post IDs, channel IDs and schedule mode without echoing the secret.

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
- Postiz integration IDs
- Postiz draft/schedule/post IDs
- planned publish order
- metrics checkpoint fields

## Safety invariants

- Publishing content is reversible; financial, KYC, tax, account-owner and paid-ad actions are not autonomous.
- Public Postiz scheduling/publishing requires explicit human confirmation; drafts do not.
- No spend or paid subscription without human approval.
- No public health/medical claims without review.
- No fake reviews, testimonials, product tests, prices, discounts, follower counts or sales results.
- No product link just because a commission is attractive.

## Current execution

- V001: rendered; Postiz transport is implemented, but publication remains blocked until the Maya site destination is live and a real Postiz API key + connected social channel IDs are configured.
- V002: HeyGen render `11f0491307c481b45fb469fb7f1bb86c`; proof review required after render.
- `EXP-BEAUTY-GADGET-01`: future experiment; not canonical V002.
