import React from 'react';
import { Composition } from 'remotion';
import { RenderInputSchema, type RenderInput } from '../../core/types.ts';
import { VerticalVideo } from './VerticalVideo.tsx';
import { FALLBACK_INPUT } from './default-input.ts';

/**
 * One composition serves every brand. The pipeline passes a validated
 * RenderInput through --props, so the studio and the CLI render identical output.
 */
export const RemotionRoot: React.FC = () => (
  <Composition
    id="VerticalVideo"
    component={VerticalVideo as React.FC<Record<string, unknown>>}
    durationInFrames={FALLBACK_INPUT.totalFrames}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ input: FALLBACK_INPUT } as unknown as Record<string, unknown>}
    calculateMetadata={({ props }) => {
      const input = RenderInputSchema.parse((props as { input: RenderInput }).input);
      return { durationInFrames: input.totalFrames, fps: input.fps, width: input.width, height: input.height };
    }}
  />
);
