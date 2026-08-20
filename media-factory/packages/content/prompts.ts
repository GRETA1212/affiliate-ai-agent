import type { Brand, Fact } from '../core/types.ts';

/**
 * One prompt set, used by every provider. The mock provider ignores the prose
 * and reads the JSON context; hosted providers get both.
 */

export function systemPrompt(brand: Brand): string {
  const lines = [
    `You write short-form vertical video content for the brand "${brand.name}".`,
    `Niche: ${brand.niche}. Audience: ${brand.audience}. Voice: ${brand.voice}.`,
    'Hard rules:',
    '- Original writing only. Never reproduce someone else\'s script, lyrics, or copy.',
    '- Never state a price, discount, statistic, or study result unless it is in the supplied verified facts, and cite its sourceId.',
    '- Never claim to have personally used, tested, worn, or reviewed a product when the assets are synthetic.',
    '- No urgency pressure, no medical or curative claims, no superlatives you cannot support.',
  ];
  if (brand.rules.bannedPhrases.length) {
    lines.push(`- These phrases are banned for this brand: ${brand.rules.bannedPhrases.join('; ')}.`);
  }
  if (brand.rules.childDirected) {
    lines.push(
      '- This is child-directed content: no purchase CTA, no data collection, no fear or comparison framing. One idea per scene, concrete objects, calm pacing.',
    );
  }
  if (brand.rules.requireAiDisclosure) {
    lines.push(`- The video carries an on-screen disclosure: "${brand.rules.aiDisclosureText}". Write as a synthetic presenter, honestly.`);
  }
  return lines.join('\n');
}

export function briefPrompt(context: BriefContext): string {
  return [
    `Topic: ${context.topic}`,
    `Target duration: ${context.targetDurationSeconds}s`,
    `Monetization paths available: ${context.monetizationPaths.join(', ')}`,
    `Verified facts:\n${formatFacts(context.facts)}`,
    'Produce a content brief: format, hook, angle, audience, cta, monetizationPath, keyPoints.',
  ].join('\n\n');
}

export function scriptPrompt(context: ScriptContext): string {
  return [
    `Brief: ${JSON.stringify(context.brief, null, 2)}`,
    `Verified facts (cite by sourceId):\n${formatFacts(context.facts)}`,
    `Assumptions (never state these as fact):\n${formatFacts(context.assumptions)}`,
    `Assets are ${context.allSynthetic ? 'entirely synthetic' : 'partly real'}.`,
    `Write ${context.sceneCount} scenes totalling ${context.targetDurationSeconds}s.`,
  ].join('\n\n');
}

export function storyboardPrompt(context: { script: unknown; signature: string }): string {
  return [
    `Script: ${JSON.stringify(context.script, null, 2)}`,
    `Template signature: ${context.signature}`,
    'For each scene return: sceneNumber, durationSeconds, voiceover, onScreenText, visualDescription, assetRequirements, transition.',
  ].join('\n\n');
}

function formatFacts(facts: Fact[]): string {
  if (facts.length === 0) return '(none)';
  return facts.map((f) => `- [${f.sourceId ?? 'no source'}] ${f.statement}`).join('\n');
}

export interface BriefContext {
  topic: string;
  targetDurationSeconds: number;
  monetizationPaths: string[];
  facts: Fact[];
  brand: Brand;
}

export interface ScriptContext {
  brief: unknown;
  facts: Fact[];
  assumptions: Fact[];
  allSynthetic: boolean;
  sceneCount: number;
  targetDurationSeconds: number;
  brand: Brand;
}
