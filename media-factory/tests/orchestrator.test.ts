import { describe, expect, it } from 'vitest';
import { buildMockProvider } from '../packages/content/mock-content.ts';
import { loadBrand } from '../packages/core/brand.ts';
import { runPipeline } from '../packages/orchestrator/graph.ts';

const provider = buildMockProvider();
const maya = loadBrand('maya');
const kids = loadBrand('kids-learning');
const TOPIC = 'AI chooses a 10-minute makeup look';

/**
 * These run with skipRender so the graph is exercised without invoking ffmpeg.
 * The render node itself is covered by the demo run in the README.
 */
async function run(brand = maya, topic = TOPIC) {
  return runPipeline({ provider, brand, topic, skipRender: true });
}

describe('orchestrator state transitions', () => {
  it('visits every agent in dependency order', async () => {
    const state = await run();
    expect(state.steps).toEqual([
      'scout',
      'research_agent',
      'strategist',
      'script_agent',
      'storyboard_agent',
      'assets',
      'render:skipped',
      'qa_agent',
      'publish',
    ]);
  });

  it('accumulates each artifact into shared state', async () => {
    const state = await run();
    expect(state.research).not.toBeNull();
    expect(state.brief).not.toBeNull();
    expect(state.script).not.toBeNull();
    expect(state.storyboard).not.toBeNull();
    expect(state.assetPlan).not.toBeNull();
    expect(state.renderInput).not.toBeNull();
    expect(state.qa).not.toBeNull();
  });

  it('keeps artifact ids referentially consistent down the chain', async () => {
    const state = await run();
    expect(state.script?.briefId).toBe(state.brief?.id);
    expect(state.storyboard?.scriptId).toBe(state.script?.id);
    expect(state.assetPlan?.storyboardId).toBe(state.storyboard?.id);
    expect(state.renderInput?.jobId).toBe(state.jobId);
  });

  it('routes a QA-passing package to publish', async () => {
    const state = await run();
    expect(state.qa?.passed).toBe(true);
    expect(state.steps).toContain('publish');
    expect(state.steps).not.toContain('halt');
    expect(state.publication).not.toBeNull();
  });

  it('halts instead of publishing when QA fails', async () => {
    // A brand whose own rules ban a phrase the script will contain guarantees a
    // QA failure without having to stub any agent.
    const sabotaged = {
      ...maya,
      rules: { ...maya.rules, bannedPhrases: ['AI'] },
    };
    const state = await runPipeline({ provider, brand: sabotaged, topic: TOPIC, skipRender: true });
    expect(state.qa?.passed).toBe(false);
    expect(state.steps).toContain('halt');
    expect(state.steps).not.toContain('publish');
    // The gate's whole purpose: no manifest is produced for a failing package.
    expect(state.publication).toBeNull();
  });

  it('attaches the opportunity evidence when a signal matches the topic', async () => {
    const state = await run();
    expect(state.opportunity).not.toBeNull();
    expect(state.opportunity?.evidence.length).toBeGreaterThan(0);
  });

  it('proceeds with a loud warning when no signal matches the topic', async () => {
    const state = await run(maya, 'a topic with no recorded signal whatsoever');
    expect(state.opportunity).toBeNull();
    expect(state.warnings.join(' ')).toMatch(/no recorded signal/i);
    // It still produces a package: the operator asked for this topic explicitly.
    expect(state.script).not.toBeNull();
  });

  it('surfaces placeholder-evidence warnings rather than swallowing them', async () => {
    const state = await run();
    expect(state.warnings.join(' ')).toMatch(/PLACEHOLDER/);
  });

  it('reports the missing-verified-facts gap so the script stays claim-free', async () => {
    const state = await run();
    expect(state.warnings.join(' ')).toMatch(/no verified facts/i);
  });

  it('runs the kids brand through the same graph', async () => {
    const state = await run(kids, 'Counting to ten with everyday objects');
    expect(state.qa?.passed).toBe(true);
    expect(state.publication?.manifests.every((m) => m.disclosureFlags.madeForKids)).toBe(true);
  });

  it('is deterministic across runs', async () => {
    const a = await run();
    const b = await run();
    expect(b.script?.lines).toEqual(a.script?.lines);
    expect(b.jobId).toBe(a.jobId);
  });

  it('marks the job queued rather than rendered when rendering is skipped', async () => {
    const state = await run();
    expect(state.videoJob?.status).toBe('queued');
    expect(state.videoJob?.outputPath).toBeNull();
  });
});
