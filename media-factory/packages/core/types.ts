import { z } from 'zod';

/**
 * Single source of truth for every entity that crosses an agent boundary.
 * Every agent validates its own output against these schemas, so a malformed
 * LLM response fails at the producing agent instead of three steps later.
 */

export const PlatformSchema = z.enum(['tiktok', 'youtube_shorts', 'instagram_reels', 'youtube']);
export type Platform = z.infer<typeof PlatformSchema>;

export const MonetizationPathSchema = z.enum([
  'affiliate',
  'own_product',
  'sponsorship',
  'lead_magnet',
  'ad_revenue',
  'none',
]);
export type MonetizationPath = z.infer<typeof MonetizationPathSchema>;

export const AssetTypeSchema = z.enum([
  'generated_image',
  'stock_footage',
  'screen_recording',
  'product_broll',
  'animation',
  'text_graphic',
]);
export type AssetType = z.infer<typeof AssetTypeSchema>;

/* -------------------------------------------------------------------------- */
/* Brand                                                                       */
/* -------------------------------------------------------------------------- */

export const BrandThemeSchema = z.object({
  background: z.string(),
  backgroundAlt: z.string(),
  accent: z.string(),
  accentSoft: z.string(),
  text: z.string(),
  textMuted: z.string(),
  displayFont: z.string(),
  bodyFont: z.string(),
  utilityFont: z.string(),
  /** Visual signature the template is built around. Drives renderer branching. */
  signature: z.enum(['render_rail', 'lesson_stage']),
});
export type BrandTheme = z.infer<typeof BrandThemeSchema>;

export const BrandRulesSchema = z.object({
  /** Phrases that may never appear in a script for this brand. */
  bannedPhrases: z.array(z.string()).default([]),
  /** Numeric/statistical claims must carry a research source id. */
  requireCitations: z.boolean().default(true),
  /** Disclosure badge for synthetic/virtual creators. */
  requireAiDisclosure: z.boolean().default(false),
  aiDisclosureText: z.string().default('Virtual AI creator'),
  /** Affiliate/sponsor disclosure requirement when monetization is paid. */
  requireAffiliateDisclosure: z.boolean().default(true),
  affiliateDisclosureText: z.string().default('#ad - affiliate links'),
  /** Child-directed brands: no direct-response purchase CTA, no data capture. */
  childDirected: z.boolean().default(false),
  allowPurchaseCta: z.boolean().default(true),
  minDurationSeconds: z.number().int().positive().default(20),
  maxDurationSeconds: z.number().int().positive().default(60),
  maxCaptionCharsPerLine: z.number().int().positive().default(32),
  maxCaptionLinesPerScene: z.number().int().positive().default(3),
  minSceneSeconds: z.number().positive().default(1.5),
  maxSceneSeconds: z.number().positive().default(10),
});
export type BrandRules = z.infer<typeof BrandRulesSchema>;

export const BrandSchema = z.object({
  id: z.string(),
  name: z.string(),
  niche: z.string(),
  audience: z.string(),
  voice: z.string(),
  platforms: z.array(PlatformSchema).min(1),
  monetizationPaths: z.array(MonetizationPathSchema).min(1),
  defaultCta: z.string(),
  hashtags: z.array(z.string()).default([]),
  theme: BrandThemeSchema,
  rules: BrandRulesSchema,
});
export type Brand = z.infer<typeof BrandSchema>;

/* -------------------------------------------------------------------------- */
/* Research + evidence                                                         */
/* -------------------------------------------------------------------------- */

export const ResearchSourceSchema = z.object({
  id: z.string(),
  url: z.string().url(),
  title: z.string(),
  publisher: z.string(),
  /** ISO timestamp of when the evidence was captured, not when it was published. */
  capturedAt: z.string(),
  publishedAt: z.string().optional(),
  notes: z.string().optional(),
});
export type ResearchSource = z.infer<typeof ResearchSourceSchema>;

export const FactSchema = z.object({
  id: z.string(),
  statement: z.string(),
  /** Verified facts MUST carry a sourceId. Assumptions MUST NOT claim one. */
  kind: z.enum(['verified_fact', 'assumption']),
  sourceId: z.string().nullable(),
  numeric: z.boolean().default(false),
});
export type Fact = z.infer<typeof FactSchema>;

export const ResearchBundleSchema = z.object({
  id: z.string(),
  topic: z.string(),
  sources: z.array(ResearchSourceSchema),
  facts: z.array(FactSchema),
  gaps: z.array(z.string()).default([]),
  createdAt: z.string(),
});
export type ResearchBundle = z.infer<typeof ResearchBundleSchema>;

/* -------------------------------------------------------------------------- */
/* Opportunity + scoring                                                       */
/* -------------------------------------------------------------------------- */

/**
 * A signal is operator-supplied or connector-supplied observed evidence.
 * The scout may only rank signals; it may never author metrics itself.
 */
