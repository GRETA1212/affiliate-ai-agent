import { mkdirSync, readFileSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';

/**
 * Deliberately boring JSON store. SQLite is a drop-in later (same interface),
 * but a file store keeps the vertical slice free of native build steps and
 * makes every artifact diffable in review.
 */
export class JsonStore {
  constructor(private readonly root: string) {
    mkdirSync(this.root, { recursive: true });
  }

  private path(collection: string, id: string): string {
    return join(this.root, collection, `${id}.json`);
  }

  write<T>(collection: string, id: string, value: T): T {
    const file = this.path(collection, id);
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
    return value;
  }

  read<T>(collection: string, id: string): T | null {
    const file = this.path(collection, id);
    if (!existsSync(file)) return null;
    return JSON.parse(readFileSync(file, 'utf8')) as T;
  }

  list<T>(collection: string): T[] {
    const dir = join(this.root, collection);
    if (!existsSync(dir)) return [];
    return readdirSync(dir)
      .filter((f) => f.endsWith('.json'))
      .sort()
      .map((f) => JSON.parse(readFileSync(join(dir, f), 'utf8')) as T);
  }
}

export function dataDir(): string {
  return resolve(process.env.FACTORY_DATA_DIR ?? './data');
}

export function outputDir(): string {
  return resolve(process.env.FACTORY_OUTPUT_DIR ?? './output');
}

export function defaultStore(): JsonStore {
  return new JsonStore(dataDir());
}
