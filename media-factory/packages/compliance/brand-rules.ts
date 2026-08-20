import type { Brand, ContentBrief, Script, Storyboard } from '../core/types.ts';
import { wrapText } from '../core/text.ts';

/**
 * Brand-level policy. Everything here is driven by brand.json, so adding a
 * brand never means editing this file.
 */

export interface RuleViolation {
  rule: string;
  severity: 'error' | 'warning';
  message: string;
  sceneNumber: number | null;
  evidence?: string;
}

/* -------------------------------------------------------------------------- */
/* Disclosures                                                                 */
/* -------------------------------------------------------------------------- */

/** The disclosures this brand + monetization path require on the video itself. */
export function requiredDisclosures(brand: Brand, monetizationPath: string): string[] {
  const required: string[] = [];
  if (brand.rules.requireAiDisclosure) required.push(brand.rules.aiDisclosureText);
  const paid = monetizationPath === 'affiliate' || monetizationPath === 'sponsorship';
  if (brand.rules.requireAffiliateDisclosure && paid) {
    required.push(brand.rules.affiliateDisclosureText);
  }
  return required;
}

export function checkDisclosures(
  brand: Brand,
  brief: ContentBrief,
  declared: string[],
): RuleViolation[] {
  const violations: RuleViolation[] = [];
  const have = new Set(declared.map((d) => d.toLowerCase().trim()));

  for (const needed of requiredDisclosures(brand, brief.monetizationPath)) {
    if (!have.has(needed.toLowerCase().trim())) {
      const isAi = needed === brand.rules.aiDisclosureText;
      violations.push({
        rule: isAi ? 'missing_ai_disclosure' : 'missing_affiliate_disclosure',
        severity: 'error',
        message: `required disclosure is missing: "${needed}"`,
        sceneNumber: null,
      });
    }
  }
  return violations;
}

/* -------------------------------------------------------------------------- */
/* Child-directed rules                                                        */
/* -------------------------------------------------------------------------- */

const PURCHASE_CTA = /\b(?:buy|purchase|order|shop|add to cart|link in bio|swipe up|use code)\b/i;
const DATA_CAPTURE = /\b(?:sign up|subscribe to our list|enter your email|your address|dm me)\b/i;

/**
 * Child-directed content may not push a purchase or collect data. This is a
 * legal boundary (COPPA / UK Children's Code), so these are errors, not hints.
 */
export function checkChildDirected(brand: Brand, script: Script): RuleViolation[] {
  if (!brand.rules.childDirected) return [];
  const violations: RuleViolation[] = [];

  for (const line of script.lines) {
    const text = `${line.voiceover} ${line.onScreenText}`;
    if (!brand.rules.allowPurchaseCta && PURCHASE_CTA.test(text)) {
      violations.push({
        rule: 'child_directed_purchase_cta',
        severity: 'error',
        message: 'child-directed content must not contain a purchase call to action',
        sceneNumber: line.sceneNumber,
        evidence: text.match(PURCHASE_CTA)?.[0],
      });
    }
    if (DATA_CAPTURE.test(text)) {
      violations.push({
        rule: 'child_directed_data_capture',
        severity: 'error',
        message: 'child-directed content must not solicit personal data',
        sceneNumber: line.sceneNumber,
        evidence: text.match(DATA_CAPTURE)?.[0],
      });
    }
  }

  if (PURCHASE_CTA.test(script.cta) && !brand.rules.allowPurchaseCta) {
    violations.push({
      rule: 'child_directed_purchase_cta',
      severity: 'error',
      message: 'the closing CTA is a purchase prompt, which this brand forbids',
      sceneNumber: null,
      evidence: script.cta,
    });
  }
  return violations;
}

/* -------------------------------------------------------------------------- */
/* Timing + captions                                                           */
/* -------------------------------------------------------------------------- */

export function checkTiming(brand: Brand, storyboard: Storyboard): RuleViolation[] {
  const violations: RuleViolation[] = [];
  const { minSceneSeconds, maxSceneSeconds, minDurationSeconds, maxDurationSeconds } = brand.rules;

  for (const scene of storyboard.scenes) {
    if (scene.durationSeconds < minSceneSeconds) {
      violations.push({
        rule: 'scene_too_short',
        severity: 'error',
        message: `scene runs ${scene.durationSeconds}s, below the ${minSceneSeconds}s minimum`,
        sceneNumber: scene.sceneNumber,
      });
    }
    if (scene.durationSeconds > maxSceneSeconds) {
      violations.push({
        rule: 'scene_too_long',
        severity: 'error',
        message: `scene runs ${scene.durationSeconds}s, above the ${maxSceneSeconds}s maximum`,
        sceneNumber: scene.sceneNumber,
      });
    }
    // A scene must be long enough to actually speak its voiceover.
    const words = scene.voiceover.trim().split(/\s+/).filter(Boolean).length;
    const needed = words / 2.6;
    if (needed > scene.durationSeconds + 0.25) {
      violations.push({
        rule: 'voiceover_exceeds_scene',
        severity: 'error',
        message: `voiceover needs about ${needed.toFixed(1)}s but the scene is ${scene.durationSeconds}s`,
        sceneNumber: scene.sceneNumber,
      });
    }
  }

  const total = storyboard.totalDurationSeconds;
  const summed = Number(storyboard.scenes.reduce((s, sc) => s + sc.durationSeconds, 0).toFixed(2));
  if (Math.abs(total - summed) > 0.5) {
    violations.push({
      rule: 'duration_mismatch',
      severity: 'error',
      message: `declared total ${total}s does not match the sum of scenes ${summed}s`,
      sceneNumber: null,
    });
  }
  if (total < minDurationSeconds || total > maxDurationSeconds) {
    violations.push({
      rule: 'duration_out_of_range',
      severity: 'error',
      message: `total ${total}s is outside the brand range ${minDurationSeconds}-${maxDurationSeconds}s`,
      sceneNumber: null,
    });
  }
  return violations;
}

export function checkCaptions(brand: Brand, storyboard: Storyboard): RuleViolation[] {
  const { maxCaptionCharsPerLine, maxCaptionLinesPerScene } = brand.rules;
  const violations: RuleViolation[] = [];

  for (const scene of storyboard.scenes) {
    const lines = wrapText(scene.onScreenText, maxCaptionCharsPerLine);
    if (lines.length > maxCaptionLinesPerScene) {
      violations.push({
        rule: 'caption_overflow',
        severity: 'error',
        message: `on-screen text wraps to ${lines.length} lines, above the ${maxCaptionLinesPerScene}-line limit`,
        sceneNumber: scene.sceneNumber,
        evidence: scene.onScreenText,
      });
    }
  }
  return violations;
}

/** Platform targets must be ones this brand actually publishes to. */
export function checkPlatforms(brand: Brand, platforms: string[]): RuleViolation[] {
  return platforms
    .filter((p) => !brand.platforms.includes(p as Brand['platforms'][number]))
    .map((p) => ({
      rule: 'platform_not_configured',
      severity: 'error' as const,
      message: `"${p}" is not a configured platform for ${brand.name}`,
      sceneNumber: null,
    }));
}
