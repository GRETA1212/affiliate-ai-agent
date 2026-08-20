import type { RenderInput } from '../../core/types.ts';

/**
 * Studio-only placeholder so `npm run remotion:studio` opens without a pipeline
 * run. Real renders always pass --props.
 */
export const FALLBACK_INPUT: RenderInput = {
  jobId: 'studio_preview',
  brandId: 'maya',
  brandName: 'Maya.exe',
  title: 'Studio preview',
  width: 1080,
  height: 1920,
  fps: 30,
  totalFrames: 150,
  hookText: 'Studio preview',
  ctaText: 'Run the pipeline to render real props',
  badges: { brand: 'Maya.exe', disclosure: 'Virtual AI creator', affiliate: null },
  theme: {
    background: '#0B0710',
    backgroundAlt: '#171021',
    accent: '#FF4D8D',
    accentSoft: '#7B5CFF',
    text: '#FDF7FF',
    textMuted: '#B9A8C9',
    displayFont: 'DejaVuSans-Bold',
    bodyFont: 'DejaVuSans',
    utilityFont: 'DejaVuSansMono',
    signature: 'render_rail',
  },
  scenes: [
    {
      index: 0,
      sceneNumber: 1,
      durationSeconds: 5,
      durationFrames: 150,
      onScreenText: 'Studio Preview',
      captionLines: ['Studio Preview'],
      visualDescription: 'Placeholder frame',
      assetType: 'text_graphic',
      assetStatus: 'placeholder',
      transition: 'cut',
      isHook: true,
      isCta: true,
    },
  ],
  audio: { trackPath: null, placeholderSilence: true },
};
