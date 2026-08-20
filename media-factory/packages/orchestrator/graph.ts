import { Annotation, END, START, StateGraph } from '@langchain/langgraph';
import { now, stableId } from '../core/ids.ts';
import type { LlmProvider } from '../core/llm/provider.ts';
import type {
  AssetPlan,
  Brand,
  ContentBrief,
  Opportunity,
  Publication,
  QaReport,
  RenderInput,
  ResearchBundle,
  Script,
  Storyboard,
  VideoJob,
} from '../core/types.ts';
import { scout } from '../agents/opportunity-scout.ts';
import { research as gatherResearch } from '../research/research-agent.ts';
import { planContent } from '../agents/content-strategist.ts';
import { writeScript } from '../agents/script-agent.ts';
import { buildStoryboard } from '../agents/storyboard-agent.ts';
import { planAssets, type AssetMode } from '../agents/asset-planner.ts';
import { directAssets } from '../agents/asset-director.ts';
import { runQaAgent } from '../agents/qa-agent.ts';
import { runPublishingPlanner } from '../agents/publishing-planner.ts';
import { buildRenderInput } from '../renderer/build-render-input.ts';
import { renderVideo, type RendererChoice } from '../renderer/render.ts';

/**
 * The orchestrator.
 *
 * Implemented as a LangGraph StateGraph: nodes are agents, the channel reducers
 * define how each agent's output merges into shared state, and the QA gate is a
 * conditional edge. LangGraph runs entirely locally here - it needs no API key,
 * which is what let it stay in the stack.
 *
 * Flow:
 *   scout -> research -> strategist -> script -> storyboard -> assets
 *         -> render -> qa -> [gate] -> publish | halt
 */

const replace = <T,>() => ({ reducer: (_prev: T, next: T) => next, default: () => undefined as unknown as T });
const append = <T,>() => ({ reducer: (prev: T[], next: T[]) => prev.concat(next), default: () => [] as T[] });

export const FactoryState = Annotation.Root({
  brand: Annotation<Brand>(replace<Brand>()),
  topic: Annotation<string>(replace<string>()),
  jobId: Annotation<string>(replace<string>()),
  rendererChoice: Annotation<RendererChoice>(replace<RendererChoice>()),
  assetMode: Annotation<AssetMode>({ reducer: (_p, n) => n, default: () => 'synthetic' as AssetMode }),
  skipRender: Annotation<boolean>({ reducer: (_p, n) => n, default: () => false }),

  opportunity: Annotation<Opportunity | null>({ reducer: (_p, n) => n, default: () => null }),
  research: Annotation<ResearchBundle | null>({ reducer: (_p, n) => n, default: () => null }),
  brief: Annotation<ContentBrief | null>({ reducer: (_p, n) => n, default: () => null }),
  script: Annotation<Script | null>({ reducer: (_p, n) => n, default: () => null }),
  storyboard: Annotation<Storyboard | null>({ reducer: (_p, n) => n, default: () => null }),
  assetPlan: Annotation<AssetPlan | null>({ reducer: (_p, n) => n, default: () => null }),
  renderInput: Annotation<RenderInput | null>({ reducer: (_p, n) => n, default: () => null }),
  videoJob: Annotation<VideoJob | null>({ reducer: (_p, n) => n, default: () => null }),
  qa: Annotation<QaReport | null>({ reducer: (_p, n) => n, default: () => null }),
  publication: Annotation<Publication | null>({ reducer: (_p, n) => n, default: () => null }),

  /** Every node appends its name, giving a verifiable execution trace. */
  steps: Annotation<string[]>(append<string>()),
  warnings: Annotation<string[]>(append<string>()),
});

export type FactoryStateType = typeof FactoryState.State;

export interface BuildGraphOptions {
  provider: LlmProvider;
  brandsDirectory?: string;
  outDir?: string;
}

