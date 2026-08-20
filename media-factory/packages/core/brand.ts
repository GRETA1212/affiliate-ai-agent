import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { BrandSchema, type Brand } from './types.ts';

export function brandsDir(): string {
  return resolve(process.env.FACTORY_BRANDS_DIR ?? './brands');
}

export function loadBrand(id: string, dir = brandsDir()): Brand {
  const file = join(dir, id, 'brand.json');
  if (!existsSync(file)) {
    const available = listBrandIds(dir).join(', ') || '(none)';
    throw new Error(`unknown brand "${id}". Available brands: ${available}`);
  }
  const parsed = BrandSchema.safeParse(JSON.parse(readFileSync(file, 'utf8')));
  if (!parsed.success) {
    throw new Error(`brand "${id}" is invalid: ${parsed.error.message}`);
  }
  return parsed.data;
}

export function listBrandIds(dir = brandsDir()): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && existsSync(join(dir, e.name, 'brand.json')))
    .map((e) => e.name)
    .sort();
}
