# Architecture

## Shape

A workflow/orchestrator system. Agents are pure-ish functions over typed
artifacts; the orchestrator owns sequencing and state. No agent calls another
agent directly, so any step can be run, tested or replaced in isolation.

```
                        ┌──────────────────────────────┐
   topic ──────────────▶│        LangGraph graph       │
                        └──────────────┬───────────────┘
                                       │
  scout ─▶ research ─▶ strategist ─▶ script ─▶ storyboard ─▶ assets
                                       │
                                       ▼
                            render ─▶ QA ─▶ ┬─ pass ─▶ publish
                                            └─ fail ─▶ halt
```

## Why LangGraph

The brief said "use LangGraph JS if it integrates cleanly". It does: it runs
locally, needs no API key, and its channel reducers express exactly what was
needed — each node returns a partial state, `steps` and `warnings` append, every
artifact channel replaces. The QA gate is a `addConditionalEdges`, which makes
"a failing package never reaches publish" a property of the graph rather than an
`if` somebody can forget.

One wrinkle worth knowing: **LangGraph rejects a node whose name matches a state
channel.** Nodes carrying artifacts of the same name are therefore suffixed —
`research_agent`, `script_agent`, `storyboard_agent`, `qa_agent`.

## Data flow

Each artifact is a zod schema in `packages/core/types.ts` — the single source of
truth for anything crossing an agent boundary:

`Brand → Signal → Opportunity → ResearchBundle → ContentBrief → Script →
Storyboard → AssetPlan → RenderInput → VideoJob → QaReport → Publication →
AnalyticsRecord → Experiment`

Agents validate their own output, so a malformed response fails at the producing
agent instead of surfacing three steps downstream as something inexplicable.

Two schema layers, deliberately:

- **draft schemas** (`packages/content/schemas.ts`) — what a *model* returns
- **entity schemas** (`packages/core/types.ts`) — what the *system* stores

Ids and timestamps are assigned by agents, never by the model. A model cannot
mint an id, and cannot decide what a disclosure is.

## Post-conditions

Agents apply deterministic post-conditions after generation, because a swapped
provider may be creative about copy but must not be creative about policy:

- disclosures are recomputed from brand rules and overwrite the model's choice
- a child-directed brand can never be assigned a paid monetization path
- scene numbers are re-densified to 1..n
- a `sourceId` not present in the research bundle is stripped, which downgrades
  the line to unsourced and lets QA catch it
- storyboard timing is taken from the script; the storyboard describes, it does
  not retime

## Ordering note: assets before storyboard

The strategist and script agent need to know whether real footage exists
*before* the asset plan is built, because it changes what the copy may claim.
The factory default is `synthetic` — nothing filmed, worn, bought or tested —
and the operator opts into `mixed` once real capture is attached. Defaulting to
synthetic is the safe direction: it can only make copy more cautious, never
less.

## The render contract

`RenderInput` is the boundary between "what to say" and "how it looks". Both
renderers consume it, so they cannot drift on timing, captions or badges.

Frames, not seconds, are the unit of truth: `durationFrames` is rounded once in
`build-render-input.ts`, which keeps the audio bed, caption timings and total
length in agreement. `totalFrames` is always the exact sum of scene frames.

**Remotion** (`packages/renderer/remotion/`) is the production renderer — one
composition serves every brand, with differences coming from `theme` and
`theme.signature` rather than forked code.

**The ffmpeg fallback** (`packages/renderer/fallback/render_frames.py`) exists
because Remotion needs a downloaded Chromium. It rasterises the same contract
with Pillow and encodes with ffmpeg. It is a proof, not a replacement, and the
backend used is always recorded on the `VideoJob`.

## Compliance

Compliance is a separate package on purpose: it is the part that must stay
readable to someone who is not a programmer, and reviewable without reading the
pipeline.

- `claims.ts` — regex detectors for prices, discounts, statistics,
  superlatives, first-person testing and health claims. Intentionally noisy: a
  false positive costs a rewrite, a false negative costs a takedown.
- `brand-rules.ts` — disclosures, child-directed rules, scene timing, caption
  overflow, platform validity. All driven by `brand.json`, so adding a brand
  never means editing this file.

The QA agent composes both and returns findings with `error`/`warning` severity.
Anything with legal exposure is an error.

## Storage

A JSON file store under `data/`. Boring on purpose: no native build step, and
every artifact is diffable in review. SQLite is a drop-in behind the same
interface when volume justifies it.

## Determinism

`stableId()` hashes inputs; the mock writer is template-driven with a seeded
PRNG; `FACTORY_FIXED_CLOCK` freezes time. The same topic produces the same
script, which is what makes the pipeline testable and the demo reproducible.
