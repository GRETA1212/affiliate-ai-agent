import { describe, expect, it } from 'vitest';
import { containsNumericClaim, detectBannedPhrases, detectClaims } from '../packages/compliance/claims.ts';
import { runQaAgent } from '../packages/agents/qa-agent.ts';
import { loadBrand } from '../packages/core/brand.ts';
import type {
  AssetPlan,
  Brand,
  ContentBrief,
  ResearchBundle,
  Script,
  Storyboard,
} from '../packages/core/types.ts';

const maya = loadBrand('maya');

/* -------------------------------------------------------------------------- */
/* detectors                                                                   */
/* -------------------------------------------------------------------------- */

describe('claim detection', () => {
  it('catches prices in several currencies and phrasings', () => {
    for (const text of ['it costs $24', 'only £9.99', 'about 30 dollars', '15 usd']) {
      expect(detectClaims(text).some((h) => h.kind === 'price'), text).toBe(true);
    }
  });

  it('catches discounts and urgency', () => {
    for (const text of ['get 20% off today', 'use my code BEAUTY', 'the sale ends Friday', 'limited time only']) {
      expect(detectClaims(text).some((h) => h.kind === 'discount'), text).toBe(true);
    }
  });

  it('catches fabricated statistics', () => {
    for (const text of ['works for 87% of people', '9 out of 10 users agree', 'studies show it lasts', '3x better coverage']) {
      expect(detectClaims(text).some((h) => h.kind === 'statistic'), text).toBe(true);
    }
  });

  it('catches unsubstantiable superlatives', () => {
    for (const text of ['the best foundation', 'guaranteed to match', 'it works for everyone']) {
      expect(detectClaims(text).some((h) => h.kind === 'superlative'), text).toBe(true);
    }
  });

  it('catches first-person physical testing language', () => {
    for (const text of ['I tried it for a week', 'I wore this all day', 'on my own skin']) {
      expect(detectClaims(text).some((h) => h.kind === 'physical_testing'), text).toBe(true);
    }
  });

  it('leaves honest observational copy alone', () => {
    for (const text of [
      'The tool picked a lighter base than I expected.',
      'It only knows what it was shown. The rest is a guess.',
      'This is a rendered mockup. Nothing was filmed or tested.',
    ]) {
      expect(detectClaims(text), text).toEqual([]);
    }
  });

  it('matches brand-configured banned phrases case-insensitively', () => {
    const hits = detectBannedPhrases('This is CLINICALLY PROVEN to work', maya.rules.bannedPhrases);
    expect(hits).toHaveLength(1);
    expect(hits[0]?.kind).toBe('banned_phrase');
  });

  it('separates factual numbers from premise numbers', () => {
    expect(containsNumericClaim('lasts 40% longer')).toBe(true);
    expect(containsNumericClaim('costs $30')).toBe(true);
    // The premise of the video is a 10-minute look; that is not a claim about
    // the world, and flagging it would make the detector useless.
    expect(containsNumericClaim('a 10-minute makeup look')).toBe(false);
    expect(containsNumericClaim('step one, set the base')).toBe(false);
  });
});

/* -------------------------------------------------------------------------- */
/* QA gate                                                                     */
/* -------------------------------------------------------------------------- */

interface Overrides {
  brand?: Brand;
  voiceover?: string;
  sourceId?: string | null;
  disclosures?: string[];
  durationSeconds?: number;
  onScreenText?: string;
  allSynthetic?: boolean;
  monetizationPath?: ContentBrief['monetizationPath'];
}

/** Builds a minimal but schema-valid package that passes QA by default. */
function makePackage(overrides: Overrides = {}) {
  const brand = overrides.brand ?? maya;
  const duration = overrides.durationSeconds ?? 7;
  const lines = [
    { voiceover: overrides.voiceover ?? 'An AI planned the look.', onScreenText: overrides.onScreenText ?? 'THE PLAN' },
    { voiceover: 'It only knows what it was shown.', onScreenText: 'THE LIMIT' },
    { voiceover: 'This is a rendered mockup.', onScreenText: 'NOT A TEST' },
  ].map((line, index) => ({
    sceneNumber: index + 1,
    voiceover: line.voiceover,
    onScreenText: line.onScreenText,
    durationSeconds: index === 0 ? duration : 7,
    sourceId: index === 0 ? (overrides.sourceId ?? null) : null,
  }));

  const monetizationPath = overrides.monetizationPath ?? 'affiliate';
  const defaultDisclosures = [brand.rules.aiDisclosureText, brand.rules.affiliateDisclosureText];

  const brief: ContentBrief = {
    id: 'brief_1',
    brandId: brand.id,
    topic: 'test topic',
    format: 'demo_walkthrough',
    hook: 'hook',
    audience: brand.audience,
    angle: 'angle',
    cta: 'cta',
    monetizationPath,
    keyPoints: ['a', 'b'],
    targetDurationSeconds: 30,
    requiredDisclosures: [],
    createdAt: '2026-01-01T00:00:00.000Z',
  };

  const script: Script = {
    id: 'script_1',
    briefId: 'brief_1',
    brandId: brand.id,
    title: 'title',
    hook: 'hook',
    cta: 'cta',
    lines,
    totalDurationSeconds: Number(lines.reduce((s, l) => s + l.durationSeconds, 0).toFixed(2)),
    disclosures: overrides.disclosures ?? defaultDisclosures,
    createdAt: '2026-01-01T00:00:00.000Z',
  };

  const storyboard: Storyboard = {
    id: 'sb_1',
    scriptId: 'script_1',
    brandId: brand.id,
    scenes: lines.map((line) => ({
      sceneNumber: line.sceneNumber,
      durationSeconds: line.durationSeconds,
      voiceover: line.voiceover,
      onScreenText: line.onScreenText,
      visualDescription: 'a frame',
      assetRequirements: ['generated_image: frame'],
      transition: 'cut' as const,
    })),
    totalDurationSeconds: script.totalDurationSeconds,
    createdAt: '2026-01-01T00:00:00.000Z',
  };

  const assetPlan: AssetPlan = {
    id: 'plan_1',
    storyboardId: 'sb_1',
    assets: lines.map((line) => ({
      id: `asset_${line.sceneNumber}`,
      sceneNumber: line.sceneNumber,
      type: 'generated_image' as const,
      description: 'frame',
      synthetic: overrides.allSynthetic ?? true,
      status: 'placeholder' as const,
      uri: null,
    })),
    allSynthetic: overrides.allSynthetic ?? true,
    createdAt: '2026-01-01T00:00:00.000Z',
  };

  const research: ResearchBundle = {
    id: 'res_1',
    topic: 'test topic',
    sources: [
      {
        id: 'src_ok',
        url: 'https://www.ftc.gov/guidance',
        title: 'source',
        publisher: 'FTC',
        capturedAt: '2026-01-01T00:00:00.000Z',
      },
    ],
    facts: [],
    gaps: [],
    createdAt: '2026-01-01T00:00:00.000Z',
  };

  return { brand, brief, script, storyboard, assetPlan, research, jobId: 'job_test' };
}

