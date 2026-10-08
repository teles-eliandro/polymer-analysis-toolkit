/**
 * Guard against duplicate translation keys.
 *
 * A duplicated key inside one locale object is valid JavaScript and every
 * unit test still passes, but Create React App turns the ESLint
 * `no-dupe-keys` warning into a build failure when CI=true -- which is how
 * Vercel builds. The result is a deploy that fails while CI in GitHub is
 * green. This test reads the source and fails on the duplicate directly, so
 * the problem surfaces locally instead of on the deploy.
 */

const fs = require('fs');
const path = require('path');

const SOURCE = path.join(__dirname, '..', 'i18n', 'I18nContext.jsx');

/** Split the MESSAGES object into its per-locale blocks by brace depth. */
function localeBlocks(source) {
  const start = source.indexOf('const MESSAGES = {');
  expect(start).toBeGreaterThan(-1);

  const blocks = [];
  let depth = 0;
  let blockStart = -1;
  let currentLocale = null;

  for (let i = start; i < source.length; i += 1) {
    const ch = source[i];
    if (ch === '{') {
      depth += 1;
      if (depth === 2) blockStart = i;
    } else if (ch === '}') {
      if (depth === 2 && blockStart !== -1) {
        blocks.push({ locale: currentLocale, text: source.slice(blockStart, i + 1) });
        blockStart = -1;
        currentLocale = null;
      }
      depth -= 1;
      if (depth === 0) break;
    }
  }
  return blocks;
}

/** Capture the locale name that precedes each block, e.g. `en: {`. */
function namedLocales(source) {
  const names = [];
  const re = /(?:^|[\s,{])([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*\{/g;
  let m;
  while ((m = re.exec(source)) !== null) {
    // Only keep names that are at the top level of MESSAGES: `en`, `pt`, `es`.
    if (['en', 'pt', 'es'].includes(m[1])) names.push(m[1]);
  }
  return names;
}

function keysIn(blockText) {
  const keys = [];
  const re = /^\s*'([^']+)'\s*:/gm;
  let m;
  while ((m = re.exec(blockText)) !== null) keys.push(m[1]);
  return keys;
}

describe('i18n message tables', () => {
  const source = fs.readFileSync(SOURCE, 'utf8');

  test('every locale block is found', () => {
    const blocks = localeBlocks(source);
    expect(blocks.length).toBeGreaterThanOrEqual(3);
  });

  test('no locale defines the same key twice', () => {
    const locales = namedLocales(source);
    const blocks = localeBlocks(source);
    const problems = [];

    blocks.forEach((block, idx) => {
      const locale = locales[idx] || `block ${idx}`;
      const seen = new Map();
      keysIn(block.text).forEach((key, line) => {
        if (seen.has(key)) {
          problems.push(`${locale}: '${key}' defined twice (positions ${seen.get(key)} and ${line})`);
        } else {
          seen.set(key, line);
        }
      });
    });

    expect(problems).toEqual([]);
  });

  test('every locale defines the same set of keys', () => {
    const blocks = localeBlocks(source);
    const sets = blocks.map((b) => new Set(keysIn(b.text)));
    if (sets.length < 2) return;

    const reference = sets[0];
    const mismatches = [];
    sets.slice(1).forEach((set, i) => {
      const missing = [...reference].filter((k) => !set.has(k));
      const extra = [...set].filter((k) => !reference.has(k));
      if (missing.length) mismatches.push(`locale ${i + 1} missing: ${missing.join(', ')}`);
      if (extra.length) mismatches.push(`locale ${i + 1} extra: ${extra.join(', ')}`);
    });

    expect(mismatches).toEqual([]);
  });
});
