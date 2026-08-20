/**
 * Claim detection.
 *
 * The rule this package exists to enforce: a video may only state something as
 * fact when a captured source backs it. Everything else must be phrased as an
 * observation. These detectors are intentionally noisy - a false positive costs
 * a rewrite, a false negative costs a takedown or an FTC problem.
 */

export type ClaimKind =
  | 'price'
  | 'discount'
  | 'statistic'
  | 'superlative'
  | 'physical_testing'
  | 'health'
  | 'banned_phrase';

export interface ClaimHit {
  kind: ClaimKind;
  text: string;
  /** The exact substring that tripped the detector, for the QA report. */
  match: string;
}

/** Currency amounts: $12, £9.99, 20 usd, 15 dollars. */
const PRICE_PATTERNS: RegExp[] = [
  /[$£€]\s?\d[\d,]*(?:\.\d{1,2})?/gi,
  /\b\d[\d,]*(?:\.\d{1,2})?\s?(?:usd|eur|gbp|dollars?|pounds?|euros?)\b/gi,
  /\b(?:costs?|priced at|only|just)\s+[$£€]\s?\d/gi,
];

/** Discounts and urgency: 20% off, half price, use code, sale ends. */
const DISCOUNT_PATTERNS: RegExp[] = [
  /\b\d{1,3}\s?%\s?off\b/gi,
  /\b(?:half|hälfte)\s+price\b/gi,
  /\bdiscount(?:ed)?\b/gi,
  /\buse\s+(?:my\s+)?code\b/gi,
  /\b(?:sale|deal|offer)\s+(?:ends|expires)\b/gi,
  /\blimited\s+time\b/gi,
  /\bcheapest\b/gi,
];

/** Statistics: any percentage, "x out of y", "studies show", "N times more". */
const STATISTIC_PATTERNS: RegExp[] = [
  /\b\d{1,3}(?:\.\d+)?\s?%/g,
  /\b\d+\s+out\s+of\s+\d+\b/gi,
  /\b(?:studies|research|science)\s+(?:show|shows|prove|proves|suggest)\b/gi,
  /\b\d+(?:\.\d+)?\s?x\s+(?:more|better|faster|longer)\b/gi,
  /\bclinically\s+(?:proven|tested)\b/gi,
  /\b\d+\s+(?:million|billion|thousand)\s+(?:people|users|views|customers)\b/gi,
];

/** Absolutes that cannot be substantiated. */
const SUPERLATIVE_PATTERNS: RegExp[] = [
  /\b(?:the\s+)?best\b/gi,
  /\b(?:the\s+)?worst\b/gi,
  /\bnumber\s+one\b/gi,
  /#1\b/g,
  /\bguarantee(?:d|s)?\b/gi,
  /\bperfect\s+(?:match|result|every\s+time)\b/gi,
  /\bnever\s+fails\b/gi,
  /\bworks\s+for\s+everyone\b/gi,
];

/**
 * First-person physical experience. A virtual creator with only synthetic
 * assets cannot have applied, worn, bought or tested anything.
 */
const PHYSICAL_TESTING_PATTERNS: RegExp[] = [
  /\bI\s+(?:tried|tested|used|wore|applied|bought|purchased|swatched)\b/gi,
  /\bI(?:'ve| have)\s+been\s+using\b/gi,
  /\bon\s+my\s+(?:own\s+)?(?:skin|face|lips|hair)\b/gi,
  /\bafter\s+(?:a\s+)?(?:week|month|30\s+days)\s+of\s+(?:using|wearing)\b/gi,
  /\bmy\s+results\b/gi,
];

/** Health/medical territory that needs qualified review, not a script agent. */
const HEALTH_PATTERNS: RegExp[] = [
  /\b(?:cures?|treats?|heals?)\b/gi,
  /\b(?:acne|eczema|rosacea|psoriasis)\s+(?:cure|treatment|fix)\b/gi,
  /\bdermatologist\s+(?:approved|recommended)\b/gi,
  /\banti[-\s]?aging\s+(?:proven|guaranteed)\b/gi,
  /\bsafe\s+for\s+everyone\b/gi,
];

const DETECTORS: { kind: ClaimKind; patterns: RegExp[] }[] = [
  { kind: 'price', patterns: PRICE_PATTERNS },
  { kind: 'discount', patterns: DISCOUNT_PATTERNS },
  { kind: 'statistic', patterns: STATISTIC_PATTERNS },
  { kind: 'superlative', patterns: SUPERLATIVE_PATTERNS },
  { kind: 'physical_testing', patterns: PHYSICAL_TESTING_PATTERNS },
  { kind: 'health', patterns: HEALTH_PATTERNS },
];

function scan(text: string, patterns: RegExp[]): string[] {
  const hits: string[] = [];
  for (const pattern of patterns) {
    // Patterns are module-level and stateful with /g, so reset before each use.
    pattern.lastIndex = 0;
    const matches = text.match(pattern);
    if (matches) hits.push(...matches.map((m) => m.trim()));
  }
  return hits;
}

/** Detects claim-like language in a single string. */
export function detectClaims(text: string, options: { kinds?: ClaimKind[] } = {}): ClaimHit[] {
  const enabled = options.kinds;
  const hits: ClaimHit[] = [];
  for (const detector of DETECTORS) {
    if (enabled && !enabled.includes(detector.kind)) continue;
    for (const match of scan(text, detector.patterns)) {
      hits.push({ kind: detector.kind, text, match });
    }
  }
  return hits;
}

/** Detects brand-configured banned phrases (case-insensitive substring match). */
export function detectBannedPhrases(text: string, bannedPhrases: string[]): ClaimHit[] {
  const haystack = text.toLowerCase();
  return bannedPhrases
    .filter((phrase) => haystack.includes(phrase.toLowerCase()))
    .map((phrase) => ({ kind: 'banned_phrase' as const, text, match: phrase }));
}

/** True when a line states a number that a viewer would read as a fact. */
export function containsNumericClaim(text: string): boolean {
  if (/\b\d{1,3}(?:\.\d+)?\s?%/.test(text)) return true;
  if (/\b\d+\s+out\s+of\s+\d+\b/i.test(text)) return true;
  if (/[$£€]\s?\d/.test(text)) return true;
  if (/\b\d+(?:\.\d+)?\s?x\s+(?:more|better|faster|longer)\b/i.test(text)) return true;
  // Durations and counts that are part of the premise ("10-minute look",
  // "step one", "count to ten") are not factual assertions about the world.
  return false;
}
