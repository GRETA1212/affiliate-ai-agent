import { MockLlmProvider } from '../core/llm/mock.ts';
import type { LlmRequest } from '../core/llm/provider.ts';
import { seededRandom } from '../core/ids.ts';
import { estimateSpokenSeconds } from '../core/text.ts';
import type { Fact } from '../core/types.ts';
import { TASKS, type BriefDraft, type ScriptDraft, type StoryboardDraft } from './schemas.ts';

/**
 * The offline writer. It is deliberately template-driven rather than random:
 * the same inputs always produce the same script, which is what makes the
 * pipeline testable and the demo reproducible without an API key.
 *
 * Every template here obeys the same content rules the prompts state, so the
 * QA agent is checking real behaviour, not a rigged happy path.
 */

interface BrandContext {
  id: string;
  name: string;
  audience: string;
  defaultCta: string;
  monetizationPaths: string[];
  childDirected: boolean;
  targetDurationSeconds: number;
  minSceneSeconds: number;
  maxSceneSeconds: number;
}

interface BriefInput {
  topic: string;
  brand: BrandContext;
  facts: Fact[];
  syntheticAssets: boolean;
}

interface ScriptInput {
  brief: BriefDraft & { topic: string };
  brand: BrandContext;
  facts: Fact[];
  assumptions: Fact[];
  allSynthetic: boolean;
  sceneCount: number;
  targetDurationSeconds: number;
}

interface StoryboardInput {
  script: ScriptDraft;
  signature: 'render_rail' | 'lesson_stage';
  brand: BrandContext;
}

/** "AI chooses a 10-minute makeup look" -> "a 10-minute makeup look" */
export function subjectOf(topic: string): string {
  const stripped = topic
    .replace(/^(the\s+)?ai\s+(chooses|choose|chose|picks|pick|picked|selects|select)\s+/i, '')
    .replace(/^(how|why)\s+/i, '')
    .trim();
  return (stripped || topic).replace(/\.$/, '');
}

function pick<T>(items: T[], rng: () => number): T {
  const index = Math.floor(rng() * items.length);
  return items[Math.min(index, items.length - 1)] as T;
}

function verified(facts: Fact[]): Fact[] {
  return facts.filter((f) => f.kind === 'verified_fact' && f.sourceId);
}

function lower(statement: string): string {
  return statement.charAt(0).toLowerCase() + statement.slice(1);
}

/* -------------------------------------------------------------------------- */
/* Brief                                                                       */
/* -------------------------------------------------------------------------- */

function buildBrief(input: BriefInput, seed: string): BriefDraft {
  const rng = seededRandom(seed);
  const subject = subjectOf(input.topic);
  const facts = verified(input.facts);
  const format = chooseFormat(input, rng);

  const hook = input.brand.childDirected
    ? pick(
        [
          `Let's learn ${subject} together.`,
          `Here is ${subject}, one step at a time.`,
        ],
        rng,
      )
    : input.syntheticAssets
      ? pick(
          [
            `An AI planned ${subject}. Here's where it slips.`,
            `I let an AI plan ${subject}. One step is wrong.`,
          ],
          rng,
        )
      : pick(
          [
            `I handed ${subject} to an AI and followed it exactly.`,
            `An AI planned ${subject}. I ran it start to finish.`,
          ],
          rng,
        );

  const keyPoints = [
    ...facts.slice(0, 2).map((f) => f.statement),
    input.brand.childDirected
      ? 'One idea per scene, with something concrete to count or point at'
      : 'Name the limitation out loud instead of hiding it',
  ];
  if (input.syntheticAssets && !input.brand.childDirected) {
    keyPoints.push('State on screen that the visuals are a rendered plan, not a filmed test');
  }
  while (keyPoints.length < 2) keyPoints.push(`Explain ${subject} in plain language`);

  const monetizationPath = input.brand.childDirected
    ? input.brand.monetizationPaths.includes('ad_revenue')
      ? 'ad_revenue'
      : 'none'
    : (input.brand.monetizationPaths[0] ?? 'none');

  return {
    format,
    hook,
    angle: input.brand.childDirected
      ? `Teach ${subject} using objects a child can see and touch, no pressure and no comparison to other children.`
      : `Show the AI's reasoning for ${subject}, then show the one thing it cannot see.`,
    audience: input.brand.audience,
    cta: input.brand.defaultCta,
    monetizationPath: monetizationPath as BriefDraft['monetizationPath'],
    keyPoints: keyPoints.slice(0, 6),
  };
}

