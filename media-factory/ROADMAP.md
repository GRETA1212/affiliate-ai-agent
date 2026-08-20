# Roadmap

What is deliberately not built yet, and why. The first milestone was one
complete vertical slice, not many half-integrations.

## Shipped

- [x] Multi-brand config (Maya.exe, Kids Learning), brands added by copying a folder
- [x] LangGraph orchestrator with a QA gate
- [x] Opportunity scout + niche scorer (25/20/20/15/10/10 minus saturation and risk)
- [x] Research agent with verified-fact vs assumption discipline
- [x] Strategist, script, storyboard, asset planner
- [x] Reusable 9:16 Remotion template + ffmpeg fallback renderer
- [x] 13-check QA gate
- [x] Publishing planner producing per-platform manual-upload manifests
- [x] Analytics schema + 25/50/25 growth optimizer
- [x] Deterministic offline provider; optional Anthropic / OpenAI / Ollama
- [x] 113 tests, no API key required

## Next

**Real assets.** The asset planner currently emits placeholders that name what
they stand in for. Next is generating images per scene and attaching them to
`RenderInput`, with licence provenance recorded per asset.

**Voiceover.** `RenderInput.audio` already reserves a track and the composition
already supports it. TTS slots in without touching the timing model — though
real VO durations should then *replace* the speaking-rate estimate rather than
sit alongside it.

**Live research.** The research agent reads a curated corpus. Retrieval goes
behind the same interface, with the approved-domain check as the gate. The
verified-fact rule does not loosen: a fetched page still has to be captured and
registered before it can back a claim.

**Real signals.** The shipped `signals.json` files are placeholders. Real
opportunity data comes from platform analytics exports or a keyword tool, mapped
into `Signal` with genuine source URLs and capture timestamps.

## Later

**Authorised publishing.** Official platform APIs with OAuth only — TikTok
Content Posting API, YouTube Data API, Instagram Graph API. Each requires app
review and grants specific scopes. **Nothing here will ever drive a logged-in
session or work around a platform restriction**, and each integration must set
the platform's own AI-content and paid-partnership flags.

**Analytics ingestion.** Currently a JSON file. Same official APIs, read scopes.

**SQLite.** When the JSON store stops being convenient. Interface is already in
place.

**Experiment tracking.** The optimizer proposes experiments; nothing yet closes
the loop and records which variation won.

## Explicit non-goals

- Automated posting that bypasses platform rules or rate limits
- Engagement automation of any kind
- Scraping behind logins or paywalls
- Generating claims about products nobody tested
- Any content that sexualises, targets or manipulates children — the
  child-directed brand exists under stricter rules than the adult one, not looser

## Known limitations

- The mock writer is template-driven. It is good enough to exercise every check
  and produce a reviewable package; it is not a substitute for a real model on
  production copy.
- Claim detectors are regex-based and will produce false positives. That is the
  intended trade: a rewrite is cheaper than a takedown.
- Platform duration limits in the publishing planner are hardcoded and go stale.
  Verify them before relying on them.
- Nothing here is legal advice. Child-directed content in particular carries
  duties (COPPA, the UK Children's Code, YouTube "Made for Kids") that need
  qualified review.
