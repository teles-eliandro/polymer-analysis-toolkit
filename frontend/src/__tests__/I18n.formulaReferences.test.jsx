/**
 * As referencias das formulas tem duas partes com regras opostas.
 *
 * "ASTM D638-22, Standard Test Method for Tensile Properties of Plastics" e uma
 * citacao: um nome que o leitor vai procurar literalmente, e que traduzido nao
 * recupera nada. "Both require the modulus from the initial linear region" e
 * prosa, escrita para quem le a pagina. Enquanto as duas viveram numa unica
 * string, so davam para traduzir juntas -- entao nenhuma era traduzida, e a
 * pagina em portugues exibia paragrafos em ingles sob um titulo em portugues.
 *
 * Este teste prende a separacao: a citacao fica literal no prop `reference`, a
 * prosa tem de estar numa chave `referenceNote`/`expressionNote` traduzida.
 *
 * O que ele NAO garante: a heuristica de prosa procura verbos ingleses comuns
 * (" is ", " must ", " because "). Uma frase sem nenhum deles escaparia. Ela
 * existe para pegar o caso real -- alguem colar um paragrafo explicativo de
 * volta no prop -- e nao como prova formal de que todo literal e uma citacao.
 */

const fs = require('fs');
const path = require('path');

const RAIZ = path.join(__dirname, '..');
const DICIONARIO = path.join(RAIZ, 'i18n', 'I18nContext.jsx');
const PAINEIS = [
  'MechanicalPanel',
  'MolecularPanel',
  'RheologyPanel',
  'StructurePanel',
  'ThermalPanel',
].map((nome) => ({
  nome,
  fonte: fs.readFileSync(path.join(RAIZ, 'components', `${nome}.jsx`), 'utf8'),
}));

/** Marcadores de prosa explicativa em ingles, que nao aparecem numa citacao. */
const PROSA = [
  ' is ', ' are ', ' was ', ' were ', ' has ', ' have ', ' must ', ' should ',
  ' does ', ' do not ', ' because ', ' therefore ', ' its ', ' cannot ',
];

// --- o mesmo extrator de blocos usado em I18n.keys.test.jsx ----------------
function localeBlocks(source) {
  const start = source.indexOf('const MESSAGES = {');
  const blocks = [];
  let depth = 0;
  let blockStart = -1;
  for (let i = start; i < source.length; i += 1) {
    const ch = source[i];
    if (ch === '{') {
      depth += 1;
      if (depth === 2) blockStart = i;
    } else if (ch === '}') {
      if (depth === 2 && blockStart !== -1) {
        blocks.push(source.slice(blockStart, i + 1));
        blockStart = -1;
      }
      depth -= 1;
      if (depth === 0) break;
    }
  }
  return blocks;
}

