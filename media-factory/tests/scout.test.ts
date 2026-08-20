import { describe, expect, it } from 'vitest';
import { isPlaceholderSource, scout } from '../packages/agents/opportunity-scout.ts';
import { loadBrand } from '../packages/core/brand.ts';
import type { Signal } from '../packages/core/types.ts';

const maya = loadBrand('maya');

function signal(overrides: Partial<Signal> = {}): Signal {
  return {
    id: 'sig_a',
    topic: 'AI picks a base shade',
    niche: maya.niche,
    source: {
      id: 'src_a',
      url: 'https://research.example.org/report',
      title: 'captured evidence',
      publisher: 'example',
      capturedAt: '2026-02-01T00:00:00.000Z',
    },
    metrics: {
      attention: 0.8,
      growth: 0.7,
      commercialIntent: 0.6,
      monetizationPotential: 0.6,
      contentRepeatability: 0.7,
      productOpportunity: 0.5,
      saturation: 0.2,
      risk: 0.1,
    },
    metricBasis: 'operator capture',
    ...overrides,
  };
}

describe('opportunity scout: evidence discipline', () => {
  it('returns nothing and says so when there are no signals', () => {
    const result = scout({ brand: maya, signals: [] });
    expect(result.opportunities).toEqual([]);
    expect(result.notice).toMatch(/does not generate trend data/i);
  });

  it('never invents a topic that was not in the signals', () => {
    const result = scout({ brand: maya, signals: [signal()] });
    expect(result.opportunities).toHaveLength(1);
    expect(result.opportunities[0]?.topic).toBe('AI picks a base shade');
  });

  it('carries the source through to the opportunity as evidence', () => {
    const result = scout({ brand: maya, signals: [signal()] });
    const evidence = result.opportunities[0]?.evidence ?? [];
    expect(evidence).toHaveLength(1);
    expect(evidence[0]?.url).toBe('https://research.example.org/report');
    expect(evidence[0]?.capturedAt).toBe('2026-02-01T00:00:00.000Z');
  });

  it('rejects a signal whose source has no url', () => {
    const bad = signal({ source: { ...signal().source, url: '' } });
    const result = scout({ brand: maya, signals: [bad] });
    expect(result.opportunities).toHaveLength(0);
    expect(result.rejected[0]?.reason).toMatch(/evidence|url/i);
  });

  it('ranks higher-scoring opportunities first', () => {
    const weak = signal({
      id: 'sig_weak',
      topic: 'weak topic',
      metrics: { ...signal().metrics, attention: 0.1, growth: 0.1, saturation: 0.9 },
    });
    const result = scout({ brand: maya, signals: [weak, signal()] });
    expect(result.opportunities[0]?.topic).toBe('AI picks a base shade');
  });

  it('filters by topic when one is requested', () => {
    const other = signal({ id: 'sig_b', topic: 'skincare ordering' });
    const result = scout({ brand: maya, signals: [signal(), other], topic: 'skincare' });
    expect(result.opportunities.map((o) => o.topic)).toEqual(['skincare ordering']);
  });

  it('flags unreplaced template evidence rather than passing it off as data', () => {
    const placeholder = signal({
      source: { ...signal().source, url: 'https://operator-notes.invalid/maya/x' },
    });
    const result = scout({ brand: maya, signals: [placeholder] });
    expect(result.placeholderEvidenceOnly).toBe(true);
    expect(result.warnings.join(' ')).toMatch(/PLACEHOLDER/);
  });

  it('warns when a cited source has never actually been captured', () => {
    const uncaptured = signal({
      source: { ...signal().source, capturedAt: '1970-01-01T00:00:00.000Z' },
    });
    const result = scout({ brand: maya, signals: [uncaptured] });
    expect(result.warnings.join(' ')).toMatch(/never been captured/i);
  });

  it('treats reserved and example hostnames as placeholders', () => {
    expect(isPlaceholderSource('https://operator-notes.invalid/x')).toBe(true);
    expect(isPlaceholderSource('https://example.com/x')).toBe(true);
    expect(isPlaceholderSource('not a url')).toBe(true);
    expect(isPlaceholderSource('https://www.ftc.gov/guidance')).toBe(false);
  });

  it('the shipped Maya signals are all placeholders, so nobody mistakes them for real data', () => {
    const result = scout({ brand: maya });
    expect(result.opportunities.length).toBeGreaterThan(0);
    expect(result.placeholderEvidenceOnly).toBe(true);
  });
});
