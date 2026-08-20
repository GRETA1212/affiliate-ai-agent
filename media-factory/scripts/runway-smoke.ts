import { loadLocalEnv } from '../packages/core/env.ts';

loadLocalEnv();

const apiKey = process.env.RUNWAYML_API_SECRET?.trim();
if (!apiKey) {
  throw new Error('RUNWAYML_API_SECRET is missing from .env');
}

const promptText = [
  'Vertical smartphone beauty creator photo at a vanity in a real home.',
  'Natural skin texture, realistic hair flyaways, soft window light mixed with warm room light.',
  'Casual creator framing, believable phone-camera exposure, no text, no logos.',
].join(' ');

const createResponse = await fetch('https://api.dev.runwayml.com/v1/text_to_image', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
    'X-Runway-Version': '2024-11-06',
  },
  body: JSON.stringify({
    model: 'gen4_image',
    promptText,
    ratio: '720:1280',
  }),
});

const createText = await createResponse.text();
if (!createResponse.ok) {
  throw new Error(`Runway create failed ${createResponse.status}: ${createText}`);
}

const create = JSON.parse(createText) as { id?: string };
if (!create.id) throw new Error(`Runway create response had no task id: ${createText}`);

console.log(`RUNWAY_TASK ${create.id}`);

for (let attempt = 0; attempt < 60; attempt += 1) {
  const response = await fetch(`https://api.dev.runwayml.com/v1/tasks/${create.id}`, {
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'X-Runway-Version': '2024-11-06',
    },
  });

  const text = await response.text();
  if (!response.ok) {
    throw new Error(`Runway task read failed ${response.status}: ${text}`);
  }

  const task = JSON.parse(text) as {
    status?: string;
    output?: string[];
    failure?: string;
    failureCode?: string;
  };

  if (task.status === 'SUCCEEDED') {
    const uri = task.output?.find((item) => typeof item === 'string');
    console.log('RUNWAY_SMOKE PASS');
    if (uri) console.log(`OUTPUT ${uri}`);
    process.exit(0);
  }

  if (task.status === 'FAILED' || task.status === 'CANCELLED') {
    throw new Error(`Runway task ${task.status}: ${text}`);
  }

  if (attempt < 59) await new Promise((resolve) => setTimeout(resolve, 2_500));
}

throw new Error('Runway smoke task did not complete before timeout');