function chooseFormat(input: BriefInput, rng: () => number): BriefDraft['format'] {
  const topic = input.topic.toLowerCase();
  if (input.brand.childDirected) return 'explainer';
  if (/(chooses|choose|picks|pick|selects|builds)/.test(topic)) return 'demo_walkthrough';
  if (/^(why|how|what)\b/.test(topic)) return 'explainer';
  if (/\b\d+\s+(ways|tips|things|mistakes)\b/.test(topic)) return 'listicle';
  if (/(before|after|transformation|glow up)/.test(topic)) return 'transformation';
  return pick<BriefDraft['format']>(['talking_head', 'listicle'], rng);
}

/* -------------------------------------------------------------------------- */
/* Script                                                                      */
/* -------------------------------------------------------------------------- */

type Role = 'hook' | 'frame' | 'fact' | 'limit' | 'synthetic_note' | 'practice' | 'recap' | 'cta';

interface DraftLine {
  role: Role;
  voiceover: string;
  onScreenText: string;
  sourceId: string | null;
}

function buildScript(input: ScriptInput, seed: string): ScriptDraft {
  const subject = subjectOf(input.brief.topic);
  const facts = verified(input.facts);
  const numericFact = facts.find((f) => f.numeric) ?? null;
  const explainFact = facts.find((f) => !f.numeric) ?? facts[0] ?? null;
  const limitFact = facts.length > 1 ? facts[facts.length - 1] : null;

  const lines: DraftLine[] = input.brand.childDirected
    ? buildKidsLines(input, subject, explainFact)
    : buildAdultLines(input, subject, numericFact, explainFact, limitFact);

  const trimmed = fitToSceneCount(lines, input.sceneCount);
  const durations = allocateDurations(trimmed, input);

  return {
    title: `${input.brand.name}: ${input.brief.topic}`,
    hook: input.brief.hook,
    cta: input.brief.cta,
    lines: trimmed.map((line, index) => ({
      sceneNumber: index + 1,
      voiceover: line.voiceover,
      onScreenText: line.onScreenText,
      durationSeconds: durations[index] as number,
      sourceId: line.sourceId,
    })),
  };
}

function buildAdultLines(
  input: ScriptInput,
  subject: string,
  numericFact: Fact | null,
  explainFact: Fact | null,
  limitFact: Fact | null,
): DraftLine[] {
  const lines: DraftLine[] = [
    { role: 'hook', voiceover: input.brief.hook, onScreenText: 'THE PLAN', sourceId: null },
  ];

  lines.push(
    numericFact
      ? {
          role: 'frame',
          voiceover: `The constraint it worked inside: ${lower(numericFact.statement)}.`,
          onScreenText: 'THE CONSTRAINT',
          sourceId: numericFact.sourceId,
        }
      : {
          role: 'frame',
          voiceover: `One pass at ${subject}. No edits.`,
          onScreenText: 'THE SETUP',
          sourceId: null,
        },
  );

  if (explainFact) {
    lines.push({
      role: 'fact',
      voiceover: `How it decided: ${lower(explainFact.statement)}.`,
      onScreenText: 'HOW IT DECIDED',
      sourceId: explainFact.sourceId,
    });
  }

  if (limitFact && limitFact.id !== explainFact?.id) {
    lines.push({
      role: 'limit',
      voiceover: `Where it slips: ${lower(limitFact.statement)}.`,
      onScreenText: 'WHERE IT SLIPS',
      sourceId: limitFact.sourceId,
    });
  } else {
    lines.push({
      role: 'limit',
      voiceover: 'It only knows what it was shown. The rest is a guess.',
      onScreenText: 'WHERE IT SLIPS',
      sourceId: null,
    });
  }

  if (input.allSynthetic) {
    lines.push({
      role: 'synthetic_note',
      voiceover: 'This is a rendered mockup. Nothing was filmed or tested.',
      onScreenText: 'RENDERED PLAN, NOT A TEST',
      sourceId: null,
    });
  }

  lines.push({ role: 'cta', voiceover: `${input.brief.cta}.`, onScreenText: 'FULL BREAKDOWN', sourceId: null });
  return lines;
}

