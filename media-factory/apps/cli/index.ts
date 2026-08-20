#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { listBrandIds, loadBrand } from '../../packages/core/brand.ts';
import { createProvider } from '../../packages/core/llm/index.ts';
import { defaultStore, outputDir } from '../../packages/core/store.ts';
import { stableId } from '../../packages/core/ids.ts';
import { scout } from '../../packages/agents/opportunity-scout.ts';
import { runQaAgent, summariseQa } from '../../packages/agents/qa-agent.ts';
import { runPipeline } from '../../packages/orchestrator/graph.ts';
import { renderVideo } from '../../packages/renderer/render.ts';
import { ingestAnalytics, runGrowthOptimizer } from '../../packages/analytics/analytics-agent.ts';
import { RenderInputSchema } from '../../packages/core/types.ts';
import type { RendererChoice } from '../../packages/renderer/render.ts';

/* -------------------------------------------------------------------------- */
/* helpers                                                                     */
/* -------------------------------------------------------------------------- */

const c = {
  dim: (s: string) => `\x1b[2m${s}\x1b[0m`,
  bold: (s: string) => `\x1b[1m${s}\x1b[0m`,
  green: (s: string) => `\x1b[32m${s}\x1b[0m`,
  red: (s: string) => `\x1b[31m${s}\x1b[0m`,
  yellow: (s: string) => `\x1b[33m${s}\x1b[0m`,
  cyan: (s: string) => `\x1b[36m${s}\x1b[0m`,
};

function heading(text: string): void {
  console.log(`\n${c.bold(text)}\n${c.dim('─'.repeat(Math.min(72, text.length + 12)))}`);
}

function usage(): void {
  console.log(`
${c.bold('media-factory')} - multi-brand short-form video pipeline

${c.bold('Usage')}
  npm run factory -- <command> [options]

${c.bold('Commands')}
  brands                          list configured brands
  scout    --brand <id> [--niche <n>] [--limit <n>]
                                  rank recorded opportunity signals
  create   --brand <id> --topic "<topic>"
                                  brief -> script -> storyboard -> assets, no render
  pipeline --brand <id> --topic "<topic>" [--renderer auto|remotion|ffmpeg]
                                  the full run, including render, QA and publish manifest
  render   <job-id>               re-render an existing job from its saved props
  qa       <job-id>               re-run QA against a stored job
  analytics ingest --file <path>  load a JSON array of analytics rows
  optimize --brand <id>           apply the 25/50/25 growth policy

${c.bold('Notes')}
  Runs offline on the deterministic mock provider by default.
  Set LLM_PROVIDER=anthropic|openai|ollama in .env to use a real model.
`);
}

function requireOption(value: string | undefined, name: string): string {
  if (!value) {
    console.error(c.red(`error: --${name} is required`));
    process.exit(1);
  }
  return value;
}

function jobDir(jobId: string): string {
  return join(outputDir(), jobId);
}

/* -------------------------------------------------------------------------- */
/* commands                                                                    */
/* -------------------------------------------------------------------------- */

function cmdBrands(): void {
  heading('Configured brands');
  const ids = listBrandIds();
  if (ids.length === 0) {
    console.log(c.yellow('no brands found in ./brands'));
    return;
  }
  for (const id of ids) {
    const brand = loadBrand(id);
    console.log(`${c.cyan(id.padEnd(16))} ${brand.name}`);
    console.log(`${' '.repeat(16)} ${c.dim(brand.niche)}`);
    console.log(`${' '.repeat(16)} ${c.dim(`platforms: ${brand.platforms.join(', ')}`)}`);
    const flags = [
      brand.rules.requireAiDisclosure ? `AI disclosure: "${brand.rules.aiDisclosureText}"` : null,
      brand.rules.childDirected ? 'child-directed' : null,
    ].filter(Boolean);
    if (flags.length) console.log(`${' '.repeat(16)} ${c.dim(flags.join(' · '))}`);
  }
}

function cmdScout(values: Record<string, string | boolean | undefined>): void {
  const brand = loadBrand(requireOption(values.brand as string, 'brand'));
  const result = scout({
    brand,
    niche: values.niche as string | undefined,
    limit: values.limit ? Number(values.limit) : undefined,
  });

  heading(`Opportunities for ${brand.name}`);
  if (result.opportunities.length === 0) {
    console.log(c.yellow('none'));
  }
  for (const opportunity of result.opportunities) {
    const s = opportunity.score;
    console.log(`${c.bold(String(s.total).padStart(5))}  ${opportunity.topic}`);
    console.log(
      c.dim(
        `        attention ${s.attention} · growth ${s.growth} · intent ${s.commercialIntent} · ` +
          `monetization ${s.monetizationPotential} · repeatable ${s.contentRepeatability} · product ${s.productOpportunity}`,
      ),
    );
    console.log(c.dim(`        penalties: saturation -${s.saturationPenalty} · risk -${s.riskPenalty}`));
    for (const source of opportunity.evidence) {
      console.log(c.dim(`        source: ${source.url}`));
    }
  }

  const store = defaultStore();
  for (const opportunity of result.opportunities) store.write('opportunities', opportunity.id, opportunity);

  for (const rejection of result.rejected) {
    console.log(c.dim(`        skipped ${rejection.id}: ${rejection.reason}`));
  }
  if (result.notice) console.log(c.yellow(`\n${result.notice}`));

  if (result.warnings.length) {
    heading('Warnings');
    for (const warning of result.warnings) console.log(c.yellow(`! ${warning}`));
  }
  if (result.placeholderEvidenceOnly) {
    console.log(
      c.red('\nEvery signal is still repository template data. These rankings are not based on observed trends.'),
    );
  }
}

