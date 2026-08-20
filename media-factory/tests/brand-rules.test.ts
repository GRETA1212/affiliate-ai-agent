import { describe, expect, it } from 'vitest';
import { loadBrand, listBrandIds } from '../packages/core/brand.ts';
import {
  checkChildDirected,
  checkDisclosures,
  checkPlatforms,
  requiredDisclosures,
} from '../packages/compliance/brand-rules.ts';
import type { ContentBrief, Script } from '../packages/core/types.ts';

const maya = loadBrand('maya');
const kids = loadBrand('kids-learning');

function scriptWith(cta: string, voiceover = 'a normal line'): Script {
  return {
    id: 's',
    briefId: 'b',
    brandId: kids.id,
    title: 't',
    hook: 'h',
    cta,
    lines: [
      { sceneNumber: 1, voiceover, onScreenText: 'a', durationSeconds: 5, sourceId: null },
      { sceneNumber: 2, voiceover: 'another line', onScreenText: 'b', durationSeconds: 5, sourceId: null },
      { sceneNumber: 3, voiceover: cta, onScreenText: 'c', durationSeconds: 5, sourceId: null },
    ],
    totalDurationSeconds: 15,
    disclosures: [],
    createdAt: '2026-01-01T00:00:00.000Z',
  };
}

describe('brand configuration', () => {
  it('discovers brands from the filesystem with no code change', () => {
    expect(listBrandIds()).toEqual(expect.arrayContaining(['kids-learning', 'maya']));
  });

  it('loads Maya.exe with its niche and three short-form platforms', () => {
    expect(maya.name).toBe('Maya.exe');
    expect(maya.platforms).toEqual(
      expect.arrayContaining(['tiktok', 'youtube_shorts', 'instagram_reels']),
    );
  });

  it('loads the kids brand on YouTube surfaces only', () => {
    expect(kids.platforms.every((p) => p.startsWith('youtube'))).toBe(true);
  });

  it('keeps the kids brand name configurable rather than hard-coded', () => {
    // The pipeline keys off the id; the display name is pure data.
    expect(kids.id).toBe('kids-learning');
    expect(typeof kids.name).toBe('string');
  });

  it('rejects a platform the brand does not publish to', () => {
    expect(checkPlatforms(kids, ['tiktok'])).toHaveLength(1);
    expect(checkPlatforms(kids, ['youtube'])).toHaveLength(0);
  });
});

describe('disclosure policy', () => {
  it('always requires the virtual creator badge for Maya.exe', () => {
    expect(maya.rules.requireAiDisclosure).toBe(true);
    expect(requiredDisclosures(maya, 'none')).toContain(maya.rules.aiDisclosureText);
  });

  it('adds an affiliate disclosure only on a paid path', () => {
    expect(requiredDisclosures(maya, 'affiliate')).toContain(maya.rules.affiliateDisclosureText);
    expect(requiredDisclosures(maya, 'sponsorship')).toContain(maya.rules.affiliateDisclosureText);
    expect(requiredDisclosures(maya, 'ad_revenue')).not.toContain(maya.rules.affiliateDisclosureText);
  });

  it('reports a missing disclosure as an error', () => {
    const brief = { monetizationPath: 'affiliate' } as ContentBrief;
    const violations = checkDisclosures(maya, brief, []);
    expect(violations.map((v) => v.rule)).toEqual(
      expect.arrayContaining(['missing_ai_disclosure', 'missing_affiliate_disclosure']),
    );
    expect(violations.every((v) => v.severity === 'error')).toBe(true);
  });
});

describe('child-directed rules', () => {
  it('forbids a purchase CTA', () => {
    const violations = checkChildDirected(kids, scriptWith('Buy it now at the link.'));
    expect(violations.map((v) => v.rule)).toContain('child_directed_purchase_cta');
  });

  it('forbids soliciting personal data', () => {
    const violations = checkChildDirected(kids, scriptWith('Watch again.', 'Enter your email to play.'));
    expect(violations.map((v) => v.rule)).toContain('child_directed_data_capture');
  });

  it('allows an ordinary watch-again CTA', () => {
    expect(checkChildDirected(kids, scriptWith('Watch the next lesson.'))).toEqual([]);
  });

  it('does not apply child rules to a non-child brand', () => {
    const adultScript = { ...scriptWith('Shop the link in bio.'), brandId: maya.id };
    expect(checkChildDirected(maya, adultScript)).toEqual([]);
  });

  it('marks the kids brand as child-directed with purchase CTAs disabled', () => {
    expect(kids.rules.childDirected).toBe(true);
    expect(kids.rules.allowPurchaseCta).toBe(false);
  });
});