function namedLocales(source) {
  const names = [];
  const re = /(?:^|[\s,{])([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*\{/g;
  let m;
  while ((m = re.exec(source)) !== null) {
    if (['en', 'pt', 'es'].includes(m[1])) names.push(m[1]);
  }
  return names;
}

/** Mapa chave -> valor de um bloco de idioma (valores de uma linha). */
function entradas(bloco) {
  const mapa = new Map();
  const re = /^\s*'([^']+)'\s*:\s*'((?:[^'\\]|\\.)*)'\s*,/gm;
  let m;
  while ((m = re.exec(bloco)) !== null) {
    mapa.set(m[1], m[2].replace(/\\'/g, "'"));
  }
  return mapa;
}

describe('referencias das formulas: citacao literal, prosa traduzida', () => {
  const fonte = fs.readFileSync(DICIONARIO, 'utf8');
  const blocos = localeBlocks(fonte);
  const idiomas = namedLocales(fonte);
  const porIdioma = new Map();
  blocos.forEach((b, i) => porIdioma.set(idiomas[i] || `bloco ${i}`, entradas(b)));

  test('nenhuma prop reference= carrega prosa', () => {
    const problemas = [];
    for (const { nome, fonte: src } of PAINEIS) {
      const re = /reference="([^"]+)"/g;
      let m;
      while ((m = re.exec(src)) !== null) {
        const valor = m[1];
        const achado = PROSA.filter((p) => valor.includes(p));
        if (achado.length) {
          problemas.push(`${nome}: ${valor.slice(0, 70)}... [${achado.join(',')}]`);
        }
      }
    }
    expect(problemas).toEqual([]);
  });

  test('nenhuma prop expression= carrega prosa em ingles', () => {
    const problemas = [];
    for (const { nome, fonte: src } of PAINEIS) {
      const re = /expression="([^"]+)"/g;
      let m;
      while ((m = re.exec(src)) !== null) {
        const valor = m[1];
        const achado = PROSA.filter((p) => valor.includes(p));
        if (achado.length) {
          problemas.push(`${nome}: ${valor.slice(0, 70)}... [${achado.join(',')}]`);
        }
      }
    }
    expect(problemas).toEqual([]);
  });

  test('nao sobrou ingles na notacao: sum( e palavras soltas', () => {
    const problemas = [];
    for (const { nome, fonte: src } of PAINEIS) {
      const re = /expression="([^"]+)"/g;
      let m;
      while ((m = re.exec(src)) !== null) {
        if (/\bsum\(|\bhalf\b|\bpeak\b|\bedge-padded\b|\bwindow of\b/.test(m[1])) {
          problemas.push(`${nome}: ${m[1].slice(0, 70)}`);
        }
      }
    }
    expect(problemas).toEqual([]);
  });

  test('toda referenceNote/expressionNote existe nos 3 idiomas', () => {
    const chaves = [];
    for (const { fonte: src } of PAINEIS) {
      const re = /(referenceNote|expressionNote)=\{t\('([^']+)'\)\}/g;
      let m;
      while ((m = re.exec(src)) !== null) chaves.push(m[2]);
    }
    expect(chaves.length).toBeGreaterThan(20);

    const problemas = [];
    for (const chave of new Set(chaves)) {
      for (const [idioma, mapa] of porIdioma) {
        if (!mapa.has(chave)) problemas.push(`${idioma}: falta '${chave}'`);
      }
    }
    expect(problemas).toEqual([]);
  });

  test('a prosa foi mesmo traduzida: pt e es diferem do ingles', () => {
    const en = porIdioma.get('en');
    const pt = porIdioma.get('pt');
    const es = porIdioma.get('es');
    const problemas = [];
    for (const chave of en.keys()) {
      if (!chave.endsWith('.referenceNote') && !chave.endsWith('.expressionNote')) continue;
      if (pt.get(chave) === en.get(chave)) problemas.push(`pt nao traduzido: ${chave}`);
      if (es.get(chave) === en.get(chave)) problemas.push(`es nao traduzido: ${chave}`);
    }
    expect(problemas).toEqual([]);
  });

  test('a citacao nao foi duplicada para dentro das traducoes', () => {
    // Uma citacao traduzida nao se procura: ninguem acha "Rede de Bragg". O
    // invariante e que cada citacao existe UMA vez, no componente, e nunca como
    // valor de dicionario. (Uma frase de prosa pode mencionar uma norma -- o
    // que nao pode e a citacao inteira reaparecer traduzida.)
    const literais = [];
    for (const { fonte: src } of PAINEIS) {
      const re = /reference="([^"]+)"/g;
      let m;
      while ((m = re.exec(src)) !== null) literais.push(m[1]);
    }
    expect(literais.length).toBeGreaterThan(10);

    const problemas = [];
    for (const literal of literais) {
      for (const [idioma, mapa] of porIdioma) {
        for (const [chave, valor] of mapa) {
          if (valor.includes(literal)) {
            problemas.push(`${idioma}: ${chave} repete a citacao ${literal.slice(0, 45)}...`);
          }
        }
      }
    }
    expect(problemas).toEqual([]);
  });
});
