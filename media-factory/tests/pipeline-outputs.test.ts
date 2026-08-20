import { describe, expect, it } from 'vitest';
import { buildMockProvider } from '../packages/content/mock-content.ts';
import { loadBrand } from '../packages/core/brand.ts';
import { planContent } from '../packages/agents/content-strategist.ts';
import { writeScript } from '../packages/agents/script-agent.ts';
import { buildStoryboard } from '../packages/agents/storyboard-agent.ts';
import { planAssets } from '../packages/agents/asset-planner.ts';
import { buildRenderInput, thumbnailFrame, sceneStartFrames, FPS } from '../packages/renderer/build-render-input.ts';
import { runPublishingPlanner } from '../packages/agents/publishing-planner.ts';
import { runQaAgent } from '../packages/agents/qa-agent.ts';
import { research } from '../packages/research/research-agent.ts';
import {
  ContentBriefSchema,
  PublicationSchema,
  RenderInputSchema,
  ScriptSchema,
  StoryboardSchema,
} from '../packages/core/types.ts';

const maya = loadBrand('maya');
const provider = buildMockProvider();
const TOPIC = 'AI chooses a 10-minute makeup look';

async function buildPackage(brandId = 'maya') {
  const brand = loadBrand(brandId);
  const bundle = research({ brandId: brand.id, topic: TOPIC });
  const brief = await planContent({
    brand,
    topic: TOPIC,
    facts: bundle.facts,
    provider,
    syntheticAssets: true,
  });
  const script = await writeScript({ brand, brief, facts: bundle.facts, provider, allSynthetic: true });
  const storyboard = await buildStoryboard({ brand, script, provider });
  const assetPlan = planAssets({ storyboard, mode: 'synthetic' });
  const renderInput = buildRenderInput({
    jobId: 'job_test',
    brand,
    brief,
    script,
    storyboard,
    assetPlan,
  });
  return { brand, bundle, brief, script, storyboard, assetPlan, renderInput };
}

/* -------------------------------------------------------------------------- */
/* structured outputs                                                          */
/* -------------------------------------------------------------------------- */

describe('structured agent outputs', () => {
  it('produces a schema-valid brief, script and storyboard with no API key', async () => {
    const { brief, script, storyboard } = await buildPackage();
    expect(() => ContentBriefSchema.parse(brief)).not.toThrow();
    expect(() => ScriptSchema.parse(script)).not.toThrow();
    expect(() => StoryboardSchema.parse(storyboard)).not.toThrow();
  });

  it('is deterministic: the same topic yields the same script', async () => {
    const a = await buildPackage();
    const b = await buildPackage();
    expect(b.script.lines).toEqual(a.script.lines);
  });

  it('numbers scenes densely from 1', async () => {
    const { script } = await buildPackage();
    expect(script.lines.map((l) => l.sceneNumber)).toEqual(script.lines.map((_, i) => i + 1));
  });

  it('gives every scene enough time to speak its own voiceover', async () => {
    const { script } = await buildPackage();
    for (const line of script.lines) {
      const words = line.voiceover.trim().split(/\s+/).length;
      expect(line.durationSeconds + 0.25).toBeGreaterThanOrEqual(words / 2.6);
    }
  });

  it('lands inside the brand duration window', async () => {
    const { script } = await buildPackage();
    expect(script.totalDurationSeconds).toBeGreaterThanOrEqual(maya.rules.minDurationSeconds);
    expect(script.totalDurationSeconds).toBeLessThanOrEqual(maya.rules.maxDurationSeconds);
  });

  it('never repeats a voiceover line verbatim', async () => {
    const { script } = await buildPackage();
    const seen = script.lines.map((l) => l.voiceover);
    expect(new Set(seen).size).toBe(seen.length);
  });

  it('carries the brand disclosures onto the script', async () => {
    const { script } = await buildPackage();
    expect(script.disclosures).toContain(maya.rules.aiDisclosureText);
  });

  it('produces one storyboard scene per script line', async () => {
    const { script, storyboard } = await buildPackage();
    expect(storyboard.scenes).toHaveLength(script.lines.length);
  });

  it('marks every asset synthetic when nothing was filmed', async () => {
    const { assetPlan } = await buildPackage();
    expect(assetPlan.allSynthetic).toBe(true);
    expect(assetPlan.assets.every((a) => a.synthetic)).toBe(true);
  });

  it('produces a QA-clean package for both brands out of the box', async () => {
    for (const brandId of ['maya', 'kids-learning']) {
      const pkg = await buildPackage(brandId);
      const report = runQaAgent({ ...pkg, research: pkg.bundle, jobId: 'job_test' });
      expect(report.findings.filter((f) => f.severity === 'error'), brandId).toEqual([]);
      expect(report.passed, brandId).toBe(true);
    }
  });
});

/* -------------------------------------------------------------------------- */
/* renderer input                                                              */
/* -------------------------------------------------------------------------- */

