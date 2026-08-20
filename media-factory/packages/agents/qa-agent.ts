import { now, stableId } from '../core/ids.ts';
import { detectBannedPhrases, detectClaims, containsNumericClaim } from '../compliance/claims.ts';
import {
  checkCaptions,
  checkChildDirected,
  checkDisclosures,
  checkTiming,
  type RuleViolation,
} from '../compliance/brand-rules.ts';
import type {
  AssetPlan,
  Brand,
  ContentBrief,
  QaFinding,
  QaReport,
  ResearchBundle,
  Script,
  Storyboard,
} from '../core/types.ts';

/**
 * QAAgent - the gate between "generated" and "publishable".
 *
 * Every check in the product spec is implemented here and named in
 * `checksRun`, so a passing report is auditable: you can see what was actually
 * examined, not just that something passed.
 *
 * Severity: `error` blocks publication, `warning` does not. Anything with legal
 * exposure (disclosures, child-directed rules, fabricated claims) is an error.
 */

export const QA_CHECKS = [
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
  'banned_phrases',
  'child_directed_rules',
  'synthetic_asset_honesty',
] as const;

function toFinding(violation: RuleViolation): QaFinding {
  return {
    rule: violation.rule,
    severity: violation.severity,
    message: violation.message,
    sceneNumber: violation.sceneNumber,
    evidence: violation.evidence,
  };
}

export interface QaInput {
  brand: Brand;
  brief: ContentBrief;
  script: Script;
  storyboard: Storyboard;
  assetPlan: AssetPlan;
  research: ResearchBundle;
  jobId: string;
}

export function runQaAgent(input: QaInput): QaReport {
  const { brand, brief, script, storyboard, assetPlan, research, jobId } = input;
  const findings: QaFinding[] = [];
  const citable = new Set(research.sources.map((s) => s.id));

  /* ---- claim checks, line by line ------------------------------------- */
  for (const line of script.lines) {
    const text = `${line.voiceover} ${line.onScreenText}`;

    for (const hit of detectClaims(text)) {
      const rule =
        hit.kind === 'price'
          ? 'fake_prices'
          : hit.kind === 'discount'
            ? 'fake_discounts'
            : hit.kind === 'statistic'
              ? 'fake_statistics'
              : hit.kind === 'physical_testing'
                ? 'synthetic_asset_honesty'
                : 'unsupported_claims';

      // A statistic backed by a real citation is allowed. Prices and discounts
      // never are: they go stale and become false the moment they change.
      const excusedByCitation =
        (hit.kind === 'statistic' || hit.kind === 'superlative') &&
        line.sourceId !== null &&
        citable.has(line.sourceId);
      if (excusedByCitation) continue;

      // Only flag testing language when the assets really are all synthetic.
      if (hit.kind === 'physical_testing' && !assetPlan.allSynthetic) continue;

      findings.push({
        rule,
        severity: 'error',
        message:
          hit.kind === 'physical_testing'
            ? 'first-person testing language, but every asset in this video is synthetic - nothing was physically tested'
            : `unsupported ${hit.kind} claim with no citation`,
        sceneNumber: line.sceneNumber,
        evidence: hit.match,
      });
    }

    for (const hit of detectBannedPhrases(text, brand.rules.bannedPhrases)) {
      findings.push({
        rule: 'banned_phrases',
        severity: 'error',
        message: `phrase banned by ${brand.name}: "${hit.match}"`,
        sceneNumber: line.sceneNumber,
        evidence: hit.match,
      });
    }

    /* ---- missing citations ------------------------------------------- */
    if (brand.rules.requireCitations && containsNumericClaim(text) && !line.sourceId) {
      findings.push({
        rule: 'missing_citations',
        severity: 'error',
        message: 'line states a number but carries no source id',
        sceneNumber: line.sceneNumber,
        evidence: text.trim().slice(0, 120),
      });
    }
    if (line.sourceId && !citable.has(line.sourceId)) {
      findings.push({
        rule: 'missing_citations',
        severity: 'error',
        message: `line cites "${line.sourceId}", which is not a registered approved source`,
        sceneNumber: line.sceneNumber,
      });
    }
  }

  /* ---- disclosures ----------------------------------------------------- */
  findings.push(...checkDisclosures(brand, brief, script.disclosures).map(toFinding));

  /* ---- child-directed rules ------------------------------------------- */
  findings.push(...checkChildDirected(brand, script).map(toFinding));

  /* ---- timing + captions ---------------------------------------------- */
  findings.push(...checkTiming(brand, storyboard).map(toFinding));
  findings.push(...checkCaptions(brand, storyboard).map(toFinding));

  /* ---- assets ---------------------------------------------------------- */
  const plannedScenes = new Set(assetPlan.assets.map((a) => a.sceneNumber));
  for (const scene of storyboard.scenes) {
    if (!plannedScenes.has(scene.sceneNumber)) {
      findings.push({
        rule: 'missing_assets',
        severity: 'error',
        message: 'scene has no planned asset',
        sceneNumber: scene.sceneNumber,
      });
    }
  }
  for (const asset of assetPlan.assets) {
    if (asset.status === 'placeholder' && !asset.synthetic) {
      // Warning, not error: a placeholder for real footage is fine during
      // review, it just must not be published.
      findings.push({
        rule: 'missing_assets',
        severity: 'warning',
        message: `scene ${asset.sceneNumber} needs real ${asset.type}; a placeholder is standing in`,
        sceneNumber: asset.sceneNumber,
      });
    }
  }

  const passed = findings.every((f) => f.severity !== 'error');

  return {
    id: stableId('qa', jobId),
    jobId,
    brandId: brand.id,
    passed,
    checksRun: [...QA_CHECKS],
    findings,
    createdAt: now(),
  };
}

export function summariseQa(report: QaReport): string {
  const errors = report.findings.filter((f) => f.severity === 'error').length;
  const warnings = report.findings.filter((f) => f.severity === 'warning').length;
  return `${report.passed ? 'PASS' : 'FAIL'} - ${report.checksRun.length} checks, ${errors} errors, ${warnings} warnings`;
}
