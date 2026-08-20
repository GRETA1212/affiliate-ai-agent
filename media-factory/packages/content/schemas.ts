import { z } from 'zod';

/**
 * What a model is asked to return. Narrower than the entity schemas: ids and
 * timestamps are assigned by the agent, never by the model.
 */

export const BriefDraftSchema = z.object({
  format: z.enum(['talking_head', 'listicle', 'demo_walkthrough', 'transformation', 'explainer']),
  hook: z.string().min(8),
  angle: z.string().min(8),
  audience: z.string().min(4),
  cta: z.string().min(4),
  monetizationPath: z.enum(['affiliate', 'own_product', 'sponsorship', 'lead_magnet', 'ad_revenue', 'none']),
  keyPoints: z.array(z.string().min(4)).min(2).max(6),
});
export type BriefDraft = z.infer<typeof BriefDraftSchema>;

export const ScriptDraftSchema = z.object({
  title: z.string().min(4),
  hook: z.string().min(4),
  cta: z.string().min(4),
  lines: z
    .array(
      z.object({
        sceneNumber: z.number().int().positive(),
        voiceover: z.string().min(4),
        onScreenText: z.string().min(2),
        durationSeconds: z.number().positive(),
        sourceId: z.string().nullable(),
      }),
    )
    .min(3),
});
export type ScriptDraft = z.infer<typeof ScriptDraftSchema>;

export const StoryboardDraftSchema = z.object({
  scenes: z
    .array(
      z.object({
        sceneNumber: z.number().int().positive(),
        durationSeconds: z.number().positive(),
        voiceover: z.string(),
        onScreenText: z.string(),
        visualDescription: z.string().min(8),
        assetRequirements: z.array(z.string().min(2)).min(1),
        transition: z.enum(['cut', 'fade', 'whip', 'push']),
      }),
    )
    .min(3),
});
export type StoryboardDraft = z.infer<typeof StoryboardDraftSchema>;

export const TASKS = {
  brief: 'content_brief',
  script: 'script',
  storyboard: 'storyboard',
} as const;
