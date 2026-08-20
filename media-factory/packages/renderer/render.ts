import { execFile } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { now, stableId } from '../core/ids.ts';
import { outputDir } from '../core/store.ts';
import type { RenderInput, VideoJob } from '../core/types.ts';
import { thumbnailFrame } from './build-render-input.ts';

const run = promisify(execFile);
const here = dirname(fileURLToPath(import.meta.url));
const WINDOWS = process.platform === 'win32';

/**
 * Render dispatcher.
 *
 * Remotion is the intended renderer. It needs a headless Chromium binary, which
 * has to be downloaded on first use - impossible on an offline or
 * network-restricted machine. Rather than let the vertical slice dead-end
 * there, we fall back to a Pillow + ffmpeg rasteriser that consumes the exact
 * same RenderInput.
 *
 * The backend actually used is recorded on the VideoJob, so nobody reviews a
 * fallback render believing it came from Remotion.
 */

export type RendererChoice = 'auto' | 'remotion' | 'ffmpeg';

export interface RenderResult {
  outputPath: string;
  thumbnailPath: string | null;
  backend: 'remotion' | 'ffmpeg';
  durationSeconds: number;
  warnings: string[];
}

export function renderChoice(): RendererChoice {
  const raw = (process.env.RENDERER ?? 'auto').toLowerCase();
  if (raw === 'remotion' || raw === 'ffmpeg' || raw === 'auto') return raw;
  return 'auto';
}

/**
 * Run the project-local CLI. On Windows `npx` resolves through npx.cmd, which
 * `execFile()` cannot launch without a shell. PowerShell can run the same
 * command successfully, so use the Windows command shell only for this static
 * internal CLI invocation.
 */
async function runNpx(args: string[], options: { timeout: number; maxBuffer?: number } = { timeout: 120_000 }): Promise<void> {
  await run('npx', args, {
    ...options,
    ...(WINDOWS ? { shell: true } : {}),
  });
}

/** Remotion can only render if its browser is already present locally. */
export async function remotionBrowserAvailable(): Promise<boolean> {
  try {
    await runNpx(['remotion', 'browser', 'ensure'], { timeout: 120_000 });
    return true;
  } catch {
    return false;
  }
}

async function renderWithRemotion(input: RenderInput, propsPath: string, outPath: string): Promise<void> {
  const entry = join(here, 'remotion', 'index.ts');
  await runNpx(
    ['remotion', 'render', entry, 'VerticalVideo', outPath, `--props=${propsPath}`, '--log=error'],
    { timeout: 900_000, maxBuffer: 1024 * 1024 * 32 },
  );
}

async function renderWithFallback(
  propsPath: string,
  outPath: string,
  thumbPath: string,
): Promise<void> {
  const script = join(here, 'fallback', 'render_frames.py');
  await run('python3', [script, propsPath, outPath, thumbPath], {
    timeout: 600_000,
    maxBuffer: 1024 * 1024 * 32,
  });
}

export async function renderVideo(
  input: RenderInput,
  options: { choice?: RendererChoice; outDir?: string } = {},
): Promise<RenderResult> {
  const choice = options.choice ?? renderChoice();
  const dir = resolve(options.outDir ?? outputDir(), input.jobId);
  mkdirSync(dir, { recursive: true });

  const propsPath = join(dir, 'render-input.json');
  const outPath = join(dir, `${input.brandId}-${input.jobId}.mp4`);
  const thumbPath = join(dir, 'thumbnail.png');
  const warnings: string[] = [];

  // The props file is the render contract. Written every time, so a failed
  // render can still be reproduced by hand.
  writeFileSync(propsPath, `${JSON.stringify(input, null, 2)}\n`, 'utf8');

  const durationSeconds = Number((input.totalFrames / input.fps).toFixed(2));

  let backend: 'remotion' | 'ffmpeg' = 'ffmpeg';
  if (choice !== 'ffmpeg') {
    const available = await remotionBrowserAvailable();
    if (available) {
      backend = 'remotion';
    } else if (choice === 'remotion') {
      throw new Error(
        'RENDERER=remotion was requested but the Remotion headless browser is unavailable. ' +
          'Run `npm run remotion:ensure-browser` on a machine with network access, or set RENDERER=auto.',
      );
    } else {
      warnings.push(
        'Remotion headless browser unavailable - rendered with the ffmpeg fallback. ' +
          'Run `npm run remotion:ensure-browser` for the production renderer.',
      );
    }
  }

  if (backend === 'remotion') {
    try {
      await renderWithRemotion(input, propsPath, outPath);
    } catch (error) {
      if (choice === 'remotion') throw error;
      warnings.push(`Remotion render failed, fell back to ffmpeg: ${(error as Error).message.slice(0, 200)}`);
      backend = 'ffmpeg';
      await renderWithFallback(propsPath, outPath, thumbPath);
    }
  } else {
    await renderWithFallback(propsPath, outPath, thumbPath);
  }

  return {
    outputPath: outPath,
    thumbnailPath: thumbPath,
    backend,
    durationSeconds,
    warnings,
  };
}

export function newVideoJob(input: RenderInput): VideoJob {
  return {
    id: input.jobId,
    brandId: input.brandId,
    storyboardId: stableId('storyboard_ref', input.jobId),
    status: 'queued',
    backend: null,
    outputPath: null,
    thumbnailPath: null,
    durationSeconds: null,
    error: null,
    createdAt: now(),
  };
}

export { thumbnailFrame };
