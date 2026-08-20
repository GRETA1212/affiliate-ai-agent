import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type { RenderInput, RenderScene } from '../../core/types.ts';
import { HOOK_CHIP_MAX_CHARS, truncateWords } from '../../core/text.ts';

/**
 * The reusable 9:16 template. Every brand renders through this component; the
 * differences come from `theme` and `theme.signature`, not from forked code.
 *
 * Layout is built around the platform-safe area: TikTok, Reels and Shorts all
 * overlay UI at the bottom-right and bottom edge, so captions sit in the middle
 * third and the CTA never hugs the bottom.
 */

const SAFE_TOP = 260;
const SAFE_BOTTOM = 420;
const CAPTION_SAFE_WIDTH = 920;
const CAPTION_MIN_FONT_SIZE = 42;

type RuntimeRenderScene = RenderScene & {
  assetUri?: string | null;
  assetSourceNote?: string | null;
  assetMediaKind?: 'image' | 'video' | 'graphic' | null;
};

function fitCaptionFontSize(lines: string[], fontFamily: string, initialSize: number): number {
  if (typeof document === 'undefined') return initialSize;
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return initialSize;
  for (let size = initialSize; size >= CAPTION_MIN_FONT_SIZE; size -= 2) {
    ctx.font = `700 ${size}px ${fontFamily}`;
    if (lines.every((line) => ctx.measureText(line).width <= CAPTION_SAFE_WIDTH)) return size;
  }
  return CAPTION_MIN_FONT_SIZE;
}

export const VerticalVideo: React.FC<{ input: RenderInput }> = ({ input }) => {
  const { theme } = input;
  let cursor = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: theme.background }}>
      {input.scenes.map((rawScene) => {
        const scene = rawScene as RuntimeRenderScene;
        const from = cursor;
        cursor += scene.durationFrames;
        return (
          <Sequence key={scene.sceneNumber} from={from} durationInFrames={scene.durationFrames}>
            <SceneLayer scene={scene} input={input} />
          </Sequence>
        );
      })}

      <BadgeRail input={input} />

      {/* Optional separate VO/music bed. Provider video audio is used only when
          no separate audio track is configured, preventing doubled speech. */}
      {input.audio.trackPath ? <Audio src={staticFile(input.audio.trackPath)} /> : null}
    </AbsoluteFill>
  );
};

const SceneLayer: React.FC<{ scene: RuntimeRenderScene; input: RenderInput }> = ({ scene, input }) => {
  const frame = useCurrentFrame();
  const { theme } = input;
  const captionFontSize = fitCaptionFontSize(scene.captionLines, theme.displayFont, scene.isCta ? 92 : 78);

  // Transitions are entry effects on each scene, kept cheap and legible.
  // The opening scene must be fully visible at frame 0. Fading it up from
  // zero leaves the first frame blank, and platforms often use frame 0 as the
  // poster image - a black poster on the hook is the worst place to lose a
  // viewer. Later scenes still fade, where it reads as an intentional cut.
  const fadeInEnd = scene.transition === 'fade' ? 12 : 4;
  const fadeIn = scene.isHook
    ? 1
    : interpolate(frame, [0, fadeInEnd], [0, 1], { extrapolateRight: 'clamp' });
  const push = scene.transition === 'push'
    ? interpolate(frame, [0, 10], [60, 0], { extrapolateRight: 'clamp' })
    : 0;
  const whip = scene.transition === 'whip'
    ? interpolate(frame, [0, 6], [-120, 0], { extrapolateRight: 'clamp' })
    : 0;

  return (
    <AbsoluteFill style={{ opacity: fadeIn, transform: `translateX(${push + whip}px)` }}>
      <SceneVisual scene={scene} input={input} />

      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          paddingTop: SAFE_TOP,
          paddingBottom: SAFE_BOTTOM,
          paddingLeft: 80,
          paddingRight: 80,
        }}
      >
        {scene.isHook ? <HookText input={input} /> : null}

        <div
          style={{
            fontFamily: theme.displayFont,
            fontSize: captionFontSize,
            lineHeight: 1.18,
            fontWeight: 700,
            color: theme.text,
            textAlign: 'center',
            textShadow: '0 6px 30px rgba(0,0,0,0.62)',
          }}
        >
          {scene.captionLines.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>

        {scene.isCta ? (
          <div
            style={{
              marginTop: 48,
              padding: '22px 52px',
              borderRadius: 999,
              backgroundColor: theme.accent,
              color: theme.background,
              fontFamily: theme.displayFont,
              fontSize: 46,
              fontWeight: 700,
            }}
          >
            {input.ctaText}
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const SceneVisual: React.FC<{ scene: RuntimeRenderScene; input: RenderInput }> = ({ scene, input }) => {
  const frame = useCurrentFrame();
  const uri = scene.assetUri ?? null;

  if (!uri || scene.assetMediaKind === 'graphic') {
    return <PlaceholderVisual scene={scene} input={input} />;
  }

  const zoom = interpolate(
    frame,
    [0, Math.max(1, scene.durationFrames - 1)],
    [1.015, scene.assetMediaKind === 'image' ? 1.075 : 1.035],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  return (
    <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: input.theme.background }}>
      {scene.assetMediaKind === 'video' ? (
        <OffthreadVideo
          src={uri}
          volume={input.audio.trackPath ? 0 : 1}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${zoom})`,
          }}
        />
      ) : (
        <Img
          src={uri}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${zoom})`,
          }}
        />
      )}

      {/* Real media still needs a controlled contrast layer so captions and
          disclosures remain legible without flattening the image into a demo UI. */}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(8,5,14,0.28) 0%, rgba(8,5,14,0.06) 32%, rgba(8,5,14,0.18) 58%, rgba(8,5,14,0.58) 100%)',
        }}
      />
    </AbsoluteFill>
  );
};

