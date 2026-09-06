# Maya.exe Free-Mode Fallback

Purpose: keep the Maya publishing loop moving when paid or quota-limited video generation is unavailable.

## Trigger conditions

Switch a release to `free_image_short` when any of these is true:
- HeyGen avatar/video quota is exhausted.
- The configured backup video provider does not expose video generation on the current plan.
- A video render fails twice for provider-capacity/account-limit reasons.

Do not silently change the content ID. V002 remains V002 whether it is produced as avatar video or image-led short.

## Output format

Create a 9:16 image-led short package using 4–6 visual cards or stills:
1. Hook card / Maya hero still.
2. Problem or claim card.
3. Evidence/comparison card.
4. Second evidence/comparison card.
5. Resolution or takeaway card.
6. CTA + visible `Virtual AI creator` disclosure.

Use simple zoom/pan, cuts, text overlays and optional voiceover when available. Do not imply live action, physical testing, product ownership or product use unless documented evidence exists.

## V002 free-mode package

Content ID: `V002`
Title: `3 Things AI Got Wrong`

Hook:
`AI picked the look. Here are the three things it got wrong.`

Card 1 — Hook
On-screen: `3 THINGS AI GOT WRONG`
Visual: Maya reaction / final-look-style beauty portrait.

Card 2 — Problem 1
Copy: `1. Too much eye definition for a real 10-minute routine.`
Visual: simple heavier-vs-softer eye-direction comparison. This is an aesthetic/time critique only.

Card 3 — Problem 2
Copy: `2. The first blush direction fought the lip.`
Visual: two color-direction swatches or controlled face mockups.

Card 4 — Problem 3
Copy: `3. It optimized the perfect-looking version — not the fastest practical one.`
Visual: too-many-steps card vs simplified routine card.

Card 5 — Takeaway
Copy: `AI is useful for options. Judgment is still the filter.`

Card 6 — CTA
Copy: `Should Maya make AI fix all three?`
Disclosure: `Maya.exe · Virtual AI creator`

## Audio

Preferred order:
1. Existing approved Maya voice if available without paid generation.
2. Platform-native voiceover/TTS after upload.
3. Music + burned text only.

Never fabricate a Maya speech recording or claim a voice was generated when it was not.

## Publishing behavior

The publishing agent may mark the package `ready_for_manual_assembly` once all cards, copy, CTA and disclosure are prepared.
It may mark `ready_to_publish` only after a final exported short exists and platform access is available.
Actual publish timestamp and analytics are populated only from the real platform event.

## Commerce safety

No product links, prices, discounts or performance claims are allowed in free-mode V002. It remains a pre-commerce trust-building experiment.