async function cmdPipeline(
  values: Record<string, string | boolean | undefined>,
  opts: { skipRender: boolean },
): Promise<void> {
  const brand = loadBrand(requireOption(values.brand as string, 'brand'));
  const topic = requireOption(values.topic as string, 'topic');
  const provider = createProvider();
  const store = defaultStore();

  heading(`${opts.skipRender ? 'Create' : 'Pipeline'}: ${brand.name}`);
  console.log(`${c.dim('topic')}    ${topic}`);
  console.log(`${c.dim('provider')} ${provider.name}`);

  const state = await runPipeline({
    provider,
    brand,
    topic,
    skipRender: opts.skipRender,
    rendererChoice: (values.renderer as RendererChoice | undefined) ?? 'auto',
  });

  console.log(`${c.dim('job')}      ${state.jobId}`);
  console.log(`${c.dim('steps')}    ${state.steps.join(' -> ')}`);

  if (state.brief) store.write('briefs', state.brief.id, state.brief);
  if (state.script) store.write('scripts', state.script.id, state.script);
  if (state.storyboard) store.write('storyboards', state.storyboard.id, state.storyboard);
  if (state.assetPlan) store.write('assetPlans', state.assetPlan.id, state.assetPlan);
  if (state.videoJob) store.write('videoJobs', state.videoJob.id, state.videoJob);
  if (state.qa) store.write('qaReports', state.qa.id, state.qa);
  if (state.publication) store.write('publications', state.publication.id, state.publication);
  if (state.research) store.write('research', state.research.id, state.research);

  if (state.script) {
    heading('Script');
    for (const line of state.script.lines) {
      console.log(`${c.cyan(`${line.sceneNumber}.`)} ${line.voiceover}`);
      console.log(c.dim(`   on-screen: ${line.onScreenText}  (${line.durationSeconds}s)`));
    }
    console.log(c.dim(`\n   total ${state.script.totalDurationSeconds}s · disclosures: ${state.script.disclosures.join(', ') || 'none'}`));
  }

  if (state.assetPlan) {
    heading('Asset plan');
    for (const asset of state.assetPlan.assets) {
      const tag = asset.synthetic ? c.dim('synthetic') : c.yellow('needs real capture');
      console.log(`${c.cyan(`${asset.sceneNumber}.`)} ${asset.type.padEnd(17)} ${tag}`);
    }
  }

  if (state.videoJob) {
    heading('Render');
    console.log(`status   ${state.videoJob.status === 'rendered' ? c.green(state.videoJob.status) : c.yellow(state.videoJob.status)}`);
    if (state.videoJob.backend) console.log(`backend  ${state.videoJob.backend}`);
    if (state.videoJob.outputPath) console.log(`output   ${state.videoJob.outputPath}`);
    if (state.videoJob.error) console.log(c.red(`error    ${state.videoJob.error}`));
  }

  if (state.qa) {
    heading('QA');
    console.log(state.qa.passed ? c.green(summariseQa(state.qa)) : c.red(summariseQa(state.qa)));
    for (const finding of state.qa.findings) {
      const label = finding.severity === 'error' ? c.red('ERROR') : c.yellow('WARN ');
      const scene = finding.sceneNumber ? `scene ${finding.sceneNumber}: ` : '';
      console.log(`  ${label} ${c.dim(finding.rule)} ${scene}${finding.message}`);
    }
  }

  if (state.publication) {
    heading('Publish manifest');
    const dir = jobDir(state.jobId);
    mkdirSync(dir, { recursive: true });
    const path = join(dir, 'publication.json');
    writeFileSync(path, `${JSON.stringify(state.publication, null, 2)}\n`, 'utf8');
    for (const manifest of state.publication.manifests) {
      console.log(`${c.cyan(manifest.platform)} ${c.dim(`(${manifest.publishMethod})`)}`);
      console.log(c.dim(`  hashtags: ${manifest.hashtags.join(' ')}`));
      for (const note of manifest.notes) console.log(c.dim(`  - ${note}`));
    }
    console.log(`\nwritten ${path}`);
  }

  if (state.warnings.length) {
    heading('Warnings');
    for (const warning of state.warnings) console.log(c.yellow(`! ${warning}`));
  }
}

async function cmdRender(jobId: string): Promise<void> {
  const propsPath = join(jobDir(jobId), 'render-input.json');
  const input = RenderInputSchema.parse(JSON.parse(readFileSync(propsPath, 'utf8')));
  heading(`Render ${jobId}`);
  const result = await renderVideo(input);
  console.log(`backend  ${result.backend}`);
  console.log(`output   ${result.outputPath}`);
  for (const warning of result.warnings) console.log(c.yellow(`! ${warning}`));
}

