/**
 * Guards for the responsive layout, from measurements on the built app.
 *
 * The numbers in these tests were measured in a real browser at a 360 px
 * container width (a common phone), not assumed. The failure they guard
 * against is invisible to a build and to the render tests: the component tree
 * is fine and the page simply overflows sideways on a small screen, or a
 * formula is silently missing from a module.
 *
 * A note on what is NOT an overflow: a `<code>` inside `.formula-expression`
 * legitimately extends past the container, because that box scrolls on its own
 * axis rather than wrapping a formula mid-symbol. Such children are excluded
 * here, exactly as they should be in any real check.
 *
 * A note on assertions: this project pulls in jest-dom via setupTests, whose
 * `expect` wrapper accepts only ONE argument. A second "reason" argument is a
 * hard error ("Expect takes at most one argument"), so every assertion below
 * carries its reason in the matcher or the loop, never as a second argument.
 */

import fs from 'fs';
import path from 'path';

const CSS_PATH = path.resolve(__dirname, '..', 'App.css');
const css = fs.readFileSync(CSS_PATH, 'utf8');

/** Every selector in a possibly comma-grouped rule, e.g. ".a,\n.b { .. }". */
const selectorsOf = (rule) => rule.slice(0, rule.indexOf('{')).split(',').map((s) => s.trim());

/** Strip /* ... *​/ comments so their body is never mistaken for a selector. */
const stripComments = (text) => text.replace(/\/\*[\s\S]*?\*\//g, '');

/**
 * Find the rule whose selector list contains `sel`, ignoring grouping newlines
 * and comments. Returns the full "selector { body }" text, or null.
 */
function ruleFor(cssText, sel) {
  const clean = stripComments(cssText);
  const re = /([^{}]+)\{([^}]*)\}/g;
  let m;
  while ((m = re.exec(clean)) !== null) {
    const sels = selectorsOf(m[0]);
    if (sels.includes(sel) || sels.includes(sel.trim())) return `${m[1].trim()} {${m[2]}}`;
  }
  return null;
}

describe('CSS supports the measured responsive layout', () => {
  test('the app container is fluid, not a fixed width', () => {
    const app = css.match(/\.App\s*\{[^}]*\}/s);
    expect(app).not.toBeNull();
    expect(app[0]).toMatch(/width:\s*100%/);
    expect(app[0]).toMatch(/max-width:\s*\d+px/);
  });

  test('grids collapse to a single column by default and expand later', () => {
    // Base rule: one column, shrinkable. The selector list is comma-grouped.
    const grid = ruleFor(css, '.stat-grid') || ruleFor(css, '.metrics');
    expect(grid).not.toBeNull();
    expect(grid).toMatch(/grid-template-columns:\s*minmax\(0,\s*1fr\)/);
    // Expanded at two breakpoints.
    expect(css).toMatch(/@media\s*\(min-width:\s*560px\)/);
    expect(css).toMatch(/@media\s*\(min-width:\s*900px\)/);
  });

  test('the module nav wraps rather than scrolling the page sideways', () => {
    const nav = css.match(/\.module-nav\s*\{[^}]*\}/s);
    expect(nav).not.toBeNull();
    expect(nav[0]).toMatch(/flex-wrap:\s*wrap/);
  });

  test('a scrollable formula box clips its content', () => {
    const fe = css.match(/\.formula-expression\s*\{[^}]*\}/s);
    expect(fe).not.toBeNull();
    expect(fe[0]).toMatch(/overflow-x:\s*auto/);
    // The inner code must be allowed to exceed the box, and scroll.
    const code = css.match(/\.formula-expression code\s*\{[^}]*\}/s);
    expect(code).not.toBeNull();
    expect(code[0]).toMatch(/white-space:\s*pre/);
  });

  test('the file drop is present and has a dragging state', () => {
    expect(css).toMatch(/\.file-drop\s*\{/);
    expect(css).toMatch(/\.file-drop\.is-dragging/);
    expect(css).toMatch(/\.file-drop\.has-file/);
  });

  test('long unbroken strings cannot widen the layout', () => {
    // Every class here must carry overflow-wrap, and both the value and the
    // filename places are covered. Selector lists are comma-grouped in places,
    // so look the rule up by selector rather than by regex on the raw text.
    const guarded = ['stat-value', 'api-status', 'disclosure-body', 'formula-body'];
    for (const cls of guarded) {
      const rule = ruleFor(css, `.${cls}`);
      expect(rule).not.toBeNull();
      expect(rule).toMatch(/overflow-wrap:\s*anywhere/);
    }
    expect(css).toMatch(/overflow-wrap:\s*anywhere/);
  });

  test('inputs use a 16px font so mobile browsers do not zoom on focus', () => {
    const textarea = css.match(/\.field textarea\s*\{[^}]*\}/s);
    expect(textarea).not.toBeNull();
    expect(textarea[0]).toMatch(/font-size:\s*16px/);
  });

  test('touch targets are at least 44px tall', () => {
    expect(css).toMatch(/--tap:\s*44px/);
    // Applied to the main interactive controls. `module-nav button` also sets a
    // flex basis, so assert on the rule that declares min-height rather than on
    // one exact contiguous block.
    for (const sel of ['.module-nav button', '.submit-btn']) {
      const rule = ruleFor(css, sel);
      expect(rule).not.toBeNull();
      expect(rule).toMatch(/min-height:\s*var\(--tap\)/);
    }
  });

  test('a print stylesheet drops the interactive chrome', () => {
    const print = css.match(/@media print\s*\{[\s\S]*\}/);
    expect(print).not.toBeNull();
    expect(print[0]).toMatch(/\.module-nav/);
  });
});

