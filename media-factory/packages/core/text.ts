/** Caption layout maths shared by the renderer and the QA agent. */

export function wrapText(text: string, maxCharsPerLine: number): string[] {
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return [''];
  const lines: string[] = [];
  let current = '';
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxCharsPerLine) {
      current = candidate;
    } else {
      if (current) lines.push(current);
      // A single word longer than the limit is hard-split rather than silently
      // overflowing the safe area.
      if (word.length > maxCharsPerLine) {
        let rest = word;
        while (rest.length > maxCharsPerLine) {
          lines.push(rest.slice(0, maxCharsPerLine));
          rest = rest.slice(maxCharsPerLine);
        }
        current = rest;
      } else {
        current = word;
      }
    }
  }
  if (current) lines.push(current);
  return lines;
}

/** Words per second a listener comfortably follows in short-form voiceover. */
export const SPEAKING_RATE_WPS = 2.6;

export function estimateSpokenSeconds(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(0.8, Number((words / SPEAKING_RATE_WPS).toFixed(2)));
}

export function escapeXml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

export function titleCase(value: string): string {
  return value.replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1));
}

/**
 * Truncates on a word boundary with an ellipsis. Slicing at a raw character
 * index cuts words in half ("...makeup look. H"), which looks like a bug on
 * screen. Used for the hook chip, which has a fixed width budget.
 */
export function truncateWords(text: string, maxChars: number): string {
  const trimmed = text.trim();
  if (trimmed.length <= maxChars) return trimmed;
  const words = trimmed.split(/\s+/);
  let out = '';
  for (const word of words) {
    const candidate = out ? `${out} ${word}` : word;
    if (candidate.length > maxChars - 1) break;
    out = candidate;
  }
  if (!out) out = trimmed.slice(0, Math.max(1, maxChars - 1));
  return `${out.replace(/[.,;:]$/, '')}…`;
}

/** Character budget for the hook chip at its rendered font size. */
export const HOOK_CHIP_MAX_CHARS = 38;