function cmdQa(jobId: string): void {
  const store = defaultStore();
  const job = store.read<{ brandId: string; storyboardId: string }>('videoJobs', jobId);
  if (!job) {
    console.error(c.red(`no stored job "${jobId}". Run the pipeline first.`));
    process.exit(1);
  }
  const brand = loadBrand(job.brandId);
  const storyboard = store.list<{ id: string; scriptId: string; brandId: string }>('storyboards').find((s) => s.brandId === brand.id);
  const script = store.list<{ id: string; briefId: string }>('scripts').find((s) => s.id === storyboard?.scriptId);
  const brief = store.list<{ id: string }>('briefs').find((b) => b.id === script?.briefId);
  const assetPlan = store.list<{ storyboardId: string }>('assetPlans').find((a) => a.storyboardId === storyboard?.id);
  const research = store.list<{ id: string }>('research')[0];

  if (!storyboard || !script || !brief || !assetPlan || !research) {
    console.error(c.red('stored artifacts for this job are incomplete. Re-run the pipeline.'));
    process.exit(1);
  }

  const report = runQaAgent({
    brand,
    brief: brief as never,
    script: script as never,
    storyboard: storyboard as never,
    assetPlan: assetPlan as never,
    research: research as never,
    jobId,
  });

  heading(`QA ${jobId}`);
  console.log(report.passed ? c.green(summariseQa(report)) : c.red(summariseQa(report)));
  for (const finding of report.findings) {
    const label = finding.severity === 'error' ? c.red('ERROR') : c.yellow('WARN ');
    console.log(`  ${label} ${c.dim(finding.rule)} ${finding.message}`);
  }
  defaultStore().write('qaReports', report.id, report);
}

function cmdAnalyticsIngest(file: string): void {
  const rows = JSON.parse(readFileSync(file, 'utf8'));
  const records = ingestAnalytics(rows);
  const store = defaultStore();
  for (const record of records) store.write('analytics', record.id, record);
  heading('Analytics ingested');
  for (const record of records) {
    console.log(
      `${c.cyan(record.videoId.padEnd(18))} views ${String(record.views).padStart(8)} · completion ${(record.completionRate * 100).toFixed(1)}% · rev/1k ${record.revenuePer1000Views}`,
    );
  }
}

function cmdOptimize(brandId: string): void {
  const store = defaultStore();
  const records = store.list<never>('analytics');
  const plan = runGrowthOptimizer(brandId, records);

  heading(`Growth plan: ${brandId}`);
  for (const note of plan.notes) console.log(c.dim(note));

  const show = (label: string, items: { videoId: string; topic: string }[], colour: (s: string) => string) => {
    if (!items.length) return;
    console.log(`\n${colour(label)}`);
    for (const item of items) console.log(`  ${item.videoId}  ${c.dim(item.topic)}`);
  };
  show('SCALE (top 25% - 3 variations each)', plan.scale, c.green);
  show('ITERATE (middle 50% - keep testing)', plan.iterate, c.cyan);
  show('PAUSE (bottom 25%)', plan.pause, c.yellow);

  for (const experiment of plan.experiments) store.write('experiments', experiment.id, experiment);
  if (plan.experiments.length) console.log(c.dim(`\n${plan.experiments.length} experiments written to data/experiments`));
}

/* -------------------------------------------------------------------------- */
/* entry                                                                       */
/* -------------------------------------------------------------------------- */

async function main(): Promise<void> {
  const argv = process.argv.slice(2);
  const command = argv[0];
  const sub = argv[1];

  if (!command || command === 'help' || command === '--help') {
    usage();
    return;
  }

  const { values, positionals } = parseArgs({
    args: argv.slice(1),
    options: {
      brand: { type: 'string' },
      topic: { type: 'string' },
      niche: { type: 'string' },
      limit: { type: 'string' },
      renderer: { type: 'string' },
      file: { type: 'string' },
    },
    allowPositionals: true,
    strict: false,
  });

  switch (command) {
    case 'brands':
      return cmdBrands();
    case 'scout':
      return cmdScout(values);
    case 'create':
      return cmdPipeline(values, { skipRender: true });
    case 'pipeline':
      return cmdPipeline(values, { skipRender: false });
    case 'render':
      return cmdRender(requireOption(positionals[0], 'job-id'));
    case 'qa':
      return cmdQa(requireOption(positionals[0], 'job-id'));
    case 'analytics':
      if (sub !== 'ingest') {
        console.error(c.red('usage: analytics ingest --file <path>'));
        process.exit(1);
      }
      return cmdAnalyticsIngest(requireOption(values.file as string, 'file'));
    case 'optimize':
      return cmdOptimize(requireOption(values.brand as string, 'brand'));
    default:
      console.error(c.red(`unknown command "${command}"`));
      usage();
      process.exit(1);
  }
}

main().catch((error) => {
  console.error(c.red(`\n${error instanceof Error ? error.stack ?? error.message : String(error)}`));
  process.exit(1);
});