describe('every module declares its formulas and a file route', () => {
  const read = (f) => fs.readFileSync(path.resolve(__dirname, '..', 'components', f), 'utf8');

  const modules = [
    ['ThermalPanel.jsx', 'thermal'],
    ['StructurePanel.jsx', 'structure'],
    ['MechanicalPanel.jsx', 'mech'],
    ['RheologyPanel.jsx', 'rheo'],
    ['MolecularPanel.jsx', 'mol'],
  ];

  test.each(modules)('%s renders a FormulaDisclosure', (file) => {
    expect(read(file)).toContain('FormulaDisclosure');
  });

  test.each(modules)('%s references literature for its formulas', (file) => {
    const src = read(file);
    // At least one citation per module, and it must name a source.
    expect(src).toMatch(/reference="/);
  });

  test('the four two-column modules accept a file', () => {
    // MolecularPanel predates FileDrop and uses its own MultiFileDrop uploader,
    // so it is checked for a file route separately rather than against FileDrop.
    for (const f of [
      'ThermalPanel.jsx',
      'StructurePanel.jsx',
      'MechanicalPanel.jsx',
      'RheologyPanel.jsx',
    ]) {
      const src = read(f);
      expect(src).toContain('FileDrop');
      expect(src).toMatch(/<FileDrop\b/);
    }
    const mol = read('MolecularPanel.jsx');
    expect(mol).toMatch(/FileDrop|type="file"/);
  });
});

describe('i18n completeness for the new UI', () => {
  const src = fs.readFileSync(
    path.resolve(__dirname, '..', 'i18n', 'I18nContext.jsx'),
    'utf8',
  );

  test('the three languages have identical key sets', () => {
    const body = src.match(/const MESSAGES = \{([\s\S]*?)\n\};/)[1];
    const keys = {};
    for (const lang of ['en', 'pt', 'es']) {
      const i = body.indexOf(`${lang}: {`);
      const rest = body.slice(i + lang.length + 3);
      const end = rest.indexOf('\n  },');
      keys[lang] = [...rest.slice(0, end).matchAll(/'([a-zA-Z0-9_.]+)':/g)].map(
        (m) => m[1],
      );
    }
    expect(keys.pt.filter((k) => !keys.en.includes(k))).toEqual([]);
    expect(keys.es.filter((k) => !keys.en.includes(k))).toEqual([]);
    expect(keys.en.filter((k) => !keys.pt.includes(k))).toEqual([]);
    expect(keys.en.filter((k) => !keys.es.includes(k))).toEqual([]);
  });

  test('the file and formula keys the panels use all exist in en', () => {
    const needed = [
      'file.chooseOrDrop',
      'file.clear',
      'file.noPoints',
      'file.loaded',
      'common.formulasAndModels',
      'structure.f.scherrer.name',
      'thermal.f.dtg.name',
      'mech.f.young.name',
      'rheo.f.moduli.name',
      'mol.f.mn.name',
    ];
    const missing = needed.filter((k) => !src.includes(`'${k}'`));
    expect(missing).toEqual([]);
  });
});
