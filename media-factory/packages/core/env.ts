import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Minimal .env loader for the CLI/runtime. We intentionally avoid another
 * dependency for a file format this small. Existing shell environment values
 * always win, so CI/secret-manager configuration is never overwritten by .env.
 */
export function loadLocalEnv(path = '.env'): void {
  const file = resolve(path);
  if (!existsSync(file)) return;

  const source = readFileSync(file, 'utf8');
  for (const rawLine of source.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;

    const normalized = line.startsWith('export ') ? line.slice(7).trim() : line;
    const equals = normalized.indexOf('=');
    if (equals <= 0) continue;

    const key = normalized.slice(0, equals).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue;
    if (process.env[key] !== undefined) continue;

    process.env[key] = unquote(normalized.slice(equals + 1).trim());
  }
}

function unquote(value: string): string {
  if (value.length >= 2) {
    const first = value[0];
    const last = value[value.length - 1];
    if ((first === '"' && last === '"') || (first === "'" && last === "'")) {
      const inner = value.slice(1, -1);
      return first === '"'
        ? inner.replace(/\\n/g, '\n').replace(/\\r/g, '\r').replace(/\\t/g, '\t').replace(/\\"/g, '"')
        : inner;
    }
  }
  return value;
}