export function buildFactoryGraph(options: BuildGraphOptions) {
  const { provider } = options;

  const graph = new StateGraph(FactoryState)
    /* -- scout: attach evidence for the topic, if any exists --------------- */
    .addNode('scout', async (state) => {
      const result = scout({ brand: state.brand, topic: state.topic, dir: options.brandsDirectory });
      const warnings = [...result.warnings];
      if (result.opportunities.length === 0) {
        warnings.push(
          `no recorded signal matches "${state.topic}" - proceeding on operator instruction with no opportunity evidence attached.`,
        );
        if (result.notice) warnings.push(result.notice);
      }
      return { steps: ['scout'], opportunity: result.opportunities[0] ?? null, warnings };
    })

    /* -- research: verified facts vs assumptions --------------------------- */
    .addNode('research_agent', async (state) => {
      const bundle = gatherResearch({
        brandId: state.brand.id,
        topic: state.topic,
        dir: options.brandsDirectory,
        // The opportunity's own source travels with the bundle so the evidence
        // trail is unbroken from signal to script.
        extraSources: state.opportunity?.evidence ?? [],
      });
      return { steps: ['research_agent'], research: bundle, warnings: bundle.gaps };
    })

    /* -- strategist -------------------------------------------------------- */
    .addNode('strategist', async (state) => {
      const brief = await planContent({
        brand: state.brand,
        topic: state.topic,
        facts: state.research!.facts,
        provider,
        // Default is synthetic: nothing filmed, worn, bought or tested. That
        // can only make the copy more cautious, never less.
        syntheticAssets: state.assetMode === 'synthetic',
      });
      return { steps: ['strategist'], brief };
    })

    .addNode('script_agent', async (state) => {
      const script = await writeScript({
        brand: state.brand,
        brief: state.brief!,
        facts: state.research!.facts,
        provider,
        allSynthetic: state.assetMode === 'synthetic',
      });
      return { steps: ['script_agent'], script };
    })

    .addNode('storyboard_agent', async (state) => {
      const storyboard = await buildStoryboard({ brand: state.brand, script: state.script!, provider });
      return { steps: ['storyboard_agent'], storyboard };
    })

    .addNode('assets', async (state) => {
      const plannedAssets = planAssets({ storyboard: state.storyboard!, mode: state.assetMode });
      const directed = await directAssets({
        brand: state.brand,
        storyboard: state.storyboard!,
        assetPlan: plannedAssets,
        brandsDirectory: options.brandsDirectory,
      });
      const assetPlan = directed.assetPlan;
      const renderInput = buildRenderInput({
        jobId: state.jobId,
        brand: state.brand,
        brief: state.brief!,
        script: state.script!,
        storyboard: state.storyboard!,
        assetPlan,
      });
      return { steps: ['assets'], assetPlan, renderInput, warnings: directed.warnings };
    })

    /* -- render ------------------------------------------------------------ */
    .addNode('render', async (state) => {
      if (state.skipRender) {
        return {
          steps: ['render:skipped'],
          videoJob: {
            id: state.jobId,
            brandId: state.brand.id,
            storyboardId: state.storyboard!.id,
            status: 'queued' as const,
            backend: null,
            outputPath: null,
            thumbnailPath: null,
            durationSeconds: state.renderInput!.totalFrames / state.renderInput!.fps,
            error: null,
            createdAt: now(),
          },
        };
      }

      try {
        const result = await renderVideo(state.renderInput!, {
          choice: state.rendererChoice,
          outDir: options.outDir,
        });
        return {
          steps: ['render'],
          warnings: result.warnings,
          videoJob: {
            id: state.jobId,
            brandId: state.brand.id,
            storyboardId: state.storyboard!.id,
            status: 'rendered' as const,
            backend: result.backend,
            outputPath: result.outputPath,
            thumbnailPath: result.thumbnailPath,
            durationSeconds: result.durationSeconds,
            error: null,
            createdAt: now(),
          },
        };
      } catch (error) {
        // A failed render must not abort QA: the package is still worth
        // inspecting, and QA findings explain more than a stack trace.
        return {
          steps: ['render:failed'],
          warnings: [`render failed: ${(error as Error).message}`],
          videoJob: {
            id: state.jobId,
            brandId: state.brand.id,
            storyboardId: state.storyboard!.id,
            status: 'failed' as const,
            backend: null,
            outputPath: null,
            thumbnailPath: null,
            durationSeconds: null,
            error: (error as Error).message,
            createdAt: now(),
          },
        };
      }
    })

    /* -- qa ---------------------------------------------------------------- */
    .addNode('qa_agent', async (state) => {
      const qa = runQaAgent({
        brand: state.brand,
        brief: state.brief!,
        script: state.script!,
        storyboard: state.storyboard!,
        assetPlan: state.assetPlan!,
        research: state.research!,
        jobId: state.jobId,
      });
      return { steps: ['qa_agent'], qa };
    })

    /* -- publish ----------------------------------------------------------- */
    .addNode('publish', async (state) => {
      const publication = runPublishingPlanner({
        brand: state.brand,
        brief: state.brief!,
        script: state.script!,
        renderInput: state.renderInput!,
        qa: state.qa!,
        videoPath: state.videoJob?.outputPath ?? '(not rendered)',
        thumbnailPath: state.videoJob?.thumbnailPath ?? null,
      });
      return { steps: ['publish'], publication };
    })

    /* -- halt: QA failed, no publish manifest is produced ------------------ */
    .addNode('halt', async (state) => ({
      steps: ['halt'],
      warnings: [
        `QA failed with ${state.qa?.findings.filter((f) => f.severity === 'error').length ?? 0} errors - no publish manifest was generated.`,
      ],
    }));

  graph
    .addEdge(START, 'scout')
    .addEdge('scout', 'research_agent')
    .addEdge('research_agent', 'strategist')
    .addEdge('strategist', 'script_agent')
    .addEdge('script_agent', 'storyboard_agent')
    .addEdge('storyboard_agent', 'assets')
    .addEdge('assets', 'render')
    .addEdge('render', 'qa_agent')
    // The gate: only a QA-passing package reaches the publishing planner.
    .addConditionalEdges('qa_agent', (state: FactoryStateType) => (state.qa?.passed ? 'publish' : 'halt'), {
      publish: 'publish',
      halt: 'halt',
    })
    .addEdge('publish', END)
    .addEdge('halt', END);

  return graph.compile();
}

export interface RunPipelineArgs {
  provider: LlmProvider;
  brand: Brand;
  topic: string;
  rendererChoice?: RendererChoice;
  assetMode?: AssetMode;
  skipRender?: boolean;
  brandsDirectory?: string;
  outDir?: string;
  jobId?: string;
}

export async function runPipeline(args: RunPipelineArgs): Promise<FactoryStateType> {
  const graph = buildFactoryGraph({
    provider: args.provider,
    brandsDirectory: args.brandsDirectory,
    outDir: args.outDir,
  });

  return (await graph.invoke({
    brand: args.brand,
    topic: args.topic,
    jobId: args.jobId ?? stableId('job', args.brand.id, args.topic),
    rendererChoice: args.rendererChoice ?? 'auto',
    assetMode: args.assetMode ?? 'synthetic',
    skipRender: args.skipRender ?? false,
  })) as FactoryStateType;
}