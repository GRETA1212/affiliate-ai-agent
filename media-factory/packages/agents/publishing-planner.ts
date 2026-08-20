import { now, stableId } from '../core/ids.ts';
import type {
  Brand,
  ContentBrief,
  PlatformManifest,
  Publication,
  QaReport,
  RenderInput,
  Script,
} from '../core/types.ts';
import { thumbnailFrame } from '../renderer/build-render-input.ts';

/**
 * PublishingPlanner.
 *
 * Explicit non-goal: this never uploads anything. `publishMethod` is
 * `manual_upload` on every manifest, and there is no code path that posts to a
 * platform. Automated publishing is only ever added later through the
 * platforms' own authorised APIs with OAuth - never by driving a logged-in
 * session, and never by working around a platform restriction.
 *
 * What it produces is everything a human needs to upload correctly: caption,
 * hashtags, the disclosure toggles to set in the upload form, a thumbnail
 * suggestion, and the duration limits for each destination.
 */

/** Platform limits for short-form vertical uploads. Verify before relying on them. */
const PLATFORM_LIMITS: Record<string, { maxDurationSeconds: number; captionLimit: number; hashtagCount: number }> = {
  tiktok: { maxDurationSeconds: 600, captionLimit: 2200, hashtagCount: 5 },
  instagram_reels: { maxDurationSeconds: 180, captionLimit: 2200, hashtagCount: 8 },
  youtube_shorts: { maxDurationSeconds: 180, captionLimit: 5000, hashtagCount: 4 },
  youtube: { maxDurationSeconds: 43200, captionLimit: 5000, hashtagCount: 4 },
};

function buildCaption(brand: Brand, brief: ContentBrief, script: Script, limit: number): string {
  const disclosureLine = script.disclosures.length ? script.disclosures.join(' · ') : null;
  const parts = [script.hook, brief.angle ? `${brief.angle}.` : null, script.cta, disclosureLine].filter(
    Boolean,
  ) as string[];
  const caption = parts.join('\n\n');
  return caption.length <= limit ? caption : `${caption.slice(0, limit - 1)}…`;
}

export function buildManifests(
  brand: Brand,
  brief: ContentBrief,
  script: Script,
  renderInput: RenderInput,
): PlatformManifest[] {
  const durationSeconds = renderInput.totalFrames / renderInput.fps;
  const paid = brief.monetizationPath === 'affiliate' || brief.monetizationPath === 'sponsorship';

  return brand.platforms.map((platform) => {
    const limits = PLATFORM_LIMITS[platform] ?? {
      maxDurationSeconds: 180,
      captionLimit: 2200,
      hashtagCount: 5,
    };

    const notes: string[] = [
      'Upload manually. This tool does not post to platforms and does not bypass any platform restriction.',
    ];
    if (durationSeconds > limits.maxDurationSeconds) {
      notes.push(
        `video runs ${durationSeconds.toFixed(1)}s, above this platform's ${limits.maxDurationSeconds}s limit for this format`,
      );
    }
    if (brand.rules.requireAiDisclosure) {
      notes.push(`set the platform's AI-generated content toggle, and keep the "${brand.rules.aiDisclosureText}" badge visible`);
    }
    if (paid) {
      notes.push("set the platform's paid partnership / branded content toggle");
    }
    if (brand.rules.childDirected) {
      notes.push('set the audience to "Made for Kids" and verify current child-content requirements before publishing');
    }

    return {
      platform,
      caption: buildCaption(brand, brief, script, limits.captionLimit),
      hashtags: brand.hashtags.slice(0, limits.hashtagCount),
      disclosureFlags: {
        aiGeneratedContent: brand.rules.requireAiDisclosure,
        paidPartnership: paid,
        madeForKids: brand.rules.childDirected,
      },
      aspectRatio: '9:16' as const,
      maxDurationSeconds: limits.maxDurationSeconds,
      publishMethod: 'manual_upload' as const,
      notes,
    };
  });
}

export function runPublishingPlanner(args: {
  brand: Brand;
  brief: ContentBrief;
  script: Script;
  renderInput: RenderInput;
  qa: QaReport;
  videoPath: string;
  thumbnailPath: string | null;
}): Publication {
  const { brand, brief, script, renderInput, qa, videoPath, thumbnailPath } = args;

  return {
    id: stableId('publication', renderInput.jobId),
    jobId: renderInput.jobId,
    brandId: brand.id,
    videoPath,
    thumbnailPath,
    thumbnailFrameSeconds: Number((thumbnailFrame(renderInput) / renderInput.fps).toFixed(2)),
    manifests: buildManifests(brand, brief, script, renderInput),
    // Recorded, not enforced here: the CLI refuses to treat a failing package
    // as publish-ready, but the manifest still gets written for review.
    qaPassed: qa.passed,
    createdAt: now(),
  };
}
