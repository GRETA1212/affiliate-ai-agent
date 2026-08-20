# media-factory

Multi-brand short-form video pipeline. One topic in, a reviewable video package out:

```
topic → opportunity → research → brief → script → storyboard → asset plan
      → render → QA → publish manifest
```

It runs **completely offline with no API key**. The default LLM provider is a
deterministic mock writer, so `npm test` and the demo pipeline work on a fresh
clone with no `.env` and no network.

---

## Quickstart

```bash
cd media-factory
npm install
npm test                    # 113 tests, no API key needed
npm run demo                # full pipeline → real MP4
```

`npm run demo` is shorthand for:

```bash
npm run factory -- pipeline --brand maya --topic "AI chooses a 10-minute makeup look"
```

Output lands in `output/<job-id>/`:

| file | what it is |
| --- | --- |
| `maya-<job>.mp4` | 1080×1920, 30fps, H.264 + silent AAC bed |
| `thumbnail.png` | suggested still, taken from the hook scene |
| `render-input.json` | the render contract — re-render from this alone |
| `publication.json` | per-platform captions, hashtags, disclosure flags |

---

## Commands

```bash
npm run factory -- brands                        # list configured brands
npm run factory -- scout --brand maya            # rank recorded opportunity signals
npm run factory -- create --brand maya --topic "…"   # everything except render
npm run factory -- pipeline --brand maya --topic "…" # the full run
npm run factory -- render <job-id>               # re-render from saved props
npm run factory -- qa <job-id>                   # re-run QA on a stored job
npm run factory -- analytics ingest --file examples/analytics-sample.json
npm run factory -- optimize --brand maya         # 25/50/25 growth policy
```

---

## Brands

Two ship configured. Adding a third means copying a folder — no code change.

**`maya`** — Maya.exe. Beauty + AI + beauty tech. TikTok, YouTube Shorts,
Instagram Reels. Carries a persistent **"Virtual AI creator"** badge on every
frame, and an affiliate disclosure whenever the monetization path is paid.

**`kids-learning`** — educational videos for children. YouTube and Shorts.
Child-directed, so purchase CTAs and any data capture are **hard errors**, not
warnings, and every manifest sets *Made for Kids*. The display name is plain
data in `brand.json`; nothing in the code depends on it.

See `brands/README.md` for the file layout.

---

## The three rules this codebase is built around

**1. The scout ranks evidence. It never authors it.**
There is deliberately no code path in `opportunity-scout.ts` that can produce a
metric or a source. Both are read from `brands/<id>/signals.json`. If that file
is empty, the scout returns nothing and says so rather than filling the gap with
plausible-looking trend data.

The signals that ship are **placeholders** using the reserved `.invalid` TLD,
which can never resolve. The scout detects that and reports it loudly on every
run. Replace them with signals you actually observed before treating any ranking
as meaningful.

**2. A fact needs a source. Everything else is an observation.**
The research agent only promotes a statement to `verified_fact` when it cites a
registered source on an approved domain *that has actually been captured*.
Anything else becomes an `assumption` with a null source id, and an assumption
may not carry a number. `claims` ships **empty** on purpose — the factory must
never boot with pre-fabricated citations.

**3. Synthetic assets cannot claim real testing.**
The asset planner records whether each asset is synthetic. When everything is
synthetic — nothing filmed, worn, bought or tested — the QA agent blocks
first-person testing language ("I tried it", "on my own skin"). This is the rule
that stops a virtual creator implying product testing that never happened.

---

## QA gate

QA runs 13 checks and is a **gate**, not a report: a failing package never
reaches the publishing planner, and no manifest is written for it.

unsupported claims · fake prices · fake discounts · fake statistics · missing
citations · missing AI disclosure · missing affiliate disclosure · scene timing ·
caption overflow · missing assets · banned phrases · child-directed rules ·
synthetic-asset honesty

A passing report lists every check by name, so a pass is auditable rather than
just green.

---

## Publishing

**This tool does not post to any platform.** Every manifest is
`publishMethod: "manual_upload"`, and there is no code that uploads anything.

That is a deliberate boundary, not a missing feature. Automated publishing gets
added only through the platforms' own authorised APIs with OAuth — never by
driving a logged-in session and never by working around a platform restriction.
What the manifest gives you is everything needed to upload correctly by hand:
caption, hashtags, the disclosure toggles to set, a thumbnail timecode, and the
duration limits per destination.

---

## Rendering

**Remotion is the intended renderer.** `packages/renderer/remotion/` holds a real
9:16 composition: captions, hook chip, brand badge rail, CTA, per-scene timing,
transitions and an audio placeholder.

Remotion renders through headless Chromium, which must be downloaded on first
use. On an offline or network-restricted machine that download fails, so there
is a **Pillow + ffmpeg fallback** that consumes the identical `RenderInput`
contract. The backend actually used is recorded on every `VideoJob`, so nobody
reviews a fallback render believing it came from Remotion.

```bash
npm run remotion:ensure-browser   # enable the real renderer
npm run remotion:studio           # preview the composition
RENDERER=remotion npm run demo    # fail loudly instead of falling back
```

> The bundled sample MP4 in `output/` was produced by the **ffmpeg fallback**,
> because the build environment could not reach Remotion's browser download.
> Run the demo yourself after `remotion:ensure-browser` for the real thing.

---

## Providers

```bash
LLM_PROVIDER=mock       # default: deterministic, offline, free
LLM_PROVIDER=anthropic  # needs ANTHROPIC_API_KEY
LLM_PROVIDER=openai     # needs OPENAI_API_KEY
LLM_PROVIDER=ollama     # local, no key
```

Every agent asks for JSON and validates it against a zod schema before the
result goes anywhere, so a bad model response fails at the producing agent
rather than three steps later. Copy `.env.example` to `.env`. **No key is ever
read at import time, and no secret belongs in source control.**

---

## Layout

```
apps/cli/              command line entry point
packages/
  core/                entities (zod), store, ids, text, LLM providers
  content/             prompts, draft schemas, deterministic mock writer
  agents/              scout, scorer, strategist, script, storyboard,
                       asset planner, QA, publishing planner
  research/            evidence gathering, verified-fact discipline
  renderer/            render contract, Remotion composition, ffmpeg fallback
  analytics/           ingest schema, growth optimizer
  compliance/          claim detectors, brand + disclosure rules
  orchestrator/        LangGraph state graph
brands/                maya, kids-learning
tests/                 113 tests
```

See `ARCHITECTURE.md` for how it fits together and `ROADMAP.md` for what is
deliberately not built yet.