function buildKidsLines(input: ScriptInput, subject: string, explainFact: Fact | null): DraftLine[] {
  const lines: DraftLine[] = [
    { role: 'hook', voiceover: input.brief.hook, onScreenText: "Let's look", sourceId: null },
    {
      role: 'fact',
      voiceover: explainFact
        ? `Here is the idea: ${lower(explainFact.statement)}.`
        : `Here is the idea behind ${subject}.`,
      onScreenText: 'The idea',
      sourceId: explainFact?.sourceId ?? null,
    },
    {
      role: 'practice',
      voiceover: 'Your turn. Point at each group on the screen and say the number out loud with me.',
      onScreenText: 'Your turn',
      sourceId: null,
    },
    {
      role: 'recap',
      voiceover: 'We did it. Same idea, every time: make the groups first, then count the groups.',
      onScreenText: 'We did it',
      sourceId: null,
    },
    { role: 'cta', voiceover: `${input.brief.cta}.`, onScreenText: 'Next lesson', sourceId: null },
  ];
  return lines;
}

/** Pads or trims toward the requested scene count without dropping the CTA. */
function fitToSceneCount(lines: DraftLine[], sceneCount: number): DraftLine[] {
  if (lines.length === sceneCount) return lines;
  if (lines.length > sceneCount) {
    const cta = lines[lines.length - 1] as DraftLine;
    return [...lines.slice(0, sceneCount - 1), cta];
  }

  // Padding draws from distinct beats. Repeating one filler line verbatim would
  // produce two identical scenes, which reads as a bug on screen - so when the
  // pool runs out we simply return a shorter video. Scene count is a target,
  // not a requirement; the schema minimum of 3 is the real floor.
  const filler: DraftLine[] = [
    { role: 'recap', voiceover: 'Same order, every time.', onScreenText: 'RECAP', sourceId: null },
    { role: 'recap', voiceover: 'Three moves. That is the whole plan.', onScreenText: 'THE PATTERN', sourceId: null },
    { role: 'practice', voiceover: 'Would you have made the same call?', onScreenText: 'YOUR TURN', sourceId: null },
  ];

  const padded = [...lines];
  const cta = padded.pop() as DraftLine;
  for (const line of filler) {
    if (padded.length >= sceneCount - 1) break;
    padded.push(line);
  }
  padded.push(cta);
  return padded;
}

/**
 * Durations.
 *
 * The speaking-rate floor is inviolable: a scene may never be shorter than the
 * time needed to say its own voiceover. An earlier version scaled every scene
 * to hit the target duration, which silently pushed scenes under that floor and
 * the QA agent caught it - exactly the failure the QA gate exists for.
 *
 * So: compute the floor first, then only ever scale UP toward the target.
 * Overshooting the target is fine (the brand's max duration is the real
 * constraint); undershooting the floor is not.
 */