export const SignalSchema = z.object({
  id: z.string(),
  topic: z.string(),
  niche: z.string(),
  source: ResearchSourceSchema,
  metrics: z.object({
    attention: z.number().min(0).max(1),
    growth: z.number().min(0).max(1),
    commercialIntent: z.number().min(0).max(1),
    monetizationPotential: z.number().min(0).max(1),
    contentRepeatability: z.number().min(0).max(1),
    productOpportunity: z.number().min(0).max(1),
    saturation: z.number().min(0).max(1),
    risk: z.number().min(0).max(1),
  }),
  metricBasis: z.string(),
});
export type Signal = z.infer<typeof SignalSchema>;

export const ScoreBreakdownSchema = z.object({
  attention: z.number(),
  growth: z.number(),
  commercialIntent: z.number(),
  monetizationPotential: z.number(),
  contentRepeatability: z.number(),
  productOpportunity: z.number(),
  saturationPenalty: z.number(),
  riskPenalty: z.number(),
  total: z.number(),
});
export type ScoreBreakdown = z.infer<typeof ScoreBreakdownSchema>;

export const OpportunitySchema = z.object({
  id: z.string(),
  brandId: z.string(),
  topic: z.string(),
  niche: z.string(),
  score: ScoreBreakdownSchema,
  evidence: z.array(ResearchSourceSchema).min(1, 'an opportunity requires at least one source'),
  metricBasis: z.string(),
  createdAt: z.string(),
});
export type Opportunity = z.infer<typeof OpportunitySchema>;

/* -------------------------------------------------------------------------- */
/* Content                                                                     */
/* -------------------------------------------------------------------------- */

export const ContentBriefSchema = z.object({
  id: z.string(),
  brandId: z.string(),
  topic: z.string(),
  format: z.enum(['talking_head', 'listicle', 'demo_walkthrough', 'transformation', 'explainer']),
  hook: z.string(),
  audience: z.string(),
  angle: z.string(),
  cta: z.string(),
  monetizationPath: MonetizationPathSchema,
  keyPoints: z.array(z.string()).min(2),
  targetDurationSeconds: z.number().int().positive(),
  requiredDisclosures: z.array(z.string()).default([]),
  createdAt: z.string(),
});
export type ContentBrief = z.infer<typeof ContentBriefSchema>;

export const ScriptLineSchema = z.object({
  sceneNumber: z.number().int().positive(),
  voiceover: z.string().min(1),
  onScreenText: z.string().min(1),
  durationSeconds: z.number().positive(),
  /** Source id backing any factual/numeric statement in this line. */
  sourceId: z.string().nullable().default(null),
});
export type ScriptLine = z.infer<typeof ScriptLineSchema>;

export const ScriptSchema = z.object({
  id: z.string(),
  briefId: z.string(),
  brandId: z.string(),
  title: z.string(),
  hook: z.string(),
  cta: z.string(),
  lines: z.array(ScriptLineSchema).min(3),
  totalDurationSeconds: z.number().positive(),
  disclosures: z.array(z.string()).default([]),
  createdAt: z.string(),
});
export type Script = z.infer<typeof ScriptSchema>;

export const SceneSchema = z.object({
  sceneNumber: z.number().int().positive(),
  durationSeconds: z.number().positive(),
  voiceover: z.string(),
  onScreenText: z.string(),
  visualDescription: z.string(),
  assetRequirements: z.array(z.string()).min(1),
  transition: z.enum(['cut', 'fade', 'whip', 'push']),
});
export type Scene = z.infer<typeof SceneSchema>;

export const StoryboardSchema = z.object({
  id: z.string(),
  scriptId: z.string(),
  brandId: z.string(),
  scenes: z.array(SceneSchema).min(3),
  totalDurationSeconds: z.number().positive(),
  createdAt: z.string(),
});
export type Storyboard = z.infer<typeof StoryboardSchema>;

export const AssetSchema = z.object({
  id: z.string(),
  sceneNumber: z.number().int().positive(),
  type: AssetTypeSchema,
  description: z.string(),
  /** True when nothing physical was filmed or tested. Drives the QA claim rule. */
  synthetic: z.boolean(),
  status: z.enum(['placeholder', 'requested', 'ready']),
  uri: z.string().nullable().default(null),
  sourceNote: z.string().optional(),
});
export type Asset = z.infer<typeof AssetSchema>;

export const AssetPlanSchema = z.object({
  id: z.string(),
  storyboardId: z.string(),
  assets: z.array(AssetSchema).min(1),
  /** True when every asset in the plan is synthetic. */
  allSynthetic: z.boolean(),
  createdAt: z.string(),
});
export type AssetPlan = z.infer<typeof AssetPlanSchema>;

/* -------------------------------------------------------------------------- */
/* Render                                                                      */
/* -------------------------------------------------------------------------- */