/**
 * If a provider is unavailable or fails, the scene stays explicitly marked as
 * a placeholder. A reviewer can never confuse a gradient with generated media.
 */
const PlaceholderVisual: React.FC<{ scene: RuntimeRenderScene; input: RenderInput }> = ({ scene, input }) => {
  const { theme } = input;
  const isLesson = theme.signature === 'lesson_stage';
  const tilt = isLesson ? 0 : (scene.index % 2 === 0 ? -8 : 8);

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          background: isLesson
            ? `radial-gradient(circle at 50% 32%, ${theme.backgroundAlt} 0%, ${theme.background} 70%)`
            : `linear-gradient(${140 + tilt}deg, ${theme.background} 0%, ${theme.backgroundAlt} 55%, ${theme.background} 100%)`,
        }}
      />
      {/* Brand signature: a rail of accent bars for Maya, a soft stage for kids. */}
      {isLesson ? (
        <AbsoluteFill style={{ justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 300 }}>
          <div style={{ width: 720, height: 12, borderRadius: 8, backgroundColor: theme.accentSoft, opacity: 0.5 }} />
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{ justifyContent: 'center', paddingLeft: 44 }}>
          <div style={{ width: 10, height: 520, borderRadius: 8, backgroundColor: theme.accent, opacity: 0.75 }} />
        </AbsoluteFill>
      )}

      {scene.assetStatus === 'placeholder' ? (
        <AbsoluteFill style={{ justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 210 }}>
          <div
            style={{
              fontFamily: theme.utilityFont,
              fontSize: 26,
              color: theme.textMuted,
              opacity: 0.85,
              textAlign: 'center',
              maxWidth: 860,
            }}
          >
            [placeholder - {scene.assetType}] {scene.visualDescription}
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

const HookText: React.FC<{ input: RenderInput }> = ({ input }) => (
  <div
    style={{
      marginBottom: 36,
      padding: '14px 32px',
      borderRadius: 18,
      backgroundColor: input.theme.accentSoft,
      color: input.theme.text,
      fontFamily: input.theme.utilityFont,
      fontSize: 34,
      letterSpacing: 1,
      textTransform: 'uppercase',
    }}
  >
    {truncateWords(input.hookText, HOOK_CHIP_MAX_CHARS)}
  </div>
);

/**
 * Disclosure badges. For Maya.exe the "Virtual AI creator" badge is held for
 * the entire duration - it is a persistent disclosure, not a title card that
 * scrolls past before anyone reads it.
 */
const BadgeRail: React.FC<{ input: RenderInput }> = ({ input }) => {
  const { theme, badges } = input;
  const { height } = useVideoConfig();

  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <div style={{ position: 'absolute', top: 96, left: 56, display: 'flex', gap: 14, flexDirection: 'column' }}>
        <span
          style={{
            fontFamily: theme.displayFont,
            fontSize: 34,
            fontWeight: 700,
            color: theme.text,
            backgroundColor: 'rgba(0,0,0,0.35)',
            padding: '10px 22px',
            borderRadius: 999,
            alignSelf: 'flex-start',
          }}
        >
          {badges.brand}
        </span>

        {badges.disclosure ? (
          <span
            style={{
              fontFamily: theme.utilityFont,
              fontSize: 26,
              color: theme.background,
              backgroundColor: theme.accent,
              padding: '9px 20px',
              borderRadius: 999,
              alignSelf: 'flex-start',
            }}
          >
            {badges.disclosure}
          </span>
        ) : null}

        {badges.affiliate ? (
          <span
            style={{
              fontFamily: theme.utilityFont,
              fontSize: 24,
              color: theme.text,
              backgroundColor: 'rgba(0,0,0,0.45)',
              padding: '8px 18px',
              borderRadius: 999,
              alignSelf: 'flex-start',
            }}
          >
            {badges.affiliate}
          </span>
        ) : null}
      </div>

      <div
        style={{
          position: 'absolute',
          top: height - 150,
          width: '100%',
          textAlign: 'center',
          fontFamily: theme.utilityFont,
          fontSize: 22,
          color: theme.textMuted,
          opacity: 0.7,
        }}
      >
        {input.audio.placeholderSilence ? 'audio placeholder - VO not yet recorded' : ''}
      </div>
    </AbsoluteFill>
  );
};