const rules = (report: ReturnType<typeof runQaAgent>) => report.findings.map((f) => f.rule);

describe('QA agent', () => {
  it('passes a clean package', () => {
    const report = runQaAgent(makePackage());
    expect(report.findings).toEqual([]);
    expect(report.passed).toBe(true);
  });

  it('names every check it ran, so a pass is auditable', () => {
    const report = runQaAgent(makePackage());
    for (const check of [
      'unsupported_claims',
      'fake_prices',
      'fake_discounts',
      'fake_statistics',
      'missing_citations',
      'missing_ai_disclosure',
      'missing_affiliate_disclosure',
      'scene_timing',
      'caption_overflow',
      'missing_assets',
    ]) {
      expect(report.checksRun).toContain(check);
    }
  });

  it('blocks a fabricated price', () => {
    const report = runQaAgent(makePackage({ voiceover: 'This one costs $24.' }));
    expect(rules(report)).toContain('fake_prices');
    expect(report.passed).toBe(false);
  });

  it('blocks a fabricated discount', () => {
    expect(rules(runQaAgent(makePackage({ voiceover: 'Use my code for 20% off.' })))).toContain('fake_discounts');
  });

  it('blocks an uncited statistic', () => {
    expect(rules(runQaAgent(makePackage({ voiceover: 'It matched 90% of testers.' })))).toContain('fake_statistics');
  });

  it('blocks a number that carries no source id', () => {
    expect(rules(runQaAgent(makePackage({ voiceover: 'It lasts 12% longer.' })))).toContain('missing_citations');
  });

  it('rejects a citation pointing at an unregistered source', () => {
    const report = runQaAgent(makePackage({ voiceover: 'A sourced statement.', sourceId: 'src_nonexistent' }));
    expect(rules(report)).toContain('missing_citations');
  });

  it('blocks testing language when every asset is synthetic', () => {
    const report = runQaAgent(makePackage({ voiceover: 'I wore this all day.' }));
    expect(rules(report)).toContain('synthetic_asset_honesty');
    expect(report.passed).toBe(false);
  });

  it('allows testing language once real footage exists', () => {
    const report = runQaAgent(makePackage({ voiceover: 'I wore this all day.', allSynthetic: false }));
    expect(rules(report)).not.toContain('synthetic_asset_honesty');
  });

  it('blocks a missing AI disclosure', () => {
    const report = runQaAgent(makePackage({ disclosures: [maya.rules.affiliateDisclosureText] }));
    expect(rules(report)).toContain('missing_ai_disclosure');
  });

  it('blocks a missing affiliate disclosure on a paid path', () => {
    const report = runQaAgent(makePackage({ disclosures: [maya.rules.aiDisclosureText] }));
    expect(rules(report)).toContain('missing_affiliate_disclosure');
  });

  it('does not demand an affiliate disclosure when nothing is monetized', () => {
    const report = runQaAgent(
      makePackage({ monetizationPath: 'none', disclosures: [maya.rules.aiDisclosureText] }),
    );
    expect(rules(report)).not.toContain('missing_affiliate_disclosure');
  });

  it('blocks a scene too short to speak its own voiceover', () => {
    const report = runQaAgent(
      makePackage({ voiceover: 'This is a fairly long line that cannot possibly fit inside two seconds of screen time.', durationSeconds: 2 }),
    );
    expect(rules(report)).toContain('voiceover_exceeds_scene');
  });

  it('allows a caption that wraps to exactly the configured line limit', () => {
    const line = 'X'.repeat(maya.rules.maxCaptionCharsPerLine);
    const text = Array.from({ length: maya.rules.maxCaptionLinesPerScene }, () => line).join(' ');
    const report = runQaAgent(makePackage({ onScreenText: text }));
    expect(rules(report)).not.toContain('caption_overflow');
  });

  it('blocks caption overflow past the configured line limit', () => {
    const line = 'X'.repeat(maya.rules.maxCaptionCharsPerLine);
    const text = Array.from({ length: maya.rules.maxCaptionLinesPerScene + 1 }, () => line).join(' ');
    const report = runQaAgent(makePackage({ onScreenText: text }));
    expect(rules(report)).toContain('caption_overflow');
  });

  it('blocks a banned phrase', () => {
    const report = runQaAgent(makePackage({ voiceover: 'It is clinically proven.' }));
    expect(rules(report)).toContain('banned_phrases');
  });
});