function allocateDurations(lines: DraftLine[], input: ScriptInput): number[] {
  const { minSceneSeconds, maxSceneSeconds } = input.brand;

  // +0.4s of breathing room so the line does not end exactly on the cut.
  const floors = lines.map((line) =>
    clamp(estimateSpokenSeconds(line.voiceover) + 0.4, minSceneSeconds, maxSceneSeconds),
  );
  const floorTotal = floors.reduce((sum, value) => sum + value, 0);

  // Already at or over target: keep the floors, the video simply runs longer.
  if (floorTotal >= input.targetDurationSeconds) {
    return floors.map((value) => Number(value.toFixed(2)));
  }

  // Under target: distribute the slack proportionally, never below the floor.
  const slack = input.targetDurationSeconds - floorTotal;
  const padded = floors.map((value) => {
    const share = (value / floorTotal) * slack;
    return clamp(Number((value + share).toFixed(2)), value, maxSceneSeconds);
  });

  // Absorb rounding drift into the scene with the most headroom.
  const drift = Number((input.targetDurationSeconds - padded.reduce((s, v) => s + v, 0)).toFixed(2));
  if (Math.abs(drift) >= 0.01) {
    let index = 0;
    for (let i = 1; i < padded.length; i++) {
      const headroom = maxSceneSeconds - (padded[i] as number);
      if (headroom > maxSceneSeconds - (padded[index] as number)) index = i;
    }
    const floor = floors[index] as number;
    padded[index] = clamp(Number(((padded[index] as number) + drift).toFixed(2)), floor, maxSceneSeconds);
  }
  return padded;
}

function clamp(value: number, min: number, max: number): number {
  return Number(Math.min(max, Math.max(min, value)).toFixed(2));
}

/* -------------------------------------------------------------------------- */
/* Storyboard                                                                  */
/* -------------------------------------------------------------------------- */

function buildStoryboard(input: StoryboardInput): StoryboardDraft {
  const last = input.script.lines.length - 1;
  return {
    scenes: input.script.lines.map((line, index) => {
      const isHook = index === 0;
      const isCta = index === last;
      const visual = visualFor(input.signature, line.onScreenText, isHook, isCta, input.brand.name);
      return {
        sceneNumber: line.sceneNumber,
        durationSeconds: line.durationSeconds,
        voiceover: line.voiceover,
        onScreenText: line.onScreenText,
        visualDescription: visual.description,
        assetRequirements: visual.assets,
        transition: isHook ? 'whip' : isCta ? 'fade' : index % 2 === 0 ? 'cut' : 'fade',
      };
    }),
  };
}

function visualFor(
  signature: StoryboardInput['signature'],
  label: string,
  isHook: boolean,
  isCta: boolean,
  brandName: string,
): { description: string; assets: string[] } {
  if (signature === 'lesson_stage') {
    if (isHook) {
      return {
        description: `Wide stage card: one large friendly object centred on the teal field, ${brandName} badge top left, no clutter.`,
        assets: ['generated_image: single large object on flat background', 'text_graphic: lesson title'],
      };
    }
    if (isCta) {
      return {
        description: 'Stage card with the next-lesson arrow motif, no purchase prompt, no link.',
        assets: ['animation: gentle arrow pointing right', 'text_graphic: next lesson label'],
      };
    }
    return {
      description: `Stage card showing the counted groups laid out in rows, step label "${label}" pinned to the frame edge.`,
      assets: ['generated_image: countable objects arranged in groups', 'text_graphic: step label'],
    };
  }

  // render_rail
  if (isHook) {
    return {
      description: `Cold open: hook text set large over the gradient field, ${brandName} badge and the virtual-creator chip visible from frame one.`,
      assets: ['text_graphic: hook typography', 'generated_image: abstract gloss texture backdrop'],
    };
  }
  if (isCta) {
    return {
      description: 'Closing card: CTA line centred, disclosure chips held on screen for the full beat.',
      assets: ['text_graphic: CTA card', 'text_graphic: disclosure chips'],
    };
  }
  return {
    description: `Panel labelled "${label}" on the render rail, with the described step illustrated as a synthetic mockup, not a filmed demo.`,
    assets: ['generated_image: synthetic mockup of the step', 'text_graphic: panel label'],
  };
}

/* -------------------------------------------------------------------------- */
/* Provider wiring                                                             */
/* -------------------------------------------------------------------------- */

export function buildMockProvider(): MockLlmProvider {
  return new MockLlmProvider()
    .register(TASKS.brief, (request: LlmRequest) =>
      buildBrief(request.input as unknown as BriefInput, request.seed),
    )
    .register(TASKS.script, (request: LlmRequest) =>
      buildScript(request.input as unknown as ScriptInput, request.seed),
    )
    .register(TASKS.storyboard, (request: LlmRequest) =>
      buildStoryboard(request.input as unknown as StoryboardInput),
    );
}