describe('renderer input', () => {
  it('is a valid 1080x1920 30fps contract', async () => {
    const { renderInput } = await buildPackage();
    expect(() => RenderInputSchema.parse(renderInput)).not.toThrow();
    expect(renderInput.width).toBe(1080);
    expect(renderInput.height).toBe(1920);
    expect(renderInput.fps).toBe(30);
  });

  it('total frames equal the sum of the scene frames', async () => {
    const { renderInput } = await buildPackage();
    const summed = renderInput.scenes.reduce((s, scene) => s + scene.durationFrames, 0);
    expect(renderInput.totalFrames).toBe(summed);
  });

  it('converts seconds to frames consistently', async () => {
    const { renderInput } = await buildPackage();
    for (const scene of renderInput.scenes) {
      expect(scene.durationFrames).toBe(Math.round(scene.durationSeconds * FPS));
    }
  });

  it('pre-wraps captions within the brand line limit', async () => {
    const { renderInput } = await buildPackage();
    for (const scene of renderInput.scenes) {
      expect(scene.captionLines.length).toBeLessThanOrEqual(maya.rules.maxCaptionLinesPerScene);
      for (const line of scene.captionLines) {
        expect(line.length).toBeLessThanOrEqual(maya.rules.maxCaptionCharsPerLine);
      }
    }
  });

  it('carries the persistent AI disclosure badge for Maya.exe', async () => {
    const { renderInput } = await buildPackage();
    expect(renderInput.badges.disclosure).toBe(maya.rules.aiDisclosureText);
  });

  it('marks exactly one hook scene and one CTA scene', async () => {
    const { renderInput } = await buildPackage();
    expect(renderInput.scenes.filter((s) => s.isHook)).toHaveLength(1);
    expect(renderInput.scenes.filter((s) => s.isCta)).toHaveLength(1);
    expect(renderInput.scenes[0]?.isHook).toBe(true);
  });

  it('reserves a silent audio bed when no voiceover track exists', async () => {
    const { renderInput } = await buildPackage();
    expect(renderInput.audio.trackPath).toBeNull();
    expect(renderInput.audio.placeholderSilence).toBe(true);
  });

  it('computes scene start frames contiguously', async () => {
    const { renderInput } = await buildPackage();
    const starts = sceneStartFrames(renderInput);
    expect(starts[0]).toBe(0);
    for (let i = 1; i < starts.length; i++) {
      expect(starts[i]).toBe((starts[i - 1] as number) + (renderInput.scenes[i - 1]?.durationFrames as number));
    }
  });

  it('suggests a thumbnail inside the hook scene', async () => {
    const { renderInput } = await buildPackage();
    const frame = thumbnailFrame(renderInput);
    expect(frame).toBeGreaterThanOrEqual(0);
    expect(frame).toBeLessThan(renderInput.scenes[0]?.durationFrames as number);
  });
});

/* -------------------------------------------------------------------------- */
/* publication manifest                                                        */
/* -------------------------------------------------------------------------- */

describe('publication manifest', () => {
  async function publication(brandId = 'maya') {
    const pkg = await buildPackage(brandId);
    const qa = runQaAgent({ ...pkg, research: pkg.bundle, jobId: 'job_test' });
    return runPublishingPlanner({
      brand: pkg.brand,
      brief: pkg.brief,
      script: pkg.script,
      renderInput: pkg.renderInput,
      qa,
      videoPath: '/tmp/video.mp4',
      thumbnailPath: '/tmp/thumb.png',
    });
  }

  it('is schema valid', async () => {
    const pub = await publication();
    expect(() => PublicationSchema.parse(pub)).not.toThrow();
  });

  it('produces one manifest per configured platform', async () => {
    const pub = await publication();
    expect(pub.manifests.map((m) => m.platform).sort()).toEqual([...maya.platforms].sort());
  });

  it('never automates publishing', async () => {
    const pub = await publication();
    for (const manifest of pub.manifests) {
      expect(manifest.publishMethod).toBe('manual_upload');
      expect(manifest.notes.join(' ')).toMatch(/does not bypass any platform restriction/i);
    }
  });

  it('is 9:16 on every platform', async () => {
    const pub = await publication();
    expect(pub.manifests.every((m) => m.aspectRatio === '9:16')).toBe(true);
  });

  it('sets the AI-content flag for a virtual creator', async () => {
    const pub = await publication();
    expect(pub.manifests.every((m) => m.disclosureFlags.aiGeneratedContent)).toBe(true);
  });

  it('sets made-for-kids and never paid partnership on the kids brand', async () => {
    const pub = await publication('kids-learning');
    for (const manifest of pub.manifests) {
      expect(manifest.disclosureFlags.madeForKids).toBe(true);
      expect(manifest.disclosureFlags.paidPartnership).toBe(false);
    }
  });

  it('includes the disclosure text in the caption', async () => {
    const pub = await publication();
    expect(pub.manifests[0]?.caption).toContain(maya.rules.aiDisclosureText);
  });

  it('records a thumbnail timecode inside the video', async () => {
    const pub = await publication();
    expect(pub.thumbnailFrameSeconds).toBeGreaterThanOrEqual(0);
  });
});