export const RenderSceneSchema = z.object({
  index: z.number().int().nonnegative(),
  sceneNumber: z.number().int().positive(),
  durationSeconds: z.number().positive(),
  durationFrames: z.number().int().positive(),
  onScreenText: z.string(),
  captionLines: z.array(z.string()).min(1),
  visualDescription: z.string(),
  assetType: AssetTypeSchema,
  assetStatus: z.enum(['placeholder', 'requested', 'ready']),
  transition: z.enum(['cut', 'fade', 'whip', 'push']),
  isHook: z.boolean(),
  isCta: z.boolean(),
});
export type RenderScene = z.infer<typeof RenderSceneSchema>;

export const RenderInputSchema = z.object({
  jobId: z.string(),
  brandId: z.string(),
  brandName: z.string(),
  title: z.string(),
  width: z.literal(1080),
  height: z.literal(1920),
  fps: z.literal(30),
  totalFrames: z.number().int().positive(),
  hookText: z.string().min(1),
  ctaText: z.string().min(1),
  badges: z.object({
    brand: z.string(),
    disclosure: z.string().nullable(),
    affiliate: z.string().nullable(),
  }),
  theme: BrandThemeSchema,
  scenes: z.array(RenderSceneSchema).min(1),
  audio: z.object({
    trackPath: z.string().nullable(),
    /** Silent bed reserved for VO so timings stay honest before audio exists. */
    placeholderSilence: z.boolean(),
  }),
});
export type RenderInput = z.infer<typeof RenderInputSchema>;

export const VideoJobSchema = z.object({
  id: z.string(),
  brandId: z.string(),
  storyboardId: z.string(),
  status: z.enum(['queued', 'rendering', 'rendered', 'failed']),
  backend: z.enum(['remotion', 'ffmpeg']).nullable(),
  outputPath: z.string().nullable(),
  thumbnailPath: z.string().nullable(),
  durationSeconds: z.number().nullable(),
  error: z.string().nullable().default(null),
  createdAt: z.string(),
});
export type VideoJob = z.infer<typeof VideoJobSchema>;

/* -------------------------------------------------------------------------- */
/* QA + publishing                                                             */
/* -------------------------------------------------------------------------- */

export const QaFindingSchema = z.object({
  rule: z.string(),
  severity: z.enum(['error', 'warning']),
  message: z.string(),
  sceneNumber: z.number().int().positive().nullable().default(null),
  evidence: z.string().optional(),
});
export type QaFinding = z.infer<typeof QaFindingSchema>;

export const QaReportSchema = z.object({
  id: z.string(),
  jobId: z.string(),
  brandId: z.string(),
  passed: z.boolean(),
  checksRun: z.array(z.string()),
  findings: z.array(QaFindingSchema),
  createdAt: z.string(),
});
export type QaReport = z.infer<typeof QaReportSchema>;

export const PlatformManifestSchema = z.object({
  platform: PlatformSchema,
  caption: z.string(),
  hashtags: z.array(z.string()),
  /** Set on the platform's own upload form / official API. Never spoofed. */
  disclosureFlags: z.object({
    aiGeneratedContent: z.boolean(),
    paidPartnership: z.boolean(),
    madeForKids: z.boolean(),
  }),
  aspectRatio: z.literal('9:16'),
  maxDurationSeconds: z.number(),
  publishMethod: z.literal('manual_upload'),
  notes: z.array(z.string()).default([]),
});
export type PlatformManifest = z.infer<typeof PlatformManifestSchema>;

export const PublicationSchema = z.object({
  id: z.string(),
  jobId: z.string(),
  brandId: z.string(),
  videoPath: z.string(),
  thumbnailPath: z.string().nullable(),
  thumbnailFrameSeconds: z.number(),
  manifests: z.array(PlatformManifestSchema).min(1),
  qaPassed: z.boolean(),
  createdAt: z.string(),
});
export type Publication = z.infer<typeof PublicationSchema>;

/* -------------------------------------------------------------------------- */
/* Analytics + experiments                                                     */
/* -------------------------------------------------------------------------- */

export const AnalyticsRecordSchema = z.object({
  id: z.string(),
  brand: z.string(),
  platform: PlatformSchema,
  videoId: z.string(),
  topic: z.string(),
  hook: z.string(),
  views: z.number().int().nonnegative(),
  watchTimeSeconds: z.number().nonnegative(),
  completionRate: z.number().min(0).max(1),
  profileVisits: z.number().int().nonnegative(),
  clicks: z.number().int().nonnegative(),
  orders: z.number().int().nonnegative(),
  revenue: z.number().nonnegative(),
  revenuePer1000Views: z.number().nonnegative(),
  recordedAt: z.string(),
});
export type AnalyticsRecord = z.infer<typeof AnalyticsRecordSchema>;

export const ExperimentSchema = z.object({
  id: z.string(),
  brand: z.string(),
  sourceVideoId: z.string(),
  topic: z.string(),
  decision: z.enum(['scale', 'iterate', 'pause']),
  variationOf: z.string().nullable(),
  variationAxis: z.enum(['hook', 'format', 'cta', 'none']),
  hypothesis: z.string(),
  status: z.enum(['proposed', 'running', 'closed']),
  createdAt: z.string(),
});
export type Experiment = z.infer<typeof ExperimentSchema>;